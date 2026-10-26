
"""Schemas de leitura do histórico de liberações."""

from datetime import datetime, time

from pydantic import BaseModel, ConfigDict

from app.domain.estados import Estado, Perfil, TipoAcao


class HistoricoLiberacaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    liberacao_id: int
    aluno_id: int
    usuario_id: int

    perfil: Perfil
    ocorrido_em: datetime
    horario_anterior: time | None = None
    horario_novo: time | None = None

    estado_anterior: Estado | None
    novo_estado: Estado

    tipo_acao: TipoAcao
    motivo: str | None
