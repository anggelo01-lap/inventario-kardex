from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from aplicacion.nucleo.base_datos import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    descripcion = Column(String(300), nullable=True)

    productos = relationship("Producto", back_populates="categoria")
