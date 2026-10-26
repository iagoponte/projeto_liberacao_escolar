"""Consulta do estado diário de liberação pelo responsável."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel


class SituacaoLiberacaoResponsavel(BaseModel):
    aluno_id: int
    data: date
    estado: Literal[
        "LIBERADO",
        "CANCELADO",
        "SEM_REGISTRO",
    ]
    horario_inicio_liberacao: time | None = None