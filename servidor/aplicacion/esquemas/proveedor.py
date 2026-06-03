from pydantic import BaseModel, ConfigDict


class ProveedorBase(BaseModel):
    nombre: str
    contacto: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    notas: str | None = None


class ProveedorCreate(ProveedorBase):
    pass


class ProveedorUpdate(BaseModel):
    nombre: str | None = None
    contacto: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    notas: str | None = None


class ProveedorOut(ProveedorBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
