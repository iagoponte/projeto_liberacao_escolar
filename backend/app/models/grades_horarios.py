
"""Grades semanais versionadas por turma."""

from datetime import date, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GradeHorario(Base):
    __tablename__ = "grades_horarios"

    __table_args__ = (
        CheckConstraint(
            "vigente_ate IS NULL OR vigente_ate >= vigente_desde",
            name="ck_grade_periodo_valido",
        ),
        Index(
            "uq_grade_aberta_por_turma",
            "turma_id",
            unique=True,
            postgresql_where=text("vigente_ate IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(
        Identity(),
        primary_key=True,
    )

    turma_id: Mapped[int] = mapped_column(
        ForeignKey("turmas.id"),
        nullable=False,
        index=True,
    )

    vigente_desde: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    vigente_ate: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    # Preserva todas as linhas de horario, inclusive
    # aquelas sem aula em determinados dias.
    horarios: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    
    hora_termino: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )


class AulaRecorrente(Base):
    __tablename__ = "aulas_recorrentes"

    __table_args__ = (
        CheckConstraint(
            "dia_semana BETWEEN 0 AND 4",
            name="ck_aula_dia_semana",
        ),
        CheckConstraint(
            "tipo IN ('AULA', 'INTERVALO')",
            name="ck_aula_tipo",
        ),
        Index(
            "uq_aula_grade_dia_hora",
            "grade_id",
            "dia_semana",
            "hora_inicio",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(
        Identity(),
        primary_key=True,
    )

    grade_id: Mapped[int] = mapped_column(
        ForeignKey("grades_horarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    dia_semana: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    hora_inicio: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    descricao: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
