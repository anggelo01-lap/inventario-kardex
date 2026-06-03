from decimal import Decimal
from sqlalchemy.orm import Session

from aplicacion.nucleo.seguridad import hash_password
from aplicacion.modelos.usuario import User
from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.proveedor import Proveedor
from aplicacion.modelos.cliente import Cliente
from aplicacion.modelos.producto import Producto


CATEGORIAS_BASE = [
    ("Repuestos", "Productos de repuesto para mantenimiento"),
    ("Accesorios", "Accesorios y complementos"),
    ("Seguridad", "Equipos y elementos de seguridad"),
    ("Insumos", "Insumos y materiales consumibles"),
]

PROVEEDORES_BASE = [
    ("Andes Supply", "Contacto 01", "900000001", "proveedor01@demo.local", "Avenida Demo 10"),
    ("Motopartes Lima", "Contacto 02", "900000002", "proveedor02@demo.local", "Avenida Demo 20"),
    ("Distribuciones Delta", "Contacto 03", "900000003", "proveedor03@demo.local", "Avenida Demo 30"),
    ("Norte Comercial", "Contacto 04", "900000004", "proveedor04@demo.local", "Avenida Demo 40"),
    ("Importadora Nova", "Contacto 05", "900000005", "proveedor05@demo.local", "Avenida Demo 50"),
]

CLIENTES_BASE = [
    ("Cliente Solis", "70000001", "955000001", "cliente01@demo.local", "Jiron Demo 7"),
    ("Cliente Rivera", "70000002", "955000002", "cliente02@demo.local", "Jiron Demo 14"),
    ("Cliente Paredes", "70000003", "955000003", "cliente03@demo.local", "Jiron Demo 21"),
    ("Cliente Huaman", "70000004", "955000004", "cliente04@demo.local", "Jiron Demo 28"),
    ("Cliente Torres", "70000005", "955000005", "cliente05@demo.local", "Jiron Demo 35"),
]

PRODUCTOS_BASE = [
    ("PROD-001", "Filtro de Aceite", "Filtro de aceite para motor", 1, 1, "producto", Decimal("25.50"), 50, 10),
    ("PROD-002", "Pastillas de Freno", "Pastillas de freno delanteras", 1, 2, "producto", Decimal("45.00"), 35, 8),
    ("PROD-003", "Bujía de Encendido", "Bujía de encendido estándar", 1, 3, "producto", Decimal("8.50"), 100, 20),
    ("PROD-004", "Aceite Motor 5W-30", "Aceite sintético 5W-30", 4, 1, "insumo", Decimal("38.00"), 60, 15),
    ("PROD-005", "Limpiador Multiusos", "Limpiador multiusos para superficies", 4, 2, "insumo", Decimal("12.90"), 80, 25),
    ("PROD-006", "Casco de Seguridad", "Casco de seguridad industrial", 3, 3, "producto", Decimal("55.00"), 25, 5),
    ("PROD-007", "Guantes de Trabajo", "Guantes de cuero para trabajo", 3, 4, "producto", Decimal("18.00"), 45, 12),
    ("PROD-008", "Tapacubos", "Tapacubos decorativos", 2, 5, "producto", Decimal("32.00"), 30, 8),
    ("PROD-009", "Alfombrillas", "Alfombrillas de goma", 2, 1, "producto", Decimal("28.00"), 40, 10),
    ("PROD-010", "Limpiaparabrisas", "Juego de limpiaparabrisas", 2, 2, "producto", Decimal("22.50"), 35, 9),
]


def seed_admin_user(
    db: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
) -> tuple[User, bool]:
    existing_by_username = db.query(User).filter(User.username == username).first()
    existing_by_email = db.query(User).filter(User.email == email).first()

    if (
        existing_by_username is not None
        and existing_by_email is not None
        and existing_by_username.id != existing_by_email.id
    ):
        raise ValueError("El username y el email pertenecen a usuarios distintos.")

    user = existing_by_username or existing_by_email
    created = user is None

    if user is None:
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
            role="admin",
        )
        db.add(user)
    else:
        user.username = username
        user.email = email
        user.full_name = full_name
        user.hashed_password = hash_password(password)
        user.is_active = True
        user.role = "admin"

    db.commit()
    db.refresh(user)
    return user, created


def seed_categorias(db: Session) -> list[Categoria]:
    categorias: list[Categoria] = []
    for nombre, descripcion in CATEGORIAS_BASE:
        categoria = db.query(Categoria).filter(Categoria.nombre == nombre).first()
        if categoria is None:
            categoria = Categoria(nombre=nombre, descripcion=descripcion)
            db.add(categoria)
            db.flush()
        categorias.append(categoria)
    db.commit()
    return categorias


def seed_proveedores(db: Session) -> list[Proveedor]:
    proveedores: list[Proveedor] = []
    for nombre, contacto, telefono, email, direccion in PROVEEDORES_BASE:
        proveedor = db.query(Proveedor).filter(Proveedor.nombre == nombre).first()
        if proveedor is None:
            proveedor = Proveedor(
                nombre=nombre,
                contacto=contacto,
                telefono=telefono,
                email=email,
                direccion=direccion,
                notas="Proveedor inicial",
            )
            db.add(proveedor)
            db.flush()
        proveedores.append(proveedor)
    db.commit()
    return proveedores


def seed_clientes(db: Session) -> list[Cliente]:
    clientes: list[Cliente] = []
    for nombre, documento, telefono, email, direccion in CLIENTES_BASE:
        cliente = db.query(Cliente).filter(Cliente.nombre == nombre).first()
        if cliente is None:
            cliente = Cliente(
                nombre=nombre,
                documento=documento,
                telefono=telefono,
                email=email,
                direccion=direccion,
                notas="Cliente inicial",
            )
            db.add(cliente)
            db.flush()
        clientes.append(cliente)
    db.commit()
    return clientes


def seed_productos(db: Session, categorias: list[Categoria], proveedores: list[Proveedor]) -> list[Producto]:
    productos: list[Producto] = []
    for codigo, nombre, descripcion, cat_idx, prov_idx, tipo, precio, stock, stock_min in PRODUCTOS_BASE:
        producto = db.query(Producto).filter(Producto.codigo == codigo).first()
        if producto is None:
            producto = Producto(
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                categoria_id=categorias[(cat_idx - 1) % len(categorias)].id,
                proveedor_id=proveedores[(prov_idx - 1) % len(proveedores)].id,
                tipo=tipo,
                precio=precio,
                stock_actual=stock,
                stock_minimo=stock_min,
            )
            db.add(producto)
            db.flush()
        productos.append(producto)
    db.commit()
    return productos


def bootstrap_demo_data(db: Session) -> None:
    seed_categorias(db)
    seed_proveedores(db)
    seed_clientes(db)
    categorias = seed_categorias(db)
    proveedores = seed_proveedores(db)
    seed_productos(db, categorias, proveedores)
