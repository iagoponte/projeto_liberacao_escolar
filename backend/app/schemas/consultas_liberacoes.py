
"""Schemas para consultas administrativas de liberações."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel


class SituacaoLiberacaoAluno(BaseModel):
    aluno_id: int
    nome_completo: str
    matricula_institucional: str
    turma_id: int
    data: date
    horario_inicio_liberacao: time | None = None

    estado: Literal[
        "SEM_REGISTRO",
        "LIBERADO",
        "CANCELADO",
    ]
