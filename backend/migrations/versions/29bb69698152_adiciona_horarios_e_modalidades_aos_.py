"""adiciona horarios e modalidades aos eventos

Revision ID: 29bb69698152
Revises: af345349e817
Create Date: 2026-10-24 16:49:39.287940
"""
from alembic import op
import sqlalchemy as sa


revision = '29bb69698152'
down_revision = 'af345349e817'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "eventos_agenda",
        sa.Column(
            "modo_aplicacao",
            sa.String(length=30),
            nullable=False,
            server_default="INFORMATIVO",
        ),
    )

    op.add_column(
        "eventos_agenda",
        sa.Column(
            "hora_inicio",
            sa.Time(),
            nullable=True,
        ),
    )

    op.add_column(
        "eventos_agenda",
        sa.Column(
            "hora_fim",
            sa.Time(),
            nullable=True,
        ),
    )

    op.create_check_constraint(
        "ck_evento_modo_aplicacao",
        "eventos_agenda",
        "modo_aplicacao IN ("
        "'INFORMATIVO', "
        "'SUBSTITUICAO_PARCIAL', "
        "'SUBSTITUICAO_INTEGRAL'"
        ")",
    )

    op.create_check_constraint(
        "ck_evento_intervalo_horario",
        "eventos_agenda",
        "(hora_inicio IS NULL AND hora_fim IS NULL) "
        "OR "
        "(hora_inicio IS NOT NULL AND hora_fim IS NOT NULL "
        "AND hora_fim > hora_inicio)",
    )

    op.create_check_constraint(
        "ck_evento_parcial_com_horario",
        "eventos_agenda",
        "modo_aplicacao <> 'SUBSTITUICAO_PARCIAL' "
        "OR "
        "(hora_inicio IS NOT NULL AND hora_fim IS NOT NULL "
        "AND data_inicio = data_fim)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_evento_parcial_com_horario",
        "eventos_agenda",
        type_="check",
    )

    op.drop_constraint(
        "ck_evento_intervalo_horario",
        "eventos_agenda",
        type_="check",
    )

    op.drop_constraint(
        "ck_evento_modo_aplicacao",
        "eventos_agenda",
        type_="check",
    )

    op.drop_column("eventos_agenda", "hora_fim")
    op.drop_column("eventos_agenda", "hora_inicio")
    op.drop_column("eventos_agenda", "modo_aplicacao")