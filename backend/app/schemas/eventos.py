
"""Schemas de entrada e saída dos eventos escolares."""

from datetime import date, datetime, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

class ModoAplicacaoEvento(StrEnum):
    INFORMATIVO = "INFORMATIVO"
    SUBSTITUICAO_PARCIAL = "SUBSTITUICAO_PARCIAL"
    SUBSTITUICAO_INTEGRAL = "SUBSTITUICAO_INTEGRAL"
    
class EventoCriar(BaseModel):
    turma_id: int
    titulo: str
    data_inicio: date
    data_fim: date

    modo_aplicacao: ModoAplicacaoEvento = ModoAplicacaoEvento.INFORMATIVO
    hora_inicio: time | None = None
    hora_fim: time | None = None

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.data_fim < self.data_inicio:
            raise ValueError(
                "A data final nao pode ser anterior a data inicial."
            )
        if (self.hora_inicio is None) != (self.hora_fim is None):
            raise ValueError(
                "Informe hora_inicio e hora_fim conjuntamente."
            )

        if (
            self.hora_inicio is not None
            and self.hora_fim <= self.hora_inicio
        ):
            raise ValueError(
                "A hora final deve ser posterior a inicial."
            )

        if self.modo_aplicacao == ModoAplicacaoEvento.SUBSTITUICAO_PARCIAL:
            if self.hora_inicio is None:
                raise ValueError(
                    "Substituicao parcial exige horarios."
                )

            if self.data_inicio != self.data_fim:
                raise ValueError(
                    "Substituicao parcial deve ocorrer em uma unica data."
                )
        return self


class EventoResposta(BaseModel):
    id: int
    turma_id: int
    titulo: str
    data_inicio: date
    data_fim: date
    ativo: bool

    modo_aplicacao: ModoAplicacaoEvento
    hora_inicio: time | None
    hora_fim: time | None

    model_config = ConfigDict(from_attributes=True)


class EventoAtualizar(BaseModel):
    turma_id: int | None = Field(default=None, gt=0)
    titulo: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    data_inicio: date | None = None
    data_fim: date | None = None
    modo_aplicacao: ModoAplicacaoEvento | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None

    @model_validator(mode="after")
    def validar_datas_informadas(self):
        if (
            self.data_inicio is not None
            and self.data_fim is not None
            and self.data_fim < self.data_inicio
        ):
            raise ValueError(
                "A data final nao pode ser anterior a inicial."
            )

        return self
