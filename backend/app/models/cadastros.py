from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.estados import Perfil
from app.domain.turno import Turno
from app.models.base import Base, CarimbosDeTempo, coluna_enum


class Usuario(CarimbosDeTempo, Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[Perfil] = mapped_column(coluna_enum(Perfil, "perfil"))
    ativo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class Aluno(CarimbosDeTempo, Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    nome_completo: Mapped[str] = mapped_column(String(200))
    matricula_institucional: Mapped[str | None] = mapped_column(String(50), unique=True)
    ativo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class Responsavel(CarimbosDeTempo, Base):
    __tablename__ = "responsaveis"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True)
    nome_completo: Mapped[str] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class ResponsavelAluno(Base):
    """Vinculo com vigencia. Revogar = preencher `revogado_em`; nunca apagar."""

    __tablename__ = "responsaveis_alunos"
    __table_args__ = (
        CheckConstraint(
            "revogado_em IS NULL OR revogado_em > vigente_desde", name="revogacao_apos_inicio"
        ),
        # Um unico vinculo ATIVO por par; o historico de vinculos revogados e preservado.
        Index(
            "uq_responsaveis_alunos_vinculo_ativo",
            "responsavel_id",
            "aluno_id",
            unique=True,
            postgresql_where=text("revogado_em IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    responsavel_id: Mapped[int] = mapped_column(ForeignKey("responsaveis.id"))
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnoLetivo(Base):
    __tablename__ = "anos_letivos"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    ano: Mapped[int] = mapped_column(unique=True)
    ativo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class Turma(CarimbosDeTempo, Base):
    __tablename__ = "turmas"
    __table_args__ = (
        UniqueConstraint("ano_letivo_id", "identificacao"),
        # Alvo da FK composta de matriculas: garante turma e ano letivo coerentes.
        UniqueConstraint("id", "ano_letivo_id"),
        CheckConstraint("ano_escolar > 0", name="ano_escolar_positivo"),
        CheckConstraint(
            "modo_aplicacao IN ("
            "'INFORMATIVO', "
            "'SUBSTITUICAO_PARCIAL', "
            "'SUBSTITUICAO_INTEGRAL'"
            ")",
            name="ck_evento_modo_aplicacao",
        ),
        CheckConstraint(
            "(hora_inicio IS NULL AND hora_fim IS NULL) "
            "OR "
            "(hora_inicio IS NOT NULL AND hora_fim IS NOT NULL "
            "AND hora_fim > hora_inicio)",
            name="ck_evento_intervalo_horario",
        ),
        CheckConstraint(
            "modo_aplicacao <> 'SUBSTITUICAO_PARCIAL' "
            "OR "
            "(hora_inicio IS NOT NULL AND hora_fim IS NOT NULL "
            "AND data_inicio = data_fim)",
            name="ck_evento_parcial_com_horario",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    identificacao: Mapped[str] = mapped_column(String(50))
    ano_escolar: Mapped[int]
    ano_letivo_id: Mapped[int] = mapped_column(ForeignKey("anos_letivos.id"))
    turno: Mapped[Turno] = mapped_column(coluna_enum(Turno, "turno"))
    ativo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))


class Matricula(CarimbosDeTempo, Base):
    """Aluno em uma turma durante um periodo. Mudar de turma = fechar e abrir outra."""

    __tablename__ = "matriculas"
    __table_args__ = (
        ForeignKeyConstraint(
            ["turma_id", "ano_letivo_id"], ["turmas.id", "turmas.ano_letivo_id"]
        ),
        CheckConstraint("data_fim IS NULL OR data_fim >= data_inicio", name="periodo_valido"),
        Index(
            "uq_matriculas_aberta_por_aluno_e_ano",
            "aluno_id",
            "ano_letivo_id",
            unique=True,
            postgresql_where=text("data_fim IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"))
    turma_id: Mapped[int] = mapped_column(index=True)
    ano_letivo_id: Mapped[int]
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date | None] = mapped_column(Date)


class EventoAgenda(CarimbosDeTempo, Base):
    __tablename__ = "eventos_agenda"
    __table_args__ = (
        CheckConstraint("data_fim >= data_inicio", name="periodo_valido"),
        Index("ix_eventos_agenda_turma_periodo", "turma_id", "data_inicio", "data_fim"),
    )

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    turma_id: Mapped[int] = mapped_column(ForeignKey("turmas.id"))
    titulo: Mapped[str] = mapped_column(String(200))
    data_inicio: Mapped[date] = mapped_column(Date)
    data_fim: Mapped[date] = mapped_column(Date)
    ativo: Mapped[bool] = mapped_column(default=True, server_default=text("true"))
    
    modo_aplicacao: Mapped[str] = mapped_column(
    String(30),
    nullable=False,
    default="INFORMATIVO",
    server_default=text("'INFORMATIVO'"),
    )

    hora_inicio: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    hora_fim: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )