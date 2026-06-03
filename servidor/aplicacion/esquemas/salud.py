from pydantic import BaseModel


class HealthOut(BaseModel):
    estado: str
    database: str
    app_env: str
