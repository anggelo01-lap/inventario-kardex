"""clientes proveedores auditoria chatbot

Revision ID: e1f2a3b4c5d6
Revises: d7e8f9a0b1c2
Create Date: 2026-04-11 11:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("documento", sa.String(length=40), nullable=True),
        sa.Column("telefono", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("direccion", sa.String(length=200), nullable=True),
        sa.Column("notas", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clientes_id"), "clientes", ["id"], unique=False)
    op.create_index(op.f("ix_clientes_nombre"), "clientes", ["nombre"], unique=True)
    op.create_index(op.f("ix_clientes_documento"), "clientes", ["documento"], unique=False)

    op.create_table(
        "proveedores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("contacto", sa.String(length=120), nullable=True),
        sa.Column("telefono", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("direccion", sa.String(length=200), nullable=True),
        sa.Column("notas", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proveedores_id"), "proveedores", ["id"], unique=False)
    op.create_index(op.f("ix_proveedores_nombre"), "proveedores", ["nombre"], unique=True)

    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("proveedor_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("image_url", sa.String(length=500), nullable=True))
        batch_op.create_index(op.f("ix_productos_proveedor_id"), ["proveedor_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_productos_proveedor_id_proveedores",
            "proveedores",
            ["proveedor_id"],
            ["id"],
        )

    with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
        batch_op.add_column(sa.Column("cliente_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("motivo", sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column("stock_anterior", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("stock_posterior", sa.Integer(), nullable=True))
        batch_op.create_index(op.f("ix_movimientos_cliente_id"), ["cliente_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_movimientos_cliente_id_clientes",
            "clientes",
            ["cliente_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_movimientos_cliente_id_clientes", type_="foreignkey")
        batch_op.drop_index(op.f("ix_movimientos_cliente_id"))
        batch_op.drop_column("stock_posterior")
        batch_op.drop_column("stock_anterior")
        batch_op.drop_column("motivo")
        batch_op.drop_column("cliente_id")

    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_productos_proveedor_id_proveedores", type_="foreignkey")
        batch_op.drop_index(op.f("ix_productos_proveedor_id"))
        batch_op.drop_column("image_url")
        batch_op.drop_column("proveedor_id")

    op.drop_index(op.f("ix_proveedores_nombre"), table_name="proveedores")
    op.drop_index(op.f("ix_proveedores_id"), table_name="proveedores")
    op.drop_table("proveedores")

    op.drop_index(op.f("ix_clientes_documento"), table_name="clientes")
    op.drop_index(op.f("ix_clientes_nombre"), table_name="clientes")
    op.drop_index(op.f("ix_clientes_id"), table_name="clientes")
    op.drop_table("clientes")
