from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from aplicacion.nucleo.base_datos import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), unique=True, nullable=False, index=True)
    contacto = Column(String(120), nullable=True)
    telefono = Column(String(40), nullable=True)
    email = Column(String(150), nullable=True)
    direccion = Column(String(200), nullable=True)
    notas = Column(String(300), nullable=True)

    productos = relationship("Producto", back_populates="proveedor")
    movimientos = relationship("Movimiento", back_populates="proveedor")
