import argparse
import sys
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from aplicacion.nucleo.base_datos import SessionLocal
from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.cliente import Cliente  # noqa: F401
from aplicacion.modelos.movimiento import Movimiento  # noqa: F401
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.proveedor import Proveedor  # noqa: F401
from aplicacion.modelos.usuario import User  # noqa: F401


CATEGORIAS_BASE = [
    ("Demo Repuestos", "Productos de ejemplo para repuestos"),
    ("Demo Accesorios", "Productos de ejemplo para accesorios"),
    ("Demo Seguridad", "Productos de ejemplo para seguridad"),
]
TIPOS = ("producto", "repuesto", "insumo")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inserta productos demo con stock inicial.")
    parser.add_argument("--count", type=int, default=70, help="Cantidad de productos a generar.")
    parser.add_argument("--stock", type=int, default=100, help="Stock actual que recibira cada producto.")
    parser.add_argument("--stock-minimo", type=int, default=15, help="Stock minimo por producto.")
    parser.add_argument("--prefix", default="DEMO", help="Prefijo para el codigo del producto.")
    return parser


def ensure_categorias(db) -> list[Categoria]:
    categorias: list[Categoria] = []
    for nombre, descripcion in CATEGORIAS_BASE:
        categoria = db.query(Categoria).filter(Categoria.nombre == nombre).first()
        if categoria is None:
            categoria = Categoria(nombre=nombre, descripcion=descripcion)
            db.add(categoria)
            db.flush()
        categorias.append(categoria)
    return categorias


def seed_productos(count: int, stock: int, stock_minimo: int, prefix: str) -> tuple[int, int]:
    db = SessionLocal()
    creados = 0
    actualizados = 0

    try:
        categorias = ensure_categorias(db)
        for index in range(1, count + 1):
            codigo = f"{prefix.strip().upper()}-{index:03d}"
            categoria = categorias[(index - 1) % len(categorias)]
            tipo = TIPOS[(index - 1) % len(TIPOS)]
            precio = Decimal("12.50") + Decimal(index)

            producto = db.query(Producto).filter(Producto.codigo == codigo).first()
            if producto is None:
                producto = Producto(
                    codigo=codigo,
                    nombre=f"Producto Demo {index:03d}",
                    descripcion=f"Producto de prueba generado automaticamente #{index:03d}",
                    categoria_id=categoria.id,
                    tipo=tipo,
                    precio=precio,
                    stock_actual=stock,
                    stock_minimo=stock_minimo,
                )
                db.add(producto)
                creados += 1
            else:
                producto.nombre = f"Producto Demo {index:03d}"
                producto.descripcion = f"Producto de prueba generado automaticamente #{index:03d}"
                producto.categoria_id = categoria.id
                producto.tipo = tipo
                producto.precio = precio
                producto.stock_actual = stock
                producto.stock_minimo = stock_minimo
                actualizados += 1

        db.commit()
        return creados, actualizados
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> int:
    args = build_parser().parse_args()
    creados, actualizados = seed_productos(
        count=args.count,
        stock=args.stock,
        stock_minimo=args.stock_minimo,
        prefix=args.prefix,
    )
    print(
        f"Productos demo procesados: creados={creados} actualizados={actualizados} "
        f"stock={args.stock} prefijo={args.prefix.strip().upper()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
