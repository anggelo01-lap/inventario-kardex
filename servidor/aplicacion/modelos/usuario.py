from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from aplicacion.nucleo.base_datos import Base


class User(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'usuario')", name="ck_usuarios_role_valido"),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(20), nullable=False, server_default="usuario")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    movimientos = relationship("Movimiento", back_populates="usuario")
