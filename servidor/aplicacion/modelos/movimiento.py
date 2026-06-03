from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from aplicacion.nucleo.base_datos import Base


class Movimiento(Base):
    __tablename__ = "movimientos"
    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_movimientos_cantidad_positiva"),
        CheckConstraint(
            "tipo IN ('entrada', 'salida', 'ajuste')",
            name="ck_movimientos_tipo_valido",
        ),
        CheckConstraint(
            "costo_unitario IS NULL OR costo_unitario >= 0",
            name="ck_movimientos_costo_unitario_no_negativo",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    tipo = Column(String(20), nullable=False)  # entrada | salida | ajuste
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Numeric(12, 2), nullable=True)
    referencia = Column(String(100), nullable=True)
    motivo = Column(String(200), nullable=True)
    observacion = Column(String(300), nullable=True)
    stock_anterior = Column(Integer, nullable=True)
    stock_posterior = Column(Integer, nullable=True)
    fecha_movimiento = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    producto = relationship("Producto", back_populates="movimientos")
    usuario = relationship("User", back_populates="movimientos")
    cliente = relationship("Cliente", back_populates="movimientos")
    proveedor = relationship("Proveedor", back_populates="movimientos")
