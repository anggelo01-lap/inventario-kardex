import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from aplicacion.nucleo.configuracion import get_settings
from aplicacion.nucleo.base_datos import SessionLocal
from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.cliente import Cliente
from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.proveedor import Proveedor
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.movimiento import MovimientoCreate
from aplicacion.servicios.servicio_movimiento import registrar_movimiento


settings = get_settings()
TIPOS = ("producto", "repuesto", "insumo")
PALETTE = (
    ("#dbeafe", "#2563eb"),
    ("#dcfce7", "#15803d"),
    ("#fee2e2", "#dc2626"),
    ("#fef3c7", "#d97706"),
    ("#ede9fe", "#7c3aed"),
    ("#cffafe", "#0891b2"),
)
CATEGORIAS_BASE = [
    ("Demo Repuestos", "Productos de ejemplo para repuestos"),
    ("Demo Accesorios", "Productos de ejemplo para accesorios"),
    ("Demo Seguridad", "Productos de ejemplo para seguridad"),
]
PROVEEDORES_BASE = [
    "Andes Supply",
    "Motopartes Lima",
    "Distribuciones Delta",
    "Norte Comercial",
    "Importadora Nova",
    "Repuestos Atlas",
    "Seguridad Prime",
    "Central Industrial",
    "Zona Taller",
    "Grupo Altura",
]
CLIENTES_BASE = [
    "Cliente Solis",
    "Cliente Rivera",
    "Cliente Paredes",
    "Cliente Huaman",
    "Cliente Torres",
    "Cliente Flores",
    "Cliente Castro",
    "Cliente Medina",
    "Cliente Rojas",
    "Cliente Vargas",
    "Cliente Garcia",
    "Cliente Leon",
    "Cliente Salazar",
    "Cliente Mena",
    "Cliente Bravo",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Carga dataset demo para productos, clientes y movimientos.")
    parser.add_argument("--count", type=int, default=70)
    parser.add_argument("--stock", type=int, default=100)
    parser.add_argument("--stock-minimo", type=int, default=15)
    parser.add_argument("--prefix", default="DEMO")
    parser.add_argument("--username", default="")
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


def ensure_proveedores(db) -> list[Proveedor]:
    proveedores: list[Proveedor] = []
    for index, nombre in enumerate(PROVEEDORES_BASE, start=1):
        proveedor = db.query(Proveedor).filter(Proveedor.nombre == nombre).first()
        if proveedor is None:
            proveedor = Proveedor(
                nombre=nombre,
                contacto=f"Contacto {index:02d}",
                telefono=f"900000{index:03d}",
                email=f"proveedor{index:02d}@demo.local",
                direccion=f"Avenida Demo {index * 10}",
                notas="Proveedor demo generado automaticamente",
            )
            db.add(proveedor)
            db.flush()
        proveedores.append(proveedor)
    return proveedores


def ensure_clientes(db) -> list[Cliente]:
    clientes: list[Cliente] = []
    for index, nombre in enumerate(CLIENTES_BASE, start=1):
        cliente = db.query(Cliente).filter(Cliente.nombre == nombre).first()
        if cliente is None:
            cliente = Cliente(
                nombre=nombre,
                documento=f"70{index:06d}",
                telefono=f"955000{index:03d}",
                email=f"cliente{index:02d}@demo.local",
                direccion=f"Jiron Demo {index * 7}",
                notas="Cliente demo generado automaticamente",
            )
            db.add(cliente)
            db.flush()
        clientes.append(cliente)
    return clientes


def ensure_demo_image(index: int, codigo: str, nombre: str) -> str:
    bg, accent = PALETTE[(index - 1) % len(PALETTE)]
    filename = f"demo-{index:03d}.svg"
    destination = settings.productos_media_path / filename
    settings.productos_media_path.mkdir(parents=True, exist_ok=True)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
<rect width="480" height="360" rx="28" fill="{bg}"/>
<circle cx="390" cy="88" r="74" fill="{accent}" fill-opacity="0.12"/>
<circle cx="88" cy="286" r="86" fill="{accent}" fill-opacity="0.10"/>
<rect x="36" y="38" width="132" height="34" rx="17" fill="{accent}"/>
<text x="52" y="60" font-size="20" font-family="Arial, sans-serif" font-weight="700" fill="#ffffff">{codigo}</text>
<text x="38" y="176" font-size="34" font-family="Arial, sans-serif" font-weight="700" fill="#0f172a">{nombre}</text>
<text x="38" y="212" font-size="18" font-family="Arial, sans-serif" fill="#334155">Inventario demo listo para dashboard</text>
<rect x="38" y="248" width="152" height="44" rx="16" fill="#ffffff"/>
<text x="60" y="276" font-size="19" font-family="Arial, sans-serif" font-weight="700" fill="{accent}">Stock ilustrativo</text>
</svg>
"""
    destination.write_text(svg, encoding="utf-8")
    return f"{settings.media_url_prefix}/productos/{filename}"


def ensure_productos(db, count: int, stock: int, stock_minimo: int, prefix: str, categorias, proveedores) -> list[Producto]:
    productos: list[Producto] = []
    for index in range(1, count + 1):
        codigo = f"{prefix}-{index:03d}"
        nombre = f"Producto Demo {index:03d}"
        categoria = categorias[(index - 1) % len(categorias)]
        proveedor = proveedores[(index - 1) % len(proveedores)]
        image_url = ensure_demo_image(index, codigo, nombre)
        precio = Decimal("18.50") + Decimal(index) * Decimal("1.75")

        producto = db.query(Producto).filter(Producto.codigo == codigo).first()
        if producto is None:
            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=f"Producto demo con imagen local #{index:03d}",
                categoria_id=categoria.id,
                proveedor_id=proveedor.id,
                tipo=TIPOS[(index - 1) % len(TIPOS)],
                image_url=image_url,
                precio=precio,
                stock_actual=stock,
                stock_minimo=stock_minimo,
            )
            db.add(producto)
            db.flush()
        else:
            producto.nombre = nombre
            producto.descripcion = f"Producto demo con imagen local #{index:03d}"
            producto.categoria_id = categoria.id
            producto.proveedor_id = proveedor.id
            producto.tipo = TIPOS[(index - 1) % len(TIPOS)]
            producto.image_url = image_url
            producto.precio = precio
            producto.stock_actual = stock
            producto.stock_minimo = stock_minimo
        productos.append(producto)
    db.commit()
    return productos


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
        raise ValueError("No hay usuarios activos para registrar movimientos demo.")
    return int(user.id)


def clear_demo_movements(db, product_ids: list[int]) -> None:
    if not product_ids:
        return
    db.execute(
        delete(Movimiento).where(
            Movimiento.producto_id.in_(product_ids),
            Movimiento.referencia.like("SEED-DEMO-%"),
        )
    )
    db.commit()


def restore_product_stock(db, productos: list[Producto], stock: int, stock_minimo: int) -> None:
    for producto in productos:
        producto.stock_actual = stock
        producto.stock_minimo = stock_minimo
    db.commit()


def create_demo_movement(
    db,
    *,
    user_id: int,
    producto_id: int,
    tipo: str,
    cantidad: int,
    fecha: datetime,
    referencia: str,
    costo_unitario: float | None = None,
    cliente_id: int | None = None,
    motivo: str | None = None,
) -> None:
    movimiento = registrar_movimiento(
        db,
        user_id,
        MovimientoCreate(
            producto_id=producto_id,
            cliente_id=cliente_id,
            tipo=tipo,
            cantidad=cantidad,
            costo_unitario=costo_unitario,
            referencia=referencia,
            motivo=motivo,
            observacion="Movimiento demo generado automaticamente",
        ),
    )
    movimiento.fecha_movimiento = fecha
    db.add(movimiento)
    db.commit()


def seed_movements(db, productos: list[Producto], clientes: list[Cliente], user_id: int) -> int:
    now = datetime.now(timezone.utc)
    created = 0

    for index, producto in enumerate(productos, start=1):
        precio = float(producto.precio)
        cliente = clientes[(index - 1) % len(clientes)]

        venta_fecha = now - timedelta(days=((index * 5) % 320), hours=index % 8)
        venta_qty = (index % 6) + 2
        create_demo_movement(
            db,
            user_id=user_id,
            producto_id=producto.id,
            tipo="salida",
            cantidad=venta_qty,
            fecha=venta_fecha,
            referencia=f"SEED-DEMO-SAL-{index:03d}-A",
            costo_unitario=round(precio * 0.62, 2),
            cliente_id=cliente.id,
            motivo="Venta demo inicial",
        )
        created += 1

        reposicion_fecha = venta_fecha + timedelta(days=(index % 3) + 1)
        if reposicion_fecha > now:
            reposicion_fecha = now - timedelta(hours=(index % 4) + 1)
        create_demo_movement(
            db,
            user_id=user_id,
            producto_id=producto.id,
            tipo="entrada",
            cantidad=venta_qty,
            fecha=reposicion_fecha,
            referencia=f"SEED-DEMO-ENT-{index:03d}-A",
            costo_unitario=round(precio * 0.55, 2),
            motivo="Reposicion demo",
        )
        created += 1

        if index % 4 == 0:
            venta_reciente_fecha = now - timedelta(days=index % 7, hours=(index % 5) + 1)
            venta_reciente_qty = (index % 4) + 1
            create_demo_movement(
                db,
                user_id=user_id,
                producto_id=producto.id,
                tipo="salida",
                cantidad=venta_reciente_qty,
                fecha=venta_reciente_fecha,
                referencia=f"SEED-DEMO-SAL-{index:03d}-B",
                costo_unitario=round(precio * 0.6, 2),
                cliente_id=cliente.id,
                motivo="Venta demo reciente",
            )
            created += 1

            if index > 8:
                restore_fecha = venta_reciente_fecha + timedelta(hours=6)
                if restore_fecha > now:
                    restore_fecha = now - timedelta(minutes=30 + index)
                create_demo_movement(
                    db,
                    user_id=user_id,
                    producto_id=producto.id,
                    tipo="entrada",
                    cantidad=venta_reciente_qty,
                    fecha=restore_fecha,
                    referencia=f"SEED-DEMO-ENT-{index:03d}-B",
                    costo_unitario=round(precio * 0.52, 2),
                    motivo="Reposicion demo reciente",
                )
                created += 1

        if index <= 8:
            ajuste_fecha = now - timedelta(hours=index)
            stock_objetivo = 6 + (index % 6)
            create_demo_movement(
                db,
                user_id=user_id,
                producto_id=producto.id,
                tipo="ajuste",
                cantidad=stock_objetivo,
                fecha=ajuste_fecha,
                referencia=f"SEED-DEMO-AJU-{index:03d}",
                motivo="Ajuste demo para alertas de stock",
            )
            created += 1

    return created


def main() -> int:
    args = build_parser().parse_args()
    prefix = args.prefix.strip().upper()

    db = SessionLocal()
    try:
        categorias = ensure_categorias(db)
        proveedores = ensure_proveedores(db)
        clientes = ensure_clientes(db)
        productos = ensure_productos(db, args.count, args.stock, args.stock_minimo, prefix, categorias, proveedores)
        user_id = resolve_user_id(db, args.username)
        product_ids = [producto.id for producto in productos]
        clear_demo_movements(db, product_ids)
        restore_product_stock(db, productos, args.stock, args.stock_minimo)
        movimientos = seed_movements(db, productos, clientes, user_id)
    finally:
        db.close()

    print(
        f"Dataset demo listo: productos={args.count} proveedores={len(PROVEEDORES_BASE)} "
        f"clientes={len(CLIENTES_BASE)} movimientos={movimientos}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
