from sqlalchemy.orm import Session

from aplicacion.modelos.cliente import Cliente
from aplicacion.esquemas.cliente import ClienteCreate, ClienteUpdate


def crear_cliente(db: Session, payload: ClienteCreate) -> Cliente:
    cliente = Cliente(
        nombre=payload.nombre.strip(),
        documento=payload.documento.strip() if payload.documento else None,
        telefono=payload.telefono.strip() if payload.telefono else None,
        email=payload.email.strip().lower() if payload.email else None,
        direccion=payload.direccion.strip() if payload.direccion else None,
        notas=payload.notas.strip() if payload.notas else None,
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


def listar_clientes(db: Session) -> list[Cliente]:
    return list(db.query(Cliente).order_by(Cliente.nombre.asc()).all())


def obtener_cliente(db: Session, cliente_id: int) -> Cliente | None:
    return db.query(Cliente).filter(Cliente.id == cliente_id).first()


def actualizar_cliente(db: Session, cliente_id: int, payload: ClienteUpdate) -> Cliente | None:
    cliente = obtener_cliente(db, cliente_id)
    if cliente is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    for field in ("nombre", "documento", "telefono", "direccion", "notas"):
        if field in data:
            value = data[field]
            setattr(cliente, field, value.strip() if isinstance(value, str) and value else None)
    if "email" in data:
        cliente.email = data["email"].strip().lower() if data["email"] else None
    db.commit()
    db.refresh(cliente)
    return cliente


def eliminar_cliente(db: Session, cliente_id: int) -> bool:
    cliente = obtener_cliente(db, cliente_id)
    if cliente is None:
        return False
    db.delete(cliente)
    db.commit()
    return True
