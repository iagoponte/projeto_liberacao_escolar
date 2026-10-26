
from datetime import date, time
from typing import Literal

from pydantic import BaseModel


class AtividadeEfetivaResposta(BaseModel):
    hora_inicio: time
    hora_fim: time
    descricao: str
    tipo: Literal["AULA", "INTERVALO", "EVENTO"]
    origem: Literal["GRADE", "EVENTO"]
    evento_id: int | None


class InformativoEfetivoResposta(BaseModel):
    id: int
    titulo: str
    data_inicio: date
    data_fim: date
    hora_inicio: time | None
    hora_fim: time | None
    modo_aplicacao: str


class AgendaAlunoResposta(BaseModel):
    aluno_id: int
    turma_id: int
    data: date
    atividades: list[AtividadeEfetivaResposta]
    informativos: list[InformativoEfetivoResposta]
