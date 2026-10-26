
"""Schemas da correção administrativa de liberações."""

from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.domain.estados import Estado


class CorrecaoLiberacaoEntrada(BaseModel):
    estado: Estado
    motivo: str = Field(min_length=1, max_length=1000)

    @field_validator("motivo")
    @classmethod
    def validar_motivo(cls, valor: str) -> str:
        motivo = valor.strip()

        if not motivo:
            raise ValueError(
                "A justificativa da correção é obrigatória."
            )

        return motivo


class CorrecaoLiberacaoResposta(BaseModel):
    aluno_id: int
    data: date
    estado: Estado
