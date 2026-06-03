from pydantic import BaseModel, ConfigDict, Field
from aplicacion.esquemas.categoria import CategoriaOut
from aplicacion.esquemas.proveedor import ProveedorOut


class ProductoBase(BaseModel):
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria_id: int
    proveedor_id: int | None = None
    tipo: str
    image_url: str | None = None
    precio: float = Field(ge=0)
    stock_minimo: int = Field(default=0, ge=0)


class ProductoCreate(ProductoBase):
    stock_inicial: int = Field(default=0, ge=0)


class ProductoUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    categoria_id: int | None = None
    proveedor_id: int | None = None
    tipo: str | None = None
    image_url: str | None = None
    precio: float | None = Field(default=None, ge=0)
    stock_minimo: int | None = Field(default=None, ge=0)


class ProductoOut(ProductoBase):
    id: int
    stock_actual: int
    categoria: CategoriaOut | None = None
    proveedor: ProveedorOut | None = None

    model_config = ConfigDict(from_attributes=True)


class ProductoImageUploadOut(BaseModel):
    image_url: str
