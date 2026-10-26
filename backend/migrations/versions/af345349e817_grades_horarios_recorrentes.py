"""grades horarias recorrentes

Revision ID: af345349e817
Revises: 33194f95d636
Create Date: 2026-10-24 15:19:03.208889
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = 'af345349e817'
down_revision = '33194f95d636'
branch_labels = None
depends_on = None



def upgrade() -> None:
    op.create_table(
        "grades_horarios",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "turma_id",
            sa.Integer(),
            sa.ForeignKey("turmas.id"),
            nullable=False,
        ),
        sa.Column(
            "vigente_desde",
            sa.Date(),
            nullable=False,
        ),
        sa.Column(
            "vigente_ate",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "horarios",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "vigente_ate IS NULL OR vigente_ate >= vigente_desde",
            name="ck_grade_periodo_valido",
        ),
    )

    op.create_index(
        "ix_grades_horarios_turma_id",
        "grades_horarios",
        ["turma_id"],
    )

    op.create_index(
        "uq_grade_aberta_por_turma",
        "grades_horarios",
        ["turma_id"],
        unique=True,
        postgresql_where=sa.text("vigente_ate IS NULL"),
    )

    op.create_table(
        "aulas_recorrentes",
        sa.Column(
            "id",
            sa.Integer(),
            sa.Identity(),
            primary_key=True,
        ),
        sa.Column(
            "grade_id",
            sa.Integer(),
            sa.ForeignKey(
                "grades_horarios.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "dia_semana",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "hora_inicio",
            sa.Time(),
            nullable=False,
        ),
        sa.Column(
            "descricao",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "tipo",
            sa.String(length=20),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dia_semana BETWEEN 0 AND 4",
            name="ck_aula_dia_semana",
        ),
        sa.CheckConstraint(
            "tipo IN ('AULA', 'INTERVALO')",
            name="ck_aula_tipo",
        ),
    )

    op.create_index(
        "ix_aulas_recorrentes_grade_id",
        "aulas_recorrentes",
        ["grade_id"],
    )

    op.create_index(
        "uq_aula_grade_dia_hora",
        "aulas_recorrentes",
        ["grade_id", "dia_semana", "hora_inicio"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_aula_grade_dia_hora",
        table_name="aulas_recorrentes",
    )
    op.drop_index(
        "ix_aulas_recorrentes_grade_id",
        table_name="aulas_recorrentes",
    )
    op.drop_table("aulas_recorrentes")

    op.drop_index(
        "uq_grade_aberta_por_turma",
        table_name="grades_horarios",
    )
    op.drop_index(
        "ix_grades_horarios_turma_id",
        table_name="grades_horarios",
    )
    op.drop_table("grades_horarios")
