from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from aplicacion.nucleo.seguridad import MAX_PASSWORD_BYTES_BCRYPT, MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=150)
    password: str = Field(
        ...,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        description=(
            f"Entre {MIN_PASSWORD_LENGTH} y {MAX_PASSWORD_LENGTH} caracteres; "
            f"max. {MAX_PASSWORD_BYTES_BCRYPT} bytes UTF-8 (limite bcrypt)."
        ),
    )

    @field_validator("password")
    @classmethod
    def password_utf8_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES_BCRYPT:
            raise ValueError(
                f"La contrasena no puede superar {MAX_PASSWORD_BYTES_BCRYPT} bytes en UTF-8 "
                "(limite de bcrypt). Acorta la contrasena o reduce caracteres multibyte."
            )
        return value


class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: EmailStr
    is_active: bool
    role: str = "usuario"

    model_config = ConfigDict(from_attributes=True)


class UserMeOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "usuario"]


class UserActiveUpdate(BaseModel):
    is_active: bool
