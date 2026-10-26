
"""Contratos de entrada e saida de anos letivos."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


AnoValido = Annotated[int, Field(strict=True, ge=1, le=9999)]


class AnoLetivoCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ano: AnoValido


class AnoLetivoAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ano: AnoValido | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def validar_atualizacao(self):
        campos = self.model_fields_set

        if not campos:
            raise ValueError("Informe ao menos um campo.")

        if any(getattr(self, campo) is None for campo in campos):
            raise ValueError("Campos informados nao podem ser nulos.")

        return self


class AnoLetivoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ano: int
    ativo: bool
