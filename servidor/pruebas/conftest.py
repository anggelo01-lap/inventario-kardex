import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aplicacion.nucleo.base_datos import Base

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg2://postgres:7721@localhost:5432/inventario_kardex_test"
)


def get_test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL).strip()
    if url.lower().startswith("sqlite"):
        raise RuntimeError(
            "SQLite no esta soportado en pruebas. Use TEST_DATABASE_URL con PostgreSQL."
        )
    if not url.lower().startswith("postgresql"):
        raise RuntimeError("TEST_DATABASE_URL debe ser una URL PostgreSQL.")
    return url


@pytest.fixture()
def test_engine():
    engine = create_engine(get_test_database_url(), pool_pre_ping=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def testing_session_local(test_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def db_session(testing_session_local) -> Generator[Session]:
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
