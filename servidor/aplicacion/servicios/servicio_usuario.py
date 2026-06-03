from sqlalchemy.orm import Session

from aplicacion.modelos.usuario import User


def list_usuarios(db: Session) -> list[User]:
    return db.query(User).order_by(User.id.asc()).all()


def get_usuario(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def update_role(db: Session, user_id: int, role: str) -> User | None:
    u = get_usuario(db, user_id)
    if u is None:
        return None
    u.role = role
    db.commit()
    db.refresh(u)
    return u


def update_active(db: Session, user_id: int, is_active: bool) -> User | None:
    u = get_usuario(db, user_id)
    if u is None:
        return None
    u.is_active = is_active
    db.commit()
    db.refresh(u)
    return u
