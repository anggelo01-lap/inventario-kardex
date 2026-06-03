import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from aplicacion.nucleo.configuracion import get_settings
from aplicacion.excepciones import PasswordInvalidaError

settings = get_settings()

_JWT_PATTERN = re.compile(r"^[A-Za-z0-9_-]+=*\.[A-Za-z0-9_-]+=*\.[A-Za-z0-9_-]+=*$")

BCRYPT_ROUNDS = 12

MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 50
MAX_PASSWORD_BYTES_BCRYPT = 72


def _password_utf8_byte_length(password: str) -> int:
    return len(password.encode("utf-8"))


def assert_password_hashable(password: str) -> None:
    if not isinstance(password, str):
        raise PasswordInvalidaError("La contrasena debe ser texto.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordInvalidaError(
            f"La contrasena debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordInvalidaError(
            f"La contrasena no puede superar {MAX_PASSWORD_LENGTH} caracteres."
        )
    byte_len = _password_utf8_byte_length(password)
    if byte_len > MAX_PASSWORD_BYTES_BCRYPT:
        raise PasswordInvalidaError(
            "La contrasena es demasiado larga en bytes UTF-8 (limite de bcrypt: 72 bytes). "
            "Usa menos caracteres o evita secuencias muy largas en Unicode."
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not isinstance(plain_password, str):
        return False
    if _password_utf8_byte_length(plain_password) > MAX_PASSWORD_BYTES_BCRYPT:
        return False
    try:
        hashed_bytes = hashed_password.encode("utf-8") if isinstance(hashed_password, str) else hashed_password
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_bytes)
    except (ValueError, TypeError):
        return False


def hash_password(password: str) -> str:
    assert_password_hashable(password)
    try:
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
        ).decode("utf-8")
    except ValueError as exc:
        raise PasswordInvalidaError(
            "No se pudo procesar la contrasena de forma segura. Comprueba longitud y caracteres."
        ) from exc


def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    payload: dict[str, Any] = {"sub": str(subject)}
    if extra_claims:
        for key, value in extra_claims.items():
            if value is not None:
                payload[key] = value
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def normalize_access_token_value(value: str) -> str:
    if not value or not isinstance(value, str):
        return ""
    raw = value.strip().lstrip("\ufeff")
    while raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        raw = raw[1:-1].strip()
    if _JWT_PATTERN.fullmatch(raw):
        return raw
    for part in raw.split():
        if _JWT_PATTERN.fullmatch(part):
            return part
    return raw


def decode_access_token(token: str) -> dict | None:
    clean = normalize_access_token_value(token)
    if not clean:
        return None
    try:
        return jwt.decode(clean, settings.secret_key, algorithms=[settings.algorithm], options={"verify_exp": False})
    except JWTError:
        return None
