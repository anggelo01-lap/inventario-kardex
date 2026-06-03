"""fix movimientos proveedor_id missing

Revision ID: f3a4b5c6d7e8
Revises: e1f2a3b4c5d6
Create Date: 2026-05-08 11:10:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(col["name"] == column for col in inspector.get_columns(table))


def _index_exists(inspector: sa.Inspector, table: str, index: str) -> bool:
    return any(idx["name"] == index for idx in inspector.get_indexes(table))


def _fk_exists(inspector: sa.Inspector, table: str, fk_name: str) -> bool:
    return any(fk["name"] == fk_name for fk in inspector.get_foreign_keys(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "movimientos", "proveedor_id"):
        with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
            batch_op.add_column(sa.Column("proveedor_id", sa.Integer(), nullable=True))

        inspector = sa.inspect(bind)

    if not _index_exists(inspector, "movimientos", "ix_movimientos_proveedor_id"):
        with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
            batch_op.create_index("ix_movimientos_proveedor_id", ["proveedor_id"], unique=False)

        inspector = sa.inspect(bind)

    if not _fk_exists(inspector, "movimientos", "fk_movimientos_proveedor_id_proveedores"):
        with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
            batch_op.create_foreign_key(
                "fk_movimientos_proveedor_id_proveedores",
                "proveedores",
                ["proveedor_id"],
                ["id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
        if _fk_exists(inspector, "movimientos", "fk_movimientos_proveedor_id_proveedores"):
            batch_op.drop_constraint("fk_movimientos_proveedor_id_proveedores", type_="foreignkey")
        if _index_exists(inspector, "movimientos", "ix_movimientos_proveedor_id"):
            batch_op.drop_index("ix_movimientos_proveedor_id")
        if _column_exists(inspector, "movimientos", "proveedor_id"):
            batch_op.drop_column("proveedor_id")
