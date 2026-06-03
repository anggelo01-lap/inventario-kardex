"""Copia datos desde PostgreSQL local hacia Neon (DATABASE_URL en .env)."""
from __future__ import annotations

import os
import sys

from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.orm import sessionmaker

from aplicacion.nucleo.configuracion import get_settings, normalize_database_url

DEFAULT_LOCAL_URL = "postgresql+psycopg2://postgres:7721@localhost:5432/inventario_kardex"

TABLES_IN_ORDER = (
    "categorias",
    "proveedores",
    "clientes",
    "usuarios",
    "productos",
    "movimientos",
)


def _engine(url: str):
    return create_engine(normalize_database_url(url), pool_pre_ping=True)


def _row_count(engine, table: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()


def main() -> int:
    settings = get_settings()
    target_url = settings.database_url
    source_url = normalize_database_url(
        os.getenv("SOURCE_DATABASE_URL", DEFAULT_LOCAL_URL)
    )

    source_engine = _engine(source_url)
    target_engine = _engine(target_url)

    try:
        with source_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        with target_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"ERROR de conexion: {exc}")
        return 1

    source_meta = MetaData()
    target_meta = MetaData()
    source_meta.reflect(bind=source_engine)
    target_meta.reflect(bind=target_engine)

    for table in TABLES_IN_ORDER:
        if table not in source_meta.tables or table not in target_meta.tables:
            print(f"ERROR: falta la tabla '{table}'. Ejecuta antes: py scripts/preparar_neon.py")
            return 1

    print("Origen:", source_url.split("@")[-1].split("?")[0])
    print("Destino:", target_url.split("@")[-1].split("?")[0])
    print()
    for table in TABLES_IN_ORDER:
        print(f"  {table}: origen={_row_count(source_engine, table)}, destino={_row_count(target_engine, table)}")

    if "--yes" not in sys.argv:
        print()
        print("Esto BORRA datos en Neon y copia desde local.")
        confirm = input("Escriba SI para continuar: ").strip().upper()
        if confirm != "SI":
            print("Cancelado.")
            return 0

    SourceSession = sessionmaker(bind=source_engine)
    TargetSession = sessionmaker(bind=target_engine)

    try:
        with target_engine.begin() as conn:
            conn.execute(
                text(
                    "TRUNCATE movimientos, productos, usuarios, clientes, proveedores, categorias "
                    "RESTART IDENTITY CASCADE"
                )
            )

        for table_name in TABLES_IN_ORDER:
            src_table = source_meta.tables[table_name]
            with SourceSession() as src_session:
                rows = src_session.execute(select(src_table)).mappings().all()
            if not rows:
                print(f"  -> {table_name}: sin filas")
                continue
            tgt_table = target_meta.tables[table_name]
            with TargetSession() as tgt_session:
                tgt_session.execute(tgt_table.insert(), [dict(row) for row in rows])
                tgt_session.commit()
            print(f"  -> {table_name}: {len(rows)} filas copiadas")

        with target_engine.begin() as conn:
            for table_name in TABLES_IN_ORDER:
                conn.execute(
                    text(
                        f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table_name}', 'id'),
                            COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                            (SELECT COUNT(*) > 0 FROM {table_name})
                        )
                        """
                    )
                )

        print()
        print("Migracion de datos completada.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
