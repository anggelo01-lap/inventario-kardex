from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.proveedor import ProveedorCreate, ProveedorOut, ProveedorUpdate
from aplicacion.servicios.servicio_proveedor import (
    actualizar_proveedor,
    crear_proveedor,
    eliminar_proveedor,
    listar_proveedores,
)

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


@router.get("", response_model=list[ProveedorOut])
def get_proveedores(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return listar_proveedores(db)


@router.post("", response_model=ProveedorOut, status_code=status.HTTP_201_CREATED)
def post_proveedor(
    payload: ProveedorCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return crear_proveedor(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un proveedor con ese nombre")


@router.put("/{proveedor_id}", response_model=ProveedorOut)
def put_proveedor(
    proveedor_id: int,
    payload: ProveedorUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        proveedor = actualizar_proveedor(db, proveedor_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un proveedor con ese nombre")
    if proveedor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
    return proveedor


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proveedor(
    proveedor_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not eliminar_proveedor(db, proveedor_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proveedor no encontrado")
