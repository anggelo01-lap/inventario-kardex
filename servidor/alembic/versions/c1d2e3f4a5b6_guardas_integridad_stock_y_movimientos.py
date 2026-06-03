"""guardas integridad stock y movimientos

Revision ID: c1d2e3f4a5b6
Revises: 081bb97cf639
Create Date: 2026-04-10 18:30:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "081bb97cf639"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_productos_stock_actual_no_negativo",
            "stock_actual >= 0",
        )
        batch_op.create_check_constraint(
            "ck_productos_stock_minimo_no_negativo",
            "stock_minimo >= 0",
        )
        batch_op.create_check_constraint(
            "ck_productos_precio_no_negativo",
            "precio >= 0",
        )
    with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_movimientos_cantidad_positiva",
            "cantidad > 0",
        )
        batch_op.create_check_constraint(
            "ck_movimientos_tipo_valido",
            "tipo IN ('entrada', 'salida', 'ajuste')",
        )
        batch_op.create_check_constraint(
            "ck_movimientos_costo_unitario_no_negativo",
            "costo_unitario IS NULL OR costo_unitario >= 0",
        )


def downgrade() -> None:
    with op.batch_alter_table("movimientos", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_movimientos_costo_unitario_no_negativo", type_="check")
        batch_op.drop_constraint("ck_movimientos_tipo_valido", type_="check")
        batch_op.drop_constraint("ck_movimientos_cantidad_positiva", type_="check")
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_productos_precio_no_negativo", type_="check")
        batch_op.drop_constraint("ck_productos_stock_minimo_no_negativo", type_="check")
        batch_op.drop_constraint("ck_productos_stock_actual_no_negativo", type_="check")
