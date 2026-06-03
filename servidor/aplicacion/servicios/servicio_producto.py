# Productos / Inventario
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from aplicacion.nucleo.configuracion import get_settings
from aplicacion.excepciones import CategoriaNoEncontradaError, ProductoEnUsoError, ProductoNoEncontradoError, TipoProductoInvalidoError
from aplicacion.modelos.categoria import Categoria
from aplicacion.modelos.movimiento import Movimiento
from aplicacion.modelos.producto import Producto
from aplicacion.modelos.proveedor import Proveedor
from aplicacion.esquemas.producto import ProductoCreate, ProductoUpdate


TIPOS_PRODUCTO_VALIDOS = {"repuesto", "producto", "insumo"}
MIME_TYPES_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
settings = get_settings()


class ImagenProductoInvalidaError(ValueError):
    pass


def _is_local_media_url(image_url: str | None) -> bool:
    if not image_url:
        return False
    return image_url.startswith(f"{settings.media_url_prefix}/productos/")


def _resolve_media_file(image_url: str) -> Path | None:
    if not _is_local_media_url(image_url):
        return None
    relative = image_url.removeprefix(settings.media_url_prefix).lstrip("/\\")
    return settings.media_root_path / relative


def delete_producto_image(image_url: str | None) -> None:
    file_path = _resolve_media_file(image_url or "")
    if file_path and file_path.exists():
        file_path.unlink(missing_ok=True)


async def save_producto_image(file: UploadFile) -> str:
    content_type = (file.content_type or "").lower()
    suffix = MIME_TYPES_PERMITIDOS.get(content_type)
    original_suffix = Path(file.filename or "").suffix.lower()
    if suffix is None and original_suffix in MIME_TYPES_PERMITIDOS.values():
        suffix = original_suffix
    if suffix is None:
        raise ImagenProductoInvalidaError("Solo se permiten imagenes JPG, PNG, WEBP o GIF.")

    content = await file.read()
    max_bytes = settings.max_image_upload_mb * 1024 * 1024
    if not content:
        raise ImagenProductoInvalidaError("La imagen esta vacia.")
    if len(content) > max_bytes:
        raise ImagenProductoInvalidaError(
            f"La imagen supera el limite de {settings.max_image_upload_mb} MB."
        )

    settings.productos_media_path.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4().hex}{suffix}"
    destination = settings.productos_media_path / filename
    destination.write_bytes(content)
    return f"{settings.media_url_prefix}/productos/{filename}"


def crear_producto(db: Session, payload: ProductoCreate) -> Producto:
    if payload.tipo not in TIPOS_PRODUCTO_VALIDOS:
        raise TipoProductoInvalidoError()
    categoria = db.query(Categoria).filter(Categoria.id == payload.categoria_id).first()
    if categoria is None:
        raise CategoriaNoEncontradaError()
    proveedor = None
    if payload.proveedor_id is not None:
        proveedor = db.query(Proveedor).filter(Proveedor.id == payload.proveedor_id).first()
    producto = Producto(
        codigo=payload.codigo.strip(),
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        categoria_id=payload.categoria_id,
        proveedor_id=proveedor.id if proveedor else None,
        tipo=payload.tipo,
        image_url=payload.image_url.strip() if payload.image_url else None,
        precio=payload.precio,
        stock_actual=payload.stock_inicial,
        stock_minimo=payload.stock_minimo,
    )
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def listar_productos(db: Session, *, busqueda: str | None = None) -> list[Producto]:
    q = db.query(Producto).options(joinedload(Producto.categoria), joinedload(Producto.proveedor)).order_by(Producto.id.desc())
    if busqueda and busqueda.strip():
        term = f"%{busqueda.strip()}%"
        q = q.filter(or_(Producto.codigo.ilike(term), Producto.nombre.ilike(term)))
    return list(q.all())


def get_producto(db: Session, producto_id: int) -> Producto | None:
    return (
        db.query(Producto)
        .options(joinedload(Producto.categoria), joinedload(Producto.proveedor))
        .filter(Producto.id == producto_id)
        .first()
    )


def require_producto(db: Session, producto_id: int) -> Producto:
    p = get_producto(db, producto_id)
    if p is None:
        raise ProductoNoEncontradoError()
    return p


def actualizar_producto(db: Session, producto_id: int, payload: ProductoUpdate) -> Producto:
    p = require_producto(db, producto_id)
    data = payload.model_dump(exclude_unset=True)
    previous_image_url = p.image_url
    if "codigo" in data and data["codigo"] is not None:
        p.codigo = data["codigo"].strip()
    if "nombre" in data and data["nombre"] is not None:
        p.nombre = data["nombre"].strip()
    if "descripcion" in data:
        p.descripcion = data["descripcion"].strip() if data["descripcion"] else None
    if "categoria_id" in data and data["categoria_id"] is not None:
        categoria = db.query(Categoria).filter(Categoria.id == data["categoria_id"]).first()
        if categoria is None:
            raise CategoriaNoEncontradaError()
        p.categoria_id = data["categoria_id"]
    if "proveedor_id" in data:
        proveedor_id = data["proveedor_id"]
        if proveedor_id is not None:
            proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
            p.proveedor_id = proveedor.id if proveedor else None
        else:
            p.proveedor_id = None
    if "tipo" in data and data["tipo"] is not None:
        if data["tipo"] not in TIPOS_PRODUCTO_VALIDOS:
            raise TipoProductoInvalidoError()
        p.tipo = data["tipo"]
    if "image_url" in data:
        p.image_url = data["image_url"].strip() if data["image_url"] else None
    if "precio" in data and data["precio"] is not None:
        p.precio = data["precio"]
    if "stock_minimo" in data and data["stock_minimo"] is not None:
        p.stock_minimo = data["stock_minimo"]
    db.commit()
    db.refresh(p)
    if "image_url" in data and previous_image_url != p.image_url:
        delete_producto_image(previous_image_url)
    return p


def eliminar_producto(db: Session, producto_id: int) -> None:
    p = require_producto(db, producto_id)
    count = db.query(func.count(Movimiento.id)).filter(Movimiento.producto_id == producto_id).scalar()
    if count and int(count) > 0:
        raise ProductoEnUsoError()
    image_url = p.image_url
    db.delete(p)
    db.commit()
    delete_producto_image(image_url)


def count_productos_bajo_stock(db: Session) -> int:
    return (
        db.query(func.count(Producto.id))
        .filter(Producto.stock_minimo > 0, Producto.stock_actual < Producto.stock_minimo)
        .scalar()
        or 0
    )


def listar_alertas_stock(db: Session, *, limit: int = 8) -> list[Producto]:
    q = (
        db.query(Producto)
        .options(joinedload(Producto.proveedor))
        .filter(Producto.stock_minimo > 0, Producto.stock_actual < Producto.stock_minimo)
        .order_by((Producto.stock_minimo - Producto.stock_actual).desc(), Producto.nombre.asc())
    )
    if limit > 0:
        q = q.limit(limit)
    return list(q.all())


list_productos = listar_productos
create_producto = crear_producto
update_producto = actualizar_producto
delete_producto = eliminar_producto
