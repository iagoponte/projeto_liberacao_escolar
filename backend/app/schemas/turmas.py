
"""Contratos de entrada e saida de turmas — E5.1-B."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.turno import Turno


class TurmaCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identificacao: str = Field(min_length=1, max_length=50)
    ano_escolar: int = Field(strict=True, gt=0)
    ano_letivo_id: int = Field(strict=True, gt=0)
    turno: Turno


class TurmaAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identificacao: str | None = Field(
        default=None, min_length=1, max_length=50
    )
    ano_escolar: int | None = Field(default=None, strict=True, gt=0)
    turno: Turno | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def validar_atualizacao(self):
        campos = self.model_fields_set

        if not campos:
            raise ValueError("Informe ao menos um campo.")

        if any(getattr(self, campo) is None for campo in campos):
            raise ValueError("Campos informados nao podem ser nulos.")

        return self


class TurmaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    identificacao: str
    ano_escolar: int
    ano_letivo_id: int
    turno: Turno
    ativo: bool
