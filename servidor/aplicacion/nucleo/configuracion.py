from functools import lru_cache
from pathlib import Path
from typing import List
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "change_me_super_secret_key"
DEFAULT_DATABASE_URL = "postgresql+psycopg2://postgres:7721@localhost:5432/inventario_kardex"
DEVELOPMENT_ENVS = {"development", "dev", "local", "test"}
DEFAULT_CORS_ORIGINS = (
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "https://inventario-kardex.vercel.app",
    "https://inventario-kardex-k0bat6nn2-a44829753-4055s-projects.vercel.app",
)


def normalize_database_url(url: str) -> str:
    """Normaliza URLs de Neon u otros hosts PostgreSQL para SQLAlchemy + psycopg2."""
    normalized = url.strip()
    if normalized.startswith("postgres://"):
        normalized = "postgresql+psycopg2://" + normalized[len("postgres://") :]
    elif normalized.startswith("postgresql://") and "+psycopg2" not in normalized.split("://", 1)[0]:
        normalized = "postgresql+psycopg2://" + normalized[len("postgresql://") :]

    parsed = urlparse(normalized)
    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query, keep_blank_values=True)

    if host.endswith(".neon.tech") or host.endswith(".neon.tech."):
        query.setdefault("sslmode", ["require"])

    flat_query = {key: values[-1] for key, values in query.items() if values}
    rebuilt = parsed._replace(query=urlencode(flat_query))
    return urlunparse(rebuilt)


class Settings(BaseSettings):
    app_name: str = "Inventario Kardex API"
    app_env: str = "development"
    app_debug: bool = True
    app_log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    database_url: str = DEFAULT_DATABASE_URL
    backend_cors_origins: str = ",".join(DEFAULT_CORS_ORIGINS)
    media_root: str = "subidas"
    media_url_prefix: str = "/subidas"
    max_image_upload_mb: int = 5

    admin_username: str = "admin"
    admin_email: str = "admin@example.com"
    admin_full_name: str = "Administrador"
    admin_password: str = "Admin12345"

    ai_enabled: bool = False
    ai_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: int = 8
    ai_max_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("app_env")
    @classmethod
    def normalize_app_env(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str) -> str:
        url = normalize_database_url(value)
        lowered = url.lower()
        if lowered.startswith("sqlite"):
            raise ValueError(
                "SQLite no esta soportado. Configure DATABASE_URL con PostgreSQL."
            )
        if not lowered.startswith("postgresql"):
            raise ValueError("DATABASE_URL debe usar PostgreSQL.")
        return url

    @model_validator(mode="after")
    def validate_secure_configuration(self) -> "Settings":
        if self.app_env not in DEVELOPMENT_ENVS:
            if self.app_debug:
                raise ValueError("APP_DEBUG debe ser false fuera de desarrollo.")
            if self.secret_key == DEFAULT_SECRET_KEY:
                raise ValueError("SECRET_KEY debe configurarse con un valor seguro fuera de desarrollo.")
            if self.database_url == DEFAULT_DATABASE_URL:
                raise ValueError("DATABASE_URL debe configurarse fuera de desarrollo.")
        return self

    @property
    def cors_origins_list(self) -> List[str]:
        origins: List[str] = []
        seen: set[str] = set()
        configured_origins = [origin.strip().rstrip("/") for origin in self.backend_cors_origins.split(",")]

        for origin in [*DEFAULT_CORS_ORIGINS, *configured_origins]:
            normalized = origin.strip().rstrip("/")
            if normalized and normalized not in seen:
                seen.add(normalized)
                origins.append(normalized)
        return origins

    @property
    def is_development(self) -> bool:
        return self.app_env in DEVELOPMENT_ENVS

    @property
    def is_neon(self) -> bool:
        return ".neon.tech" in self.database_url.lower()

    @property
    def backend_root_path(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def media_root_path(self) -> Path:
        base = Path(self.media_root)
        if base.is_absolute():
            return base
        return self.backend_root_path / base

    @property
    def productos_media_path(self) -> Path:
        return self.media_root_path / "productos"


@lru_cache
def get_settings() -> Settings:
    return Settings()
