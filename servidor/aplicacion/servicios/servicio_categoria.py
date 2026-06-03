from sqlalchemy.orm import Session

from aplicacion.modelos.categoria import Categoria
from aplicacion.esquemas.categoria import CategoriaCreate, CategoriaUpdate


def crear_categoria(db: Session, payload: CategoriaCreate) -> Categoria:
    categoria = Categoria(
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
    )
    db.add(categoria)
    db.commit()
    db.refresh(categoria)
    return categoria


def listar_categorias(db: Session) -> list[Categoria]:
    return list(db.query(Categoria).order_by(Categoria.nombre.asc()).all())


def obtener_categoria(db: Session, categoria_id: int) -> Categoria | None:
    return db.query(Categoria).filter(Categoria.id == categoria_id).first()


def actualizar_categoria(db: Session, categoria_id: int, payload: CategoriaUpdate) -> Categoria | None:
    categoria = obtener_categoria(db, categoria_id)
    if categoria is None:
        return None
    data = payload.model_dump(exclude_unset=True)
    if "nombre" in data and data["nombre"] is not None:
        categoria.nombre = data["nombre"].strip()
    if "descripcion" in data:
        categoria.descripcion = data["descripcion"].strip() if data["descripcion"] else None
    db.commit()
    db.refresh(categoria)
    return categoria


def eliminar_categoria(db: Session, categoria_id: int) -> bool:
    categoria = obtener_categoria(db, categoria_id)
    if categoria is None:
        return False
    db.delete(categoria)
    db.commit()
    return True
