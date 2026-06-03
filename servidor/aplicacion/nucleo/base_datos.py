from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from aplicacion.nucleo.configuracion import get_settings

settings = get_settings()

_engine_kwargs: dict = {
    "future": True,
    "pool_pre_ping": True,
}

if settings.is_neon:
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 5
    _engine_kwargs["pool_recycle"] = 300
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ping_db() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True
