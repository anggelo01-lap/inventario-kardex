from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from aplicacion.nucleo.base_datos import Base


class Producto(Base):
    __tablename__ = "productos"
    __table_args__ = (
        CheckConstraint("stock_actual >= 0", name="ck_productos_stock_actual_no_negativo"),
        CheckConstraint("stock_minimo >= 0", name="ck_productos_stock_minimo_no_negativo"),
        CheckConstraint("precio >= 0", name="ck_productos_precio_no_negativo"),
        CheckConstraint(
            "tipo IN ('repuesto', 'producto', 'insumo')",
            name="ck_productos_tipo_valido",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(300), nullable=True)
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    tipo = Column(String(20), nullable=False, server_default="producto")
    image_url = Column(String(500), nullable=True)
    stock_actual = Column(Integer, default=0, nullable=False)
    stock_minimo = Column(Integer, nullable=False, server_default="0")
    precio = Column(Numeric(12, 2), nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    categoria = relationship("Categoria", back_populates="productos")
    proveedor = relationship("Proveedor", back_populates="productos")
    movimientos = relationship("Movimiento", back_populates="producto")
