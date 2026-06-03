# Movimientos / Kardex
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session, joinedload

from aplicacion.excepciones import (
    CantidadInvalidaError,
    ProductoNoEncontradoError,
    StockInsuficienteError,
    TipoMovimientoInvalidoError,
)
from aplicacion.modelos.cliente import Cliente
from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.proveedor import Proveedor
from aplicacion.esquemas.movimiento import MovimientoCreate, MovimientoListaOut


def _get_producto_stock(db: Session, producto_id: int) -> int:
    stock_actual = db.query(Producto.stock_actual).filter(Producto.id == producto_id).scalar()
    if stock_actual is None:
        raise ProductoNoEncontradoError()
    return int(stock_actual)


def _aplicar_stock_entrada(db: Session, producto_id: int, cantidad: int) -> tuple[int, int]:
    result = db.execute(
        sa_update(Producto)
        .where(Producto.id == producto_id)
        .values(stock_actual=Producto.stock_actual + cantidad)
        .returning(Producto.stock_actual)
    ).scalar_one_or_none()
    if result is None:
        raise ProductoNoEncontradoError()
    stock_posterior = int(result)
    return stock_posterior - cantidad, stock_posterior


def _aplicar_stock_salida(db: Session, producto_id: int, cantidad: int) -> tuple[int, int]:
    result = db.execute(
        sa_update(Producto)
        .where(Producto.id == producto_id, Producto.stock_actual >= cantidad)
        .values(stock_actual=Producto.stock_actual - cantidad)
        .returning(Producto.stock_actual)
    ).scalar_one_or_none()
    if result is None:
        if db.query(Producto.id).filter(Producto.id == producto_id).first() is None:
            raise ProductoNoEncontradoError()
        raise StockInsuficienteError()
    stock_posterior = int(result)
    return stock_posterior + cantidad, stock_posterior


def _aplicar_stock_ajuste(db: Session, producto_id: int, cantidad: int) -> tuple[int, int]:
    stock_anterior = _get_producto_stock(db, producto_id)
    result = db.execute(
        sa_update(Producto)
        .where(Producto.id == producto_id)
        .values(stock_actual=cantidad)
        .returning(Producto.stock_actual)
    ).scalar_one_or_none()
    if result is None:
        raise ProductoNoEncontradoError()
    return stock_anterior, int(result)


def registrar_movimiento(db: Session, usuario_id: int, payload: MovimientoCreate) -> Movimiento:
    try:
        if payload.cantidad <= 0:
            raise CantidadInvalidaError()

        if payload.cliente_id is not None:
            cliente = db.query(Cliente.id).filter(Cliente.id == payload.cliente_id).first()
            if cliente is None:
                raise ProductoNoEncontradoError()

        if payload.proveedor_id is not None:
            proveedor = db.query(Proveedor.id).filter(Proveedor.id == payload.proveedor_id).first()
            if proveedor is None:
                raise ProductoNoEncontradoError()

        if payload.tipo == "entrada":
            stock_anterior, stock_posterior = _aplicar_stock_entrada(db, payload.producto_id, payload.cantidad)
        elif payload.tipo == "salida":
            stock_anterior, stock_posterior = _aplicar_stock_salida(db, payload.producto_id, payload.cantidad)
        elif payload.tipo == "ajuste":
            stock_anterior, stock_posterior = _aplicar_stock_ajuste(db, payload.producto_id, payload.cantidad)
        else:
            raise TipoMovimientoInvalidoError()

        cliente_id = payload.cliente_id if payload.tipo == "salida" else None
        proveedor_id = payload.proveedor_id if payload.tipo == "entrada" else None

        movimiento = Movimiento(
            producto_id=payload.producto_id,
            usuario_id=usuario_id,
            cliente_id=cliente_id,
            proveedor_id=proveedor_id,
            tipo=payload.tipo,
            cantidad=payload.cantidad,
            costo_unitario=payload.costo_unitario,
            referencia=payload.referencia,
            motivo=payload.motivo,
            observacion=payload.observacion,
            stock_anterior=stock_anterior,
            stock_posterior=stock_posterior,
        )
        db.add(movimiento)
        db.flush()
        db.commit()
        db.refresh(movimiento)
        return movimiento
    except Exception:
        db.rollback()
        raise


def list_movimientos_filtrados(
    db: Session,
    *,
    producto_id: int | None = None,
    tipo: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = 500,
) -> list[Movimiento]:
    q = (
        db.query(Movimiento)
        .options(
            joinedload(Movimiento.producto),
            joinedload(Movimiento.usuario),
            joinedload(Movimiento.cliente),
            joinedload(Movimiento.proveedor),
        )
        .order_by(Movimiento.fecha_movimiento.desc(), Movimiento.id.desc())
    )
    if producto_id is not None:
        q = q.filter(Movimiento.producto_id == producto_id)
    if tipo is not None and tipo.strip():
        q = q.filter(Movimiento.tipo == tipo.strip())
    if fecha_desde is not None:
        start = datetime.combine(fecha_desde, time.min, tzinfo=timezone.utc)
        q = q.filter(Movimiento.fecha_movimiento >= start)
    if fecha_hasta is not None:
        end = datetime.combine(fecha_hasta + timedelta(days=1), time.min, tzinfo=timezone.utc)
        q = q.filter(Movimiento.fecha_movimiento < end)
    if limit > 0:
        q = q.limit(min(limit, 2000))
    return list(q.all())


def movimiento_a_lista_out(m: Movimiento) -> MovimientoListaOut:
    return MovimientoListaOut(
        id=m.id,
        producto_id=m.producto_id,
        producto_codigo=m.producto.codigo if m.producto else None,
        producto_nombre=m.producto.nombre if m.producto else None,
        usuario_id=m.usuario_id,
        usuario_username=m.usuario.username if m.usuario else "",
        cliente_id=m.cliente_id,
        cliente_nombre=m.cliente.nombre if m.cliente else None,
        proveedor_id=m.proveedor_id,
        proveedor_nombre=m.proveedor.nombre if m.proveedor else None,
        tipo=m.tipo,
        cantidad=m.cantidad,
        stock_anterior=m.stock_anterior,
        stock_posterior=m.stock_posterior,
        motivo=m.motivo,
        fecha_movimiento=m.fecha_movimiento,
    )


def list_movimientos_como_dto(
    db: Session,
    *,
    producto_id: int | None = None,
    tipo: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    limit: int = 500,
) -> list[MovimientoListaOut]:
    rows = list_movimientos_filtrados(
        db,
        producto_id=producto_id,
        tipo=tipo,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        limit=limit,
    )
    return [movimiento_a_lista_out(m) for m in rows]
