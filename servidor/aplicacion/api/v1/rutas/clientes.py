from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.cliente import ClienteCreate, ClienteOut, ClienteUpdate
from aplicacion.servicios.servicio_cliente import actualizar_cliente, crear_cliente, eliminar_cliente, listar_clientes

router = APIRouter(prefix="/clientes", tags=["clientes"])


@router.get("", response_model=list[ClienteOut])
def get_clientes(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return listar_clientes(db)


@router.post("", response_model=ClienteOut, status_code=status.HTTP_201_CREATED)
def post_cliente(
    payload: ClienteCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return crear_cliente(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un cliente con ese nombre")


@router.put("/{cliente_id}", response_model=ClienteOut)
def put_cliente(
    cliente_id: int,
    payload: ClienteUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        cliente = actualizar_cliente(db, cliente_id, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un cliente con ese nombre")
    if cliente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
    return cliente


@router.delete("/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cliente(
    cliente_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not eliminar_cliente(db, cliente_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cliente no encontrado")
