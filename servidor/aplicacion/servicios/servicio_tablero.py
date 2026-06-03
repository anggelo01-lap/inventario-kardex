# Tablero
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session

from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.dashboard import (
    DashboardMetricOut,
    DashboardMovimientoRecienteOut,
    DashboardResumenOut,
    DashboardSeriePointOut,
    DashboardTopProductoOut,
    StockAlertaOut,
)
from aplicacion.servicios.servicio_producto import count_productos_bajo_stock, listar_alertas_stock

DashboardPeriodo = Literal["all", "7d", "30d", "12m", "today"]
DashboardAgrupacion = Literal["auto", "dia", "mes"]
MESES_CORTOS = {
    1: "ene",
    2: "feb",
    3: "mar",
    4: "abr",
    5: "may",
    6: "jun",
    7: "jul",
    8: "ago",
    9: "sep",
    10: "oct",
    11: "nov",
    12: "dic",
}


def _month_start(value: datetime) -> datetime:
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return value.replace(year=year, month=month, day=1)


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return round(float(value), 2)


def _calc_variacion(actual: float, anterior: float) -> float | None:
    if anterior == 0:
        if actual == 0:
            return 0.0
        return None
    return round(((actual - anterior) / anterior) * 100, 2)


def _resolve_periodo(
    periodo: DashboardPeriodo,
    ahora: datetime,
) -> tuple[datetime | None, datetime | None, datetime | None, datetime | None, str]:
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    if periodo == "today":
        inicio = inicio_hoy
        fin = inicio_hoy + timedelta(days=1)
        return inicio, fin, inicio - timedelta(days=1), inicio, "dia"

    if periodo == "7d":
        inicio = inicio_hoy - timedelta(days=6)
        fin = inicio_hoy + timedelta(days=1)
        duracion = fin - inicio
        return inicio, fin, inicio - duracion, inicio, "dia"

    if periodo == "30d":
        inicio = inicio_hoy - timedelta(days=29)
        fin = inicio_hoy + timedelta(days=1)
        duracion = fin - inicio
        return inicio, fin, inicio - duracion, inicio, "dia"

    if periodo == "12m":
        fin = _add_months(_month_start(ahora), 1)
        inicio = _add_months(_month_start(ahora), -11)
        duracion_meses = 12
        previo_fin = inicio
        previo_inicio = _add_months(inicio, -duracion_meses)
        return inicio, fin, previo_inicio, previo_fin, "mes"

    return None, None, None, None, "mes"


def _apply_range(query, inicio: datetime | None, fin: datetime | None):
    if inicio is not None:
        query = query.filter(Movimiento.fecha_movimiento >= inicio)
    if fin is not None:
        query = query.filter(Movimiento.fecha_movimiento < fin)
    return query


def _metricas_salidas(db: Session, inicio: datetime | None, fin: datetime | None) -> tuple[float, int, float]:
    margen_expr = (Producto.precio - func.coalesce(Movimiento.costo_unitario, Producto.precio)) * Movimiento.cantidad
    row = (
        _apply_range(
            db.query(
                func.coalesce(func.sum(Movimiento.cantidad * Producto.precio), 0),
                func.coalesce(func.sum(Movimiento.cantidad), 0),
                func.coalesce(func.sum(margen_expr), 0),
            )
            .join(Producto, Producto.id == Movimiento.producto_id)
            .filter(Movimiento.tipo == "salida"),
            inicio,
            fin,
        ).first()
        or (0, 0, 0)
    )
    ventas, cantidad, ganancia = row
    return _to_float(ventas), int(cantidad or 0), _to_float(ganancia)


def _serie_ventas(
    db: Session,
    inicio: datetime | None,
    fin: datetime | None,
    agrupacion: Literal["dia", "mes"],
) -> list[DashboardSeriePointOut]:
    rows = (
        _apply_range(
            db.query(Movimiento.fecha_movimiento, Movimiento.cantidad)
            .join(Producto, Producto.id == Movimiento.producto_id)
            .filter(Movimiento.tipo == "salida"),
            inicio,
            fin,
        )
        .order_by(Movimiento.fecha_movimiento.asc())
        .all()
    )

    buckets: dict[str, float] = {}
    for fecha_movimiento, cantidad in rows:
        dt = fecha_movimiento if fecha_movimiento.tzinfo else fecha_movimiento.replace(tzinfo=timezone.utc)
        key = dt.strftime("%Y-%m-%d") if agrupacion == "dia" else dt.strftime("%Y-%m")
        buckets[key] = buckets.get(key, 0.0) + float(cantidad or 0)

    if not buckets:
        return []

    points: list[DashboardSeriePointOut] = []
    for key, total in sorted(buckets.items()):
        if agrupacion == "dia":
            dt = datetime.strptime(key, "%Y-%m-%d")
            etiqueta = f"{dt.day:02d} {MESES_CORTOS[dt.month]}"
        else:
            dt = datetime.strptime(f"{key}-01", "%Y-%m-%d")
            etiqueta = f"{MESES_CORTOS[dt.month]} {dt.year}"
        points.append(DashboardSeriePointOut(etiqueta=etiqueta, valor=round(total, 2)))
    return points


def _top_productos(
    db: Session,
    inicio: datetime | None,
    fin: datetime | None,
    *,
    order_by: Literal["cantidad", "monto"],
    limit: int,
) -> list[DashboardTopProductoOut]:
    total_monto_expr = func.coalesce(func.sum(Movimiento.cantidad * Producto.precio), 0)
    total_cantidad_expr = func.coalesce(func.sum(Movimiento.cantidad), 0)

    query = _apply_range(
        db.query(
            Producto.id,
            Producto.codigo,
            Producto.nombre,
            total_cantidad_expr.label("total_cantidad"),
            total_monto_expr.label("total_monto"),
        )
        .join(Movimiento, Movimiento.producto_id == Producto.id)
        .filter(Movimiento.tipo == "salida")
        .group_by(Producto.id, Producto.codigo, Producto.nombre),
        inicio,
        fin,
    )

    if order_by == "cantidad":
        query = query.order_by(total_cantidad_expr.desc(), total_monto_expr.desc(), Producto.nombre.asc())
    else:
        query = query.order_by(total_monto_expr.desc(), total_cantidad_expr.desc(), Producto.nombre.asc())

    rows = query.limit(limit).all()
    return [
        DashboardTopProductoOut(
            producto_id=int(producto_id),
            codigo=str(codigo),
            nombre=str(nombre),
            total_cantidad=int(total_cantidad or 0),
            total_monto=_to_float(total_monto),
        )
        for producto_id, codigo, nombre, total_cantidad, total_monto in rows
    ]


def _movimientos_recientes(
    db: Session,
    inicio: datetime | None,
    fin: datetime | None,
    *,
    limit: int = 8,
) -> list[DashboardMovimientoRecienteOut]:
    rows = (
        _apply_range(
            db.query(
                Movimiento.id,
                Movimiento.fecha_movimiento,
                Movimiento.tipo,
                Movimiento.cantidad,
                Producto.codigo,
                Producto.nombre,
                Producto.precio,
                Movimiento.costo_unitario,
                User.username,
            )
            .join(Producto, Producto.id == Movimiento.producto_id)
            .join(User, User.id == Movimiento.usuario_id),
            inicio,
            fin,
        )
        .order_by(Movimiento.fecha_movimiento.desc(), Movimiento.id.desc())
        .limit(limit)
        .all()
    )

    result: list[DashboardMovimientoRecienteOut] = []
    for (
        movimiento_id,
        fecha_movimiento,
        tipo,
        cantidad,
        producto_codigo,
        producto_nombre,
        precio,
        costo_unitario,
        username,
    ) in rows:
        monto_estimado: float | None
        if tipo == "salida":
            monto_estimado = round(float(cantidad or 0) * float(precio or 0), 2)
        elif tipo == "entrada":
            monto_estimado = round(float(cantidad or 0) * float(costo_unitario or precio or 0), 2)
        else:
            monto_estimado = None
        result.append(
            DashboardMovimientoRecienteOut(
                id=int(movimiento_id),
                fecha_movimiento=fecha_movimiento,
                producto_codigo=str(producto_codigo),
                producto_nombre=str(producto_nombre),
                usuario_username=str(username),
                tipo=str(tipo),
                cantidad=int(cantidad or 0),
                monto_estimado=monto_estimado,
            )
        )
    return result


def _resolve_agrupacion(
    agrupacion_default: str,
    agrupar_por: DashboardAgrupacion,
) -> Literal["dia", "mes"]:
    if agrupar_por == "auto":
        raw = agrupacion_default
    elif agrupar_por == "dia":
        raw = "dia"
    else:
        raw = "mes"
    return "dia" if raw == "dia" else "mes"


def _build_alertas(alertas_rows: list) -> list[StockAlertaOut]:
    result: list[StockAlertaOut] = []
    for p in alertas_rows:
        pid = int(p.id)
        cod = str(p.codigo)
        nom = str(p.nombre)
        sa = int(p.stock_actual)
        sm = int(p.stock_minimo)
        prov = p.proveedor.nombre if getattr(p, "proveedor", None) else None
        result.append(StockAlertaOut(
            producto_id=pid,
            codigo=cod,
            nombre=nom,
            stock_actual=sa,
            stock_minimo=sm,
            faltante=max(sm - sa, 0),
            proveedor_nombre=prov,
        ))
    return result


def resumen_dashboard(
    db: Session,
    *,
    periodo: DashboardPeriodo = "all",
    agrupar_por: DashboardAgrupacion = "auto",
) -> DashboardResumenOut:
    total_productos = db.query(func.count(Producto.id)).scalar() or 0
    stock_total = db.query(func.coalesce(func.sum(Producto.stock_actual), 0)).scalar() or 0
    bajo = count_productos_bajo_stock(db)

    now = datetime.now(timezone.utc)
    inicio_dia = now.replace(hour=0, minute=0, second=0, microsecond=0)
    mov_hoy = db.query(func.count(Movimiento.id)).filter(Movimiento.fecha_movimiento >= inicio_dia).scalar() or 0

    categorias_rows = (
        db.query(Categoria.nombre, func.count(Producto.id))
        .outerjoin(Producto, Producto.categoria_id == Categoria.id)
        .group_by(Categoria.nombre)
        .order_by(Categoria.nombre.asc())
        .all()
    )
    productos_por_categoria = {str(nombre): int(total or 0) for nombre, total in categorias_rows}

    entradas = db.query(func.count(Movimiento.id)).filter(Movimiento.tipo == "entrada").scalar() or 0
    salidas = db.query(func.count(Movimiento.id)).filter(Movimiento.tipo == "salida").scalar() or 0

    inicio, fin, previo_inicio, previo_fin, agrupacion_default = _resolve_periodo(periodo, now)
    agrupacion = _resolve_agrupacion(agrupacion_default, agrupar_por)

    ventas_actuales, cantidad_actual, ganancia_actual = _metricas_salidas(db, inicio, fin)
    ventas_previas, cantidad_previa, ganancia_previa = _metricas_salidas(db, previo_inicio, previo_fin)

    alertas_rows = listar_alertas_stock(db, limit=6)
    alertas = _build_alertas(alertas_rows)

    return DashboardResumenOut(
        periodo=periodo,
        agrupacion=agrupacion,
        api_activa=True,
        total_productos=int(total_productos),
        stock_total=int(stock_total),
        productos_bajo_stock=bajo,
        movimientos_hoy=int(mov_hoy),
        ventas_estimadas=DashboardMetricOut(
            valor=ventas_actuales,
            variacion_pct=_calc_variacion(ventas_actuales, ventas_previas),
        ),
        cantidad_vendida=DashboardMetricOut(
            valor=float(cantidad_actual),
            variacion_pct=_calc_variacion(float(cantidad_actual), float(cantidad_previa)),
        ),
        ganancia_estimada=DashboardMetricOut(
            valor=ganancia_actual,
            variacion_pct=_calc_variacion(ganancia_actual, ganancia_previa),
        ),
        productos_por_categoria=productos_por_categoria,
        entradas_vs_salidas={"entradas": int(entradas), "salidas": int(salidas)},
        serie_ventas=_serie_ventas(db, inicio, fin, agrupacion),
        top_productos_cantidad=_top_productos(db, inicio, fin, order_by="cantidad", limit=5),
        top_productos_monto=_top_productos(db, inicio, fin, order_by="monto", limit=10),
        movimientos_recientes=_movimientos_recientes(db, inicio, fin, limit=8),
        alertas_stock=alertas,
    )
