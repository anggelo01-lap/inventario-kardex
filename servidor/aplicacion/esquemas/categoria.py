from pydantic import BaseModel, ConfigDict


class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: str | None = None


class CategoriaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None


class CategoriaOut(BaseModel):
    id: int
    nombre: str
    descripcion: str | None = None

    model_config = ConfigDict(from_attributes=True)
