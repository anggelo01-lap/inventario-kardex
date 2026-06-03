from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from aplicacion.api.dependencias import get_current_user
from aplicacion.nucleo.base_datos import get_db
from aplicacion.excepciones import PasswordInvalidaError, UsuarioDuplicadoError
from aplicacion.modelos.usuario import User
from aplicacion.esquemas.autenticacion import LoginRequest, TokenResponse
from aplicacion.esquemas.usuario import UserCreate, UserMeOut, UserOut
from aplicacion.servicios.servicio_autenticacion import login_user, register_user

router = APIRouter(prefix="/auth", tags=["autenticacion"])


@router.post("/registro", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def registro(payload: UserCreate, db: Session = Depends(get_db)):
    try:
        return register_user(
            db,
            username=payload.username.strip(),
            email=str(payload.email).lower().strip(),
            full_name=payload.full_name.strip(),
            password=payload.password,
        )
    except PasswordInvalidaError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)
    except UsuarioDuplicadoError as exc:
        campo = "nombre de usuario" if exc.campo == "username" else "correo electronico"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un usuario con ese {campo}",
        )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token = login_user(db, payload.username, payload.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserMeOut)
def perfil_actual(usuario: User = Depends(get_current_user)):
    return usuario
