"""Aplica migraciones Alembic contra DATABASE_URL (Neon u otro PostgreSQL)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

from aplicacion.nucleo.configuracion import get_settings, normalize_database_url

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    settings = get_settings()
    url = settings.database_url
    host = url.split("@")[-1].split("?")[0] if "@" in url else url
    print(f"Destino: {host}")

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Conexion OK.")
    except Exception as exc:
        print(f"ERROR de conexion: {exc}")
        print("Revisa DATABASE_URL en servidor/.env (usuario, clave, host, sslmode=require).")
        return 1

    print("Aplicando migraciones (alembic upgrade head)...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        return result.returncode

    print("Listo. Tablas creadas en Neon.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
