from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MovimientoCreate(BaseModel):
    producto_id: int
    cliente_id: int | None = None
    proveedor_id: int | None = None
    tipo: str
    cantidad: int
    costo_unitario: float | None = None
    referencia: str | None = None
    motivo: str | None = None
    observacion: str | None = None


class MovimientoOut(BaseModel):
    id: int
    producto_id: int
    usuario_id: int
    cliente_id: int | None = None
    proveedor_id: int | None = None
    tipo: str
    cantidad: int
    stock_anterior: int | None = None
    stock_posterior: int | None = None
    fecha_movimiento: datetime

    model_config = ConfigDict(from_attributes=True)


class MovimientoListaOut(BaseModel):
    id: int
    producto_id: int
    producto_codigo: str | None = None
    producto_nombre: str | None = None
    usuario_id: int
    usuario_username: str
    cliente_id: int | None = None
    cliente_nombre: str | None = None
    proveedor_id: int | None = None
    proveedor_nombre: str | None = None
    tipo: str
    cantidad: int
    stock_anterior: int | None = None
    stock_posterior: int | None = None
    motivo: str | None = None
    fecha_movimiento: datetime

    model_config = ConfigDict(from_attributes=True)


class MovimientoPaginaOut(BaseModel):
    items: list[MovimientoListaOut]
    total: int
    page: int
    page_size: int
    total_pages: int
