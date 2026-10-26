
"""Contratos da API de liberação escolar."""

from datetime import date, time

from pydantic import BaseModel

from app.domain.estados import Acao, Estado


class LiberacaoPedido(BaseModel):
    acao: Acao
    horario_inicio_liberacao: time | None = None

class LiberacaoResposta(BaseModel):
    aluno_id: int
    data: date
    estado: Estado
    horario_inicio_liberacao: time | None
