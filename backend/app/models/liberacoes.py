from datetime import date, datetime, time
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.estados import Estado, Perfil, TipoAcao
from app.models.base import Base, CarimbosDeTempo, coluna_enum


class Liberacao(CarimbosDeTempo, Base):
    """Estado ATUAL da liberacao de um aluno em uma data. Criada sob demanda."""

    __tablename__ = "liberacoes"
    __table_args__ = (UniqueConstraint("aluno_id", "data"),)

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"))
    data: Mapped[date] = mapped_column(Date)
    estado: Mapped[Estado] = mapped_column(coluna_enum(Estado, "estado"))
    horario_inicio_liberacao: Mapped[time | None] = mapped_column(Time,nullable=True,)
    atualizado_por_usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))


class HistoricoLiberacao(Base):
    """Evento imutavel de mudanca de estado (append-only, protegido por trigger)."""

    __tablename__ = "historico_liberacoes"
    __table_args__ = (
        CheckConstraint(
            """
            estado_anterior IS NULL
            OR estado_anterior <> novo_estado
            OR horario_anterior IS DISTINCT FROM horario_novo
            """,
            name="mudanca_real",
        ),
        CheckConstraint(
            "tipo_acao <> 'CORRECAO_ADMIN' OR (motivo IS NOT NULL AND btrim(motivo) <> '')",
            name="motivo_da_correcao",
        ),
        
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    liberacao_id: Mapped[int] = mapped_column(ForeignKey("liberacoes.id"), index=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("alunos.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    perfil: Mapped[Perfil] = mapped_column(coluna_enum(Perfil, "perfil"))
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    estado_anterior: Mapped[Estado | None] = mapped_column(coluna_enum(Estado, "estado_anterior"))
    novo_estado: Mapped[Estado] = mapped_column(coluna_enum(Estado, "novo_estado"))
    tipo_acao: Mapped[TipoAcao] = mapped_column(coluna_enum(TipoAcao, "tipo_acao"))
    motivo: Mapped[str | None] = mapped_column(Text)
    horario_anterior: Mapped[time | None] = mapped_column(Time, nullable=True,)
    horario_novo: Mapped[time | None] = mapped_column(Time, nullable=True,)


class Auditoria(Base):
    """Eventos administrativos e de seguranca (append-only, protegido por trigger)."""

    __tablename__ = "auditoria"
    __table_args__ = (Index("ix_auditoria_tipo_evento_ocorrido_em", "tipo_evento", "ocorrido_em"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    perfil: Mapped[Perfil | None] = mapped_column(coluna_enum(Perfil, "perfil"))
    tipo_evento: Mapped[str] = mapped_column(String(60))
    entidade: Mapped[str] = mapped_column(String(60))
    entidade_id: Mapped[int | None] = mapped_column(BigInteger)
    detalhes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
