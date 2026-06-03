"""guardas tipo producto y role usuario

Revision ID: d7e8f9a0b1c2
Revises: c1d2e3f4a5b6
Create Date: 2026-04-10 19:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_productos_tipo_valido",
            "tipo IN ('repuesto', 'producto', 'insumo')",
        )
    with op.batch_alter_table("usuarios", recreate="auto") as batch_op:
        batch_op.create_check_constraint(
            "ck_usuarios_role_valido",
            "role IN ('admin', 'usuario')",
        )


def downgrade() -> None:
    with op.batch_alter_table("usuarios", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_usuarios_role_valido", type_="check")
    with op.batch_alter_table("productos", recreate="auto") as batch_op:
        batch_op.drop_constraint("ck_productos_tipo_valido", type_="check")
