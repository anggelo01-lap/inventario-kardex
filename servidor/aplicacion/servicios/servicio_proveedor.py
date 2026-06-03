from sqlalchemy.orm import Session

from aplicacion.modelos.proveedor import Proveedor
from aplicacion.esquemas.proveedor import ProveedorCreate, ProveedorUpdate


def crear_proveedor(db: Session, payload: ProveedorCreate) -> Proveedor:
    proveedor = Proveedor(
        nombre=payload.nombre.strip(),
        contacto=payload.contacto.strip() if payload.contacto else None,
        telefono=payload.telefono.strip() if payload.telefono else None,
        email=payload.email.strip().lower() if payload.email else None,
        direccion=payload.direccion.strip() if payload.direccion else None,
        notas=payload.notas.strip() if payload.notas else None,
    )
    db.add(proveedor)
    db.commit()
    db.refresh(proveedor)
    return proveedor


def listar_proveedores(db: Session) -> list[Proveedor]:
    return list(db.query(Proveedor).order_by(Proveedor.nombre.asc()).all())


def obtener_proveedor(db: Session, proveedor_id: int) -> Proveedor | None:
    return db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()


def actualizar_proveedor(db: Session, proveedor_id: int, payload: ProveedorUpdate) -> Proveedor | None:
    proveedor = obtener_proveedor(db, proveedor_id)
    if proveedor is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for field in ("nombre", "contacto", "telefono", "direccion", "notas"):
        if field in data:
            value = data[field]
            setattr(proveedor, field, value.strip() if isinstance(value, str) and value else None)
    if "email" in data:
        proveedor.email = data["email"].strip().lower() if data["email"] else None
    db.commit()
    db.refresh(proveedor)
    return proveedor


def eliminar_proveedor(db: Session, proveedor_id: int) -> bool:
    proveedor = obtener_proveedor(db, proveedor_id)
    if proveedor is None:
        return False
    db.delete(proveedor)
    db.commit()
    return True
