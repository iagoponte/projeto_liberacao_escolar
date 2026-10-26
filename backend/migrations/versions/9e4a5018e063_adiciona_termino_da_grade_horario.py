"""adiciona termino da grade horario

Revision ID: 9e4a5018e063
Revises: 29bb69698152
Create Date: 2026-10-24 17:37:57.247151
"""
from alembic import op
import sqlalchemy as sa


revision = '9e4a5018e063'
down_revision = '29bb69698152'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "grades_horarios",
        sa.Column(
            "hora_termino",
            sa.Time(),
            nullable=True,
        ),
    )

def downgrade() -> None:
    op.drop_column(
        "grades_horarios",
        "hora_termino",
    )