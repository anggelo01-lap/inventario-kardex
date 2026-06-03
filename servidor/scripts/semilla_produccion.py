import argparse
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from random import choice, randint, uniform

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

CATEGORIAS_REPUESTOS = [
    ("Motor", "Repuestos para el motor"),
    ("Transmisión", "Repuestos para transmisión y embrague"),
    ("Frenos", "Repuestos para sistema de frenos"),
    ("Suspensión", "Repuestos para suspensión y amortiguación"),
    ("Eléctrico", "Repuestos eléctricos y electrónica"),
    ("Carrocería", "Repuestos de carrocería y latonería"),
    ("Lubricantes", "Aceites y lubricantes"),
    ("Filtros", "Filtros de aceite, aire y combustible"),
]

PROVEEDORES_REPUESTOS = [
    ("MotoRepuestos Sur", "Carlos Ruiz", "999888777", "ventas@motorepuestos.com", "Av. Industrial 123, Lima"),
    ("Carguero Parts", "María López", "999777666", "info@cargueroparts.com", "Jr. Comercio 456, Arequipa"),
    ("Distribuidora Andina", "Pedro Quispe", "999666555", "ventas@andina.com", "Av. Principal 789, Cusco"),
    ("Importadora del Norte", "Ana Torres", "999555444", "importaciones@norte.com", "Calle Central 101, Trujillo"),
    ("Repuestos Express", "José Flores", "999444333", "express@repuestos.com", "Jr. Velazco 202, Chiclayo"),
    ("AutoPartes Global", "Sofia Medina", "999333222", "global@autopartes.com", "Av. Los Incas 303, Huancayo"),
    ("Mantenimiento Total", "Luis Castillo", "999222111", "total@mantenimiento.com", "Calle Union 404, Pucallpa"),
    ("Insumos y Repuestos", "Carmen Rojas", "999111000", "insumos@repuestos.com", "Jr. Ayacucho 505, Iquitos"),
]

CLIENTES_REPUESTOS = [
    ("Taller Eléctrico Rodríguez", "10456789", "987654321", "taller@rodriguez.com", "Av. Benavides 123, Miraflores"),
    ("Transporte Los Andes", "20567890", "987654322", "logistica@losandes.com", "Jr. Puno 456, San Juan"),
    ("Moto Center Surco", "30678901", "987654323", "motocenter@surco.com", "Av. Javier Prado 789, Surco"),
    ("Servicio Express", "40789012", "987654324", "servicio@express.com", "Calle Los Olivos 101, Los Olivos"),
    ("Repuestos y Mantenimiento", "50890123", "987654325", "repuestos@mantenimiento.com", "Av. Universitaria 202, La Victoria"),
    ("Transportes del Valle", "60901234", "987654326", "valle@transportes.com", "Jr. Paruro 303, Cercado"),
    ("Taller Integral", "70012345", "987654327", "integral@taller.com", "Av. Arequipa 404, Lince"),
    ("Mantenimiento Industrial", "80123456", "987654328", "industrial@mantenimiento.com", "Calle Colon 505, Pueblo Libre"),
    ("Servicio Técnico Especializado", "90234567", "987654329", "especializado@tecnico.com", "Av. Brasil 606, Breña"),
    ("AutoMoto Repuestos", "01345678", "987654330", "automoto@repuestos.com", "Jr. Huancavelica 707, San Miguel"),
]

NOMBRES_PRODUCTOS = [
    "Kit de pastillas de freno delanteras",
    "Filtro de aceite premium",
    "Bujía de encendido doble electrodo",
    "Correa de distribución 144 dientes",
    "Amortiguador delantero gas",
    "Embrague completo reforzado",
    "Radiador de aluminio",
    "Bomba de agua",
    "Alternador 120A",
    "Kit de rodamientos de rueda",
    "Filtro de aire de alto flujo",
    "Cable de bujía performance",
    "Discos de freno ventilados",
    "Maza de rueda delantera",
    "Junta de culata multicapa",
    "Bomba de combustible eléctrica",
    "Soporte de motor hidráulico",
    "Kit de terminales de dirección",
    "Aceite de motor 15W40",
    "Líquido de frenos DOT 4",
    "Refrigerante orgánico",
    "Grasa multipropósito litio",
    "Juego de manguitos de radiador",
    "Interruptor de luces",
    "Relé de arranque",
    "Sensor de temperatura",
    "Sensor de oxígeno",
    "Bobina de encendido",
    "Modulo de encendido",
    "Valvula EGR",
    "Catalizador",
    "Silenciador de escape",
    "Tubo de escape completo",
    "Soporte de transmisión",
    "Collarín de embrague",
    "Plato de presión",
    "Disco de embrague",
    "Rulemán de embrague",
    "Kit de clutch",
    "Caja de cambios manual",
    "Differencial trasero",
    "Cardan de transmisión",
    "Palier de transmisión",
    "Rótula de suspensión",
    "Muñón de dirección",
    "Bieleta de suspensión",
    "Estabilizador de barra",
    "Bujes de suspensión",
    "Amortiguador trasero",
    "Resorte helicoidal",
    "Kit de amortiguación",
    "Manguito de freno",
    "Caliper de freno",
    "Bomba de freno",
    "Servo de freno",
    "Freno de mano",
    "Cable de freno de mano",
    "Líquido refrigerante",
    "Depósito de expansión",
    "Manguera de radiador superior",
    "Manguera de radiador inferior",
    "Termostato",
    "Ventilador eléctrico",
    "Polea de cigüeñal",
    "Tensor de correa",
    "Correa de alternador",
    "Correa de aire acondicionado",
    "Correa poly V",
    "Kit de correas",
    "Bomba de dirección hidráulica",
    "Cremallera de dirección",
    "Terminal exterior",
    "Terminal interior",
    "Buje de cremallera",
    "Fuelle de cremallera",
    "Aceite de dirección",
    "Filtro de combustible",
    "Bomba de inyección",
    "Inyectores diesel",
    "Inyectores gasolina",
    "Regulador de presión",
    "Rail de combustible",
    "Filtro separador de agua",
    "Aceite de caja",
    "Aceite de diferencial",
    "Kit de retenes",
    "Retén de cigüeñal",
    "Retén de levas",
    "Retén de rueda",
    "Junta de tapa de válvulas",
    "Junta de colector",
    "Junta de múltiple",
    "Empaques completos",
    "Kit de juntas motor",
    "Pistones y anillos",
    "Biela completa",
    "Cigüeñal",
    "Árbol de levas",
    "Culata completa",
    "Bloque de motor",
    "Tapa de cilindros",
    "Valvulas de admisión",
    "Valvulas de escape",
    "Asientos de válvula",
    "Guías de válvula",
    "Muelles de válvula",
    "Retenedores de válvula",
    "Cadenilla de distribución",
    "Piñón de cigüeñal",
    "Piñón de árbol de levas",
    "Tensor de cadena",
    "Guía de cadena",
    "Kit de distribución",
    "Sensor de posición de cigüeñal",
    "Sensor de posición de árbol de levas",
    "Sensor de detonación",
    "Sensor de presión de aceite",
    "Sensor de presión de turbo",
    "Sensor de masa de aire",
    "Sensor de temperatura de aire",
    "Valvula IAC",
    "Cuerpo de aceleración",
    "Pedal de acelerador",
    "Cable de acelerador",
    "Motor de arranque",
    "Bendix de arranque",
    "Solenoides de arranque",
    "Batería 12V 75Ah",
    "Terminales de batería",
    "Cables de batería",
    "Alternador 90A",
    "Regulador de voltaje",
    "Portaescobillas",
    "Escobillas de alternador",
    "Polea de alternador",
    "Faros delanteros",
    "Faros traseros",
    "Lámparas halógenas H4",
    "Lámparas LED",
    "Intermitentes",
    "Luz de freno",
    "Luz de reversa",
    "Switch de luces",
    "Fusibles y relés",
    "Caja de fusibles",
    "Cableado principal",
    "Conectores eléctricos",
    "Espejo retrovisor",
    "Espejo lateral",
    "Limpiaparabrisas",
    "Mecanismo de limpiaparabrisas",
    "Motor de limpiaparabrisas",
    "Parabrisas delantero",
    "Vidrio lateral",
    "Vidrio trasero",
    "Gomas de ventana",
    "Canaleta de ventana",
    "Motor de elevavidrio",
    "Interruptor de elevavidrio",
    "Cerradura de puerta",
    "Manija de puerta",
    "Bisagra de puerta",
    "Cofre del motor",
    "Portón trasero",
    "Parachoques delantero",
    "Parachoques trasero",
    "Molduras laterales",
    "Emblemas y logotipos",
    "Tapas de ruedas",
    "Rines de aleación",
    "Neumáticos 225/70R15",
    "Cubiertas de asiento",
    "Tapetes de piso",
    "Volante de dirección",
    "Palanca de cambios",
    "Freno de mano",
    "Pedal de freno",
    "Pedal de embrague",
    "Pedal de aceleración",
    "Tablero de instrumentos",
    "Velocímetro",
    "Tacómetro",
    "Reloj de temperatura",
    "Reloj de combustible",
    "Indicadores luminosos",
    "Radio de audio",
    "Bocinas",
    "Antena",
    "Aire acondicionado",
    "Compresor de A/C",
    "Condensador",
    "Evaporador",
    "Tuberías de A/C",
    "Gas refrigerante R134a",
    "Filtro de habitáculo",
    "Calefacción",
    "Radiador de calefacción",
    "Motor de ventilador",
    "Deflector de aire",
    "Escape cromado",
    "Protección de cárter",
    "Barra antivuelco",
    "Enganche de remolque",
    "Bolsa de aire",
    "Cinturones de seguridad",
    "Cabezas de seguridad",
    "ABS módulo",
    "Sensor ABS",
    "Anillo ABS",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Carga dataset completo para repuestos de motos y cargueras.")
    parser.add_argument("--productos", type=int, default=1000, help="Cantidad de productos a generar.")
    parser.add_argument("--stock", type=int, default=100, help="Stock inicial por producto.")
    parser.add_argument("--stock-minimo", type=int, default=20, help="Stock mínimo por producto.")
    parser.add_argument("--entradas", type=int, default=600, help="Cantidad de movimientos de entrada a generar.")
    parser.add_argument("--salidas", type=int, default=500, help="Cantidad de movimientos de salida a generar.")
    parser.add_argument("--prefix", default="REP", help="Prefijo para códigos de productos.")
    parser.add_argument("--username", default="admin", help="Usuario que registra movimientos.")
    return parser


def ensure_categorias(db) -> list[Categoria]:
    categorias: list[Categoria] = []
    for nombre, descripcion in CATEGORIAS_REPUESTOS:
        categoria = db.query(Categoria).filter(Categoria.nombre == nombre).first()
        if categoria is None:
            categoria = Categoria(nombre=nombre, descripcion=descripcion)
            db.add(categoria)
            db.flush()
        categorias.append(categoria)
    db.commit()
    return categorias


def ensure_proveedores(db) -> list[Proveedor]:
    proveedores: list[Proveedor] = []
    for nombre, contacto, telefono, email, direccion in PROVEEDORES_REPUESTOS:
        proveedor = db.query(Proveedor).filter(Proveedor.nombre == nombre).first()
        if proveedor is None:
            proveedor = Proveedor(
                nombre=nombre,
                contacto=contacto,
                telefono=telefono,
                email=email,
                direccion=direccion,
                notas="Proveedor de repuestos",
            )
            db.add(proveedor)
            db.flush()
        proveedores.append(proveedor)
    db.commit()
    return proveedores


def ensure_clientes(db) -> list[Cliente]:
    clientes: list[Cliente] = []
    for nombre, documento, telefono, email, direccion in CLIENTES_REPUESTOS:
        cliente = db.query(Cliente).filter(Cliente.nombre == nombre).first()
        if cliente is None:
            cliente = Cliente(
                nombre=nombre,
                documento=documento,
                telefono=telefono,
                email=email,
                direccion=direccion,
                notas="Cliente de repuestos",
            )
            db.add(cliente)
            db.flush()
        clientes.append(cliente)
    db.commit()
    return clientes


def ensure_image(index: int, codigo: str) -> str:
    return None


def ensure_productos(db, count: int, stock: int, stock_minimo: int, prefix: str, categorias, proveedores) -> list[Producto]:
    productos: list[Producto] = []
    for index in range(1, count + 1):
        codigo = f"{prefix}-{index:04d}"
        nombre = choice(NOMBRES_PRODUCTOS)
        categoria = categorias[(index - 1) % len(categorias)]
        proveedor = proveedores[(index - 1) % len(proveedores)]
        tipo = TIPOS[(index - 1) % len(TIPOS)]
        precio = Decimal(str(round(uniform(15.0, 250.0), 2)))

        producto = db.query(Producto).filter(Producto.codigo == codigo).first()
        if producto is None:
            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=f"Repuesto para motos y cargueras - {categoria.nombre}",
                categoria_id=categoria.id,
                proveedor_id=proveedor.id,
                tipo=tipo,
                precio=precio,
                stock_actual=stock,
                stock_minimo=stock_minimo,
            )
            db.add(producto)
            db.flush()
        else:
            producto.nombre = nombre
            producto.descripcion = f"Repuesto para motos y cargueras - {categoria.nombre}"
            producto.categoria_id = categoria.id
            producto.proveedor_id = proveedor.id
            producto.tipo = tipo
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
        )
    )
    db.commit()


def restore_product_stock(db, productos: list[Producto], stock: int) -> None:
    for producto in productos:
        producto.stock_actual = stock
    db.commit()


def create_movimiento(
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
            observacion="Movimiento generado automáticamente",
        ),
    )
    movimiento.fecha_movimiento = fecha
    db.add(movimiento)
    db.commit()


def seed_movimientos(db, productos: list[Producto], clientes: list[Cliente], user_id: int, entradas_count: int, salidas_count: int, stock: int) -> int:
    now = datetime.now(timezone.utc)
    created = 0

    for index in range(1, entradas_count + 1):
        producto = choice(productos)
        precio = float(producto.precio)
        qty = randint(5, 30)
        fecha = now - timedelta(days=randint(1, 90), hours=randint(0, 23))
        create_movimiento(
            db,
            user_id=user_id,
            producto_id=producto.id,
            tipo="entrada",
            cantidad=qty,
            fecha=fecha,
            referencia=f"REP-ENT-{index:04d}",
            costo_unitario=round(precio * 0.55, 2),
            motivo="Compra de repuestos",
        )
        created += 1

    for index in range(1, salidas_count + 1):
        producto = choice(productos)
        precio = float(producto.precio)
        cliente = choice(clientes)
        qty = randint(1, 15)
        fecha = now - timedelta(days=randint(1, 60), hours=randint(0, 23))
        create_movimiento(
            db,
            user_id=user_id,
            producto_id=producto.id,
            tipo="salida",
            cantidad=qty,
            fecha=fecha,
            referencia=f"REP-SAL-{index:04d}",
            costo_unitario=round(precio * 0.60, 2),
            cliente_id=cliente.id,
            motivo="Venta de repuestos",
        )
        created += 1
    
    restore_product_stock(db, productos, stock)
    return created


def main() -> int:
    args = build_parser().parse_args()
    prefix = args.prefix.strip().upper()

    db = SessionLocal()
    try:
        print("Poblando categorías...")
        categorias = ensure_categorias(db)
        
        print("Poblando proveedores...")
        proveedores = ensure_proveedores(db)
        
        print("Poblando clientes...")
        clientes = ensure_clientes(db)
        
        print(f"Poblando {args.productos} productos...")
        productos = ensure_productos(db, args.productos, args.stock, args.stock_minimo, prefix, categorias, proveedores)
        
        user_id = resolve_user_id(db, args.username)
        product_ids = [producto.id for producto in productos]
        
        print("Limpiando movimientos anteriores...")
        clear_demo_movements(db, product_ids)
        
        print(f"Generando {args.entradas} entradas y {args.salidas} salidas...")
        movimientos = seed_movimientos(db, productos, clientes, user_id, args.entradas, args.salidas, args.stock)
    finally:
        db.close()

    print(
        f"\nDataset de repuestos COMPLETO:\n"
        f"   - Productos:      {args.productos}\n"
        f"   - Categorias:     {len(CATEGORIAS_REPUESTOS)}\n"
        f"   - Proveedores:    {len(PROVEEDORES_REPUESTOS)}\n"
        f"   - Clientes:       {len(CLIENTES_REPUESTOS)}\n"
        f"   - Entradas:       {args.entradas}\n"
        f"   - Salidas:        {args.salidas}\n"
        f"   - Total movimientos: {movimientos}\n"
        f"   - Stock inicial:  {args.stock}/producto\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
