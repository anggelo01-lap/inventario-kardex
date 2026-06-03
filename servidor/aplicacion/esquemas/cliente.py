from pydantic import BaseModel, ConfigDict


class ClienteBase(BaseModel):
    nombre: str
    documento: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    notas: str | None = None


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: str | None = None
    documento: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    notas: str | None = None


class ClienteOut(ClienteBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
