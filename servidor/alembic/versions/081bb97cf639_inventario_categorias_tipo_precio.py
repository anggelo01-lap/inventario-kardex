"""inventario categorias tipo precio

Revision ID: 081bb97cf639
Revises: b2e8f1a3c4d5
Create Date: 2026-04-10 11:33:07.763815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "081bb97cf639"
down_revision: Union[str, Sequence[str], None] = "b2e8f1a3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("descripcion", sa.String(length=300), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_categorias_id"), "categorias", ["id"], unique=False)
    op.create_index(op.f("ix_categorias_nombre"), "categorias", ["nombre"], unique=True)
    op.execute(
        sa.text(
            "INSERT INTO categorias (nombre, descripcion) VALUES ('General', 'Categoria inicial para migracion')"
        )
    )
    op.add_column("productos", sa.Column("categoria_id", sa.Integer(), nullable=True))
    op.add_column(
        "productos",
        sa.Column("tipo", sa.String(length=20), server_default="producto", nullable=False),
    )
    op.add_column(
        "productos",
        sa.Column("precio", sa.Numeric(precision=12, scale=2), server_default="0", nullable=False),
    )
    op.execute(sa.text("UPDATE productos SET categoria_id = 1 WHERE categoria_id IS NULL"))
    op.execute(sa.text("UPDATE productos SET precio = COALESCE(precio_referencia, 0)"))
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.alter_column("categoria_id", existing_type=sa.Integer(), nullable=False)
        batch_op.create_index(op.f("ix_productos_categoria_id"), ["categoria_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_productos_categoria_id_categorias",
            "categorias",
            ["categoria_id"],
            ["id"],
        )
        batch_op.drop_column("precio_referencia")


def downgrade() -> None:
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.add_column(
            sa.Column(
                "precio_referencia",
                sa.NUMERIC(precision=12, scale=2),
                autoincrement=False,
                nullable=True,
            )
        )
    op.execute(sa.text("UPDATE productos SET precio_referencia = precio"))
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.drop_constraint("fk_productos_categoria_id_categorias", type_="foreignkey")
        batch_op.drop_index(op.f("ix_productos_categoria_id"))
        batch_op.drop_column("precio")
        batch_op.drop_column("tipo")
        batch_op.drop_column("categoria_id")
    op.drop_index(op.f("ix_categorias_nombre"), table_name="categorias")
    op.drop_index(op.f("ix_categorias_id"), table_name="categorias")
    op.drop_table("categorias")
