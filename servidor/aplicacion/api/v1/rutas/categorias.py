from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user, require_admin
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.categoria import CategoriaCreate, CategoriaOut, CategoriaUpdate
from aplicacion.servicios.servicio_categoria import (
    actualizar_categoria,
    crear_categoria,
    eliminar_categoria,
    listar_categorias,
)

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def post_categoria(
    payload: CategoriaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return crear_categoria(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoria con ese nombre",
        )


@router.get("", response_model=list[CategoriaOut])
def get_categorias(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return listar_categorias(db)


@router.put("/{categoria_id}", response_model=CategoriaOut)
def put_categoria(
    categoria_id: int,
    payload: CategoriaUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        categoria = actualizar_categoria(db, categoria_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una categoria con ese nombre",
        )
    if categoria is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
    return categoria


@router.delete("/{categoria_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_categoria(
    categoria_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    try:
        ok = eliminar_categoria(db, categoria_id)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se puede eliminar: la categoria tiene productos asociados",
        )
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Categoria no encontrada")
