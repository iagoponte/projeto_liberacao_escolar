"""horarios nas liberacoes e historico

Revision ID: 6bc3203668c7
Revises: 9e4a5018e063
Create Date: 2026-10-25 13:16:57.181962
"""
from alembic import op
import sqlalchemy as sa


revision = '6bc3203668c7'
down_revision = '9e4a5018e063'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "liberacoes",
        sa.Column(
            "horario_inicio_liberacao",
            sa.Time(),
            nullable=True,
        ),
    )

    op.add_column(
        "historico_liberacoes",
        sa.Column(
            "horario_anterior",
            sa.Time(),
            nullable=True,
        ),
    )

    op.add_column(
        "historico_liberacoes",
        sa.Column(
            "horario_novo",
            sa.Time(),
            nullable=True,
        ),
    )

    op.drop_constraint(
        "mudanca_real",
        "historico_liberacoes",
        type_="check",
    )

    op.create_check_constraint(
        "mudanca_real",
        "historico_liberacoes",
        """
        estado_anterior IS NULL
        OR estado_anterior <> novo_estado
        OR horario_anterior IS DISTINCT FROM horario_novo
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        "mudanca_real",
        "historico_liberacoes",
        type_="check",
    )

    op.create_check_constraint(
        "mudanca_real",
        "historico_liberacoes",
        "estado_anterior IS NULL OR estado_anterior <> novo_estado",
    )

    op.drop_column(
        "historico_liberacoes",
        "horario_novo",
    )

    op.drop_column(
        "historico_liberacoes",
        "horario_anterior",
    )

    op.drop_column(
        "liberacoes",
        "horario_inicio_liberacao",
    )