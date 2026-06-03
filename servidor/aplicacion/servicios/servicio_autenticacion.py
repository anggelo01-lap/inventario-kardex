from sqlalchemy import func
from sqlalchemy.orm import Session

from aplicacion.nucleo.seguridad import create_access_token, hash_password, verify_password
from aplicacion.excepciones import UsuarioDuplicadoError
from aplicacion.modelos.usuario import User


def login_user(db: Session, username: str, password: str) -> str | None:
    normalized = username.strip().lower()
    user = (
        db.query(User)
        .filter(
            User.is_active == True,  # noqa: E712
            (func.lower(User.username) == normalized) | (func.lower(User.email) == normalized),
        )
        .first()
    )
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return create_access_token(subject=user.id, extra_claims={"role": user.role})


def register_user(
    db: Session,
    *,
    username: str,
    email: str,
    full_name: str,
    password: str,
) -> User:
    if db.query(User).filter(User.username == username).first():
        raise UsuarioDuplicadoError("username")
    if db.query(User).filter(User.email == email).first():
        raise UsuarioDuplicadoError("email")

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        is_active=True,
        role="usuario",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
