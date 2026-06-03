import argparse
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from aplicacion.nucleo.base_datos import SessionLocal
from aplicacion.modelos.categoria import Categoria  # noqa: F401
from aplicacion.modelos.cliente import Cliente
from aplicacion.modelos.movimiento import Movimiento  # noqa: F401
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.proveedor import Proveedor  # noqa: F401
from aplicacion.modelos.usuario import User


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera movimientos de entrada/salida en los ultimos N dias."
    )
    parser.add_argument("--dias", type=int, default=60, help="Rango de dias hacia atras.")
    parser.add_argument("--entradas", type=int, default=1200, help="Cantidad de entradas a crear.")
    parser.add_argument("--salidas", type=int, default=1000, help="Cantidad de salidas a crear.")
    parser.add_argument(
        "--username",
        default="admin",
        help="Usuario que registra los movimientos (si no existe, se usa cualquier usuario activo).",
    )
    return parser


def random_fecha(start: datetime, end: datetime) -> datetime:
    span_seconds = (end - start).total_seconds()
    return start + timedelta(seconds=random.random() * span_seconds)


def resolve_user_id(db, username: str) -> int:
    user = None
    if username.strip():
        user = db.query(User).filter(User.username == username.strip(), User.is_active.is_(True)).first()
    if user is None:
        user = (
            db.query(User)
            .filter(User.is_active.is_(True))
            .order_by((User.role == "admin").desc(), User.id.asc())
            .first()
        )
    if user is None:
        raise ValueError("No existe un usuario activo para registrar movimientos.")
    return int(user.id)


def main() -> int:
    args = build_parser().parse_args()
    if args.dias <= 0 or args.entradas < 0 or args.salidas < 0:
        raise ValueError("dias debe ser > 0, y entradas/salidas deben ser >= 0.")

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=args.dias)

    db = SessionLocal()
    try:
        user_id = resolve_user_id(db, args.username)
        cliente_ids = [row[0] for row in db.query(Cliente.id).all()]
        productos = db.query(Producto.id, Producto.precio, Producto.stock_actual).all()
        if not productos:
            raise ValueError("No hay productos para generar movimientos.")

        stock_by_producto: dict[int, int] = {int(pid): int(stock or 0) for pid, _, stock in productos}
        precio_by_producto: dict[int, float] = {int(pid): float(precio or 0) for pid, precio, _ in productos}
        producto_ids = list(stock_by_producto.keys())

        entradas_creadas = 0
        salidas_creadas = 0

        for index in range(1, args.entradas + 1):
            producto_id = random.choice(producto_ids)
            cantidad = random.randint(1, 25)
            stock_anterior = stock_by_producto[producto_id]
            stock_posterior = stock_anterior + cantidad
            fecha = random_fecha(start, end)
            costo = round(precio_by_producto[producto_id] * random.uniform(0.45, 0.75), 2)

            db.execute(
                text("UPDATE productos SET stock_actual = :stock_actual WHERE id = :producto_id"),
                {"stock_actual": stock_posterior, "producto_id": producto_id},
            )
            db.execute(
                text(
                    """
                    INSERT INTO movimientos
                    (producto_id, usuario_id, tipo, cantidad, costo_unitario, referencia, observacion, fecha_movimiento, motivo, stock_anterior, stock_posterior, cliente_id)
                    VALUES
                    (:producto_id, :usuario_id, 'entrada', :cantidad, :costo, :referencia, :observacion, :fecha_movimiento, :motivo, :stock_anterior, :stock_posterior, NULL)
                    """
                ),
                {
                    "producto_id": producto_id,
                    "usuario_id": user_id,
                    "cantidad": cantidad,
                    "costo": costo,
                    "referencia": f"AUTO-ENT-{index:05d}",
                    "observacion": "Entrada generada automaticamente",
                    "fecha_movimiento": fecha,
                    "motivo": "Reposicion automatica",
                    "stock_anterior": stock_anterior,
                    "stock_posterior": stock_posterior,
                },
            )
            stock_by_producto[producto_id] = stock_posterior
            entradas_creadas += 1

        for index in range(1, args.salidas + 1):
            candidatos = [pid for pid, stock in stock_by_producto.items() if stock > 0]
            if not candidatos:
                break
            producto_id = random.choice(candidatos)
            max_qty = min(15, stock_by_producto[producto_id])
            cantidad = random.randint(1, max_qty)
            stock_anterior = stock_by_producto[producto_id]
            stock_posterior = stock_anterior - cantidad
            fecha = random_fecha(start, end)
            cliente_id = random.choice(cliente_ids) if cliente_ids else None

            db.execute(
                text("UPDATE productos SET stock_actual = :stock_actual WHERE id = :producto_id"),
                {"stock_actual": stock_posterior, "producto_id": producto_id},
            )
            db.execute(
                text(
                    """
                    INSERT INTO movimientos
                    (producto_id, usuario_id, tipo, cantidad, costo_unitario, referencia, observacion, fecha_movimiento, motivo, stock_anterior, stock_posterior, cliente_id)
                    VALUES
                    (:producto_id, :usuario_id, 'salida', :cantidad, NULL, :referencia, :observacion, :fecha_movimiento, :motivo, :stock_anterior, :stock_posterior, :cliente_id)
                    """
                ),
                {
                    "producto_id": producto_id,
                    "usuario_id": user_id,
                    "cantidad": cantidad,
                    "referencia": f"AUTO-SAL-{index:05d}",
                    "observacion": "Salida generada automaticamente",
                    "fecha_movimiento": fecha,
                    "motivo": "Venta automatica",
                    "stock_anterior": stock_anterior,
                    "stock_posterior": stock_posterior,
                    "cliente_id": cliente_id,
                },
            )
            stock_by_producto[producto_id] = stock_posterior
            salidas_creadas += 1

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        "Movimientos generados:\n"
        f"- Rango: {start.isoformat()} -> {end.isoformat()}\n"
        f"- Entradas creadas: {entradas_creadas}\n"
        f"- Salidas creadas: {salidas_creadas}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
