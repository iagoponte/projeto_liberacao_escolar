"""impedir sobreposicao de matriculas

Revision ID: 33194f95d636
Revises: 0002
Create Date: 2026-10-23 18:52:22.280802
"""
from alembic import op
import sqlalchemy as sa


revision = '33194f95d636'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS btree_gist"
    )

    op.execute("""
        ALTER TABLE matriculas
        ADD CONSTRAINT ex_matriculas_periodo_sem_sobreposicao
        EXCLUDE USING gist (
            aluno_id WITH =,
            ano_letivo_id WITH =,
            daterange(
                data_inicio,
                data_fim,
                '[]'
            ) WITH &&
        )
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE matriculas
        DROP CONSTRAINT IF EXISTS
        ex_matriculas_periodo_sem_sobreposicao
    """)