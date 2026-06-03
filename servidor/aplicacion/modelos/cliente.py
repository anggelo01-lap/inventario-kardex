from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from aplicacion.nucleo.base_datos import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), unique=True, nullable=False, index=True)
    documento = Column(String(40), nullable=True, index=True)
    telefono = Column(String(40), nullable=True)
    email = Column(String(150), nullable=True)
    direccion = Column(String(200), nullable=True)
    notas = Column(String(300), nullable=True)

    movimientos = relationship("Movimiento", back_populates="cliente")
