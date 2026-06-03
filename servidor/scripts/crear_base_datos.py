"""Crea la base de datos inventario_kardex si no existe."""
from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_NAME = os.getenv("PG_DATABASE", "inventario_kardex")
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASSWORD = os.getenv("PG_PASSWORD", "7721")
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = int(os.getenv("PG_PORT", "5432"))


def main() -> int:
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname="postgres",
        )
    except Exception as exc:
        print(f"ERROR: no se pudo conectar a PostgreSQL: {exc}")
        print("Verifica que el servicio este activo y la clave del usuario postgres.")
        return 1

    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone():
        print(f"OK: la base '{DB_NAME}' ya existe.")
    else:
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"OK: base '{DB_NAME}' creada.")

    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
