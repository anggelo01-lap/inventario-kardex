from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user, require_admin
from aplicacion.nucleo.base_datos import get_db
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.usuario import UserActiveUpdate, UserOut, UserRoleUpdate
from aplicacion.servicios.servicio_usuario import list_usuarios, update_active, update_role

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UserOut])
def listar_usuarios(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return list_usuarios(db)


@router.patch("/{user_id}/rol", response_model=UserOut)
def cambiar_rol(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    if user_id == current.id and payload.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes quitarte el rol de administrador a ti mismo",
        )
    u = update_role(db, user_id, payload.role)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return u


@router.patch("/{user_id}/activo", response_model=UserOut)
def cambiar_activo(
    user_id: int,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_admin),
):
    if user_id == current.id and not payload.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario",
        )
    u = update_active(db, user_id, payload.is_active)
    if u is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return u
