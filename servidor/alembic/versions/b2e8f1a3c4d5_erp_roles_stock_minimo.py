"""erp roles y stock_minimo

Revision ID: b2e8f1a3c4d5
Revises: 6064ad7f2a68
Create Date: 2026-04-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2e8f1a3c4d5"
down_revision: Union[str, Sequence[str], None] = "6064ad7f2a68"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("role", sa.String(length=20), server_default="usuario", nullable=False),
    )
    op.add_column(
        "productos",
        sa.Column("stock_minimo", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("productos", "stock_minimo")
    op.drop_column("usuarios", "role")
