
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MatriculaCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aluno_id: int = Field(strict=True, gt=0)
    turma_id: int = Field(strict=True, gt=0)
    ano_letivo_id: int = Field(strict=True, gt=0)
    data_inicio: date
    data_fim: date | None = None

    @model_validator(mode="after")
    def validar_periodo(self):
        if (
            self.data_fim is not None
            and self.data_fim < self.data_inicio
        ):
            raise ValueError(
                "Data de encerramento anterior ao inicio."
            )
        return self


class MatriculaAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_fim: date

    @model_validator(mode="after")
    def validar_campos(self):
        if "data_fim" not in self.model_fields_set:
            raise ValueError(
                "Informe a data de encerramento."
            )
        return self


class MatriculaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    aluno_id: int
    turma_id: int
    ano_letivo_id: int
    data_inicio: date
    data_fim: date | None



from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class TransferenciaCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turma_destino_id: int = Field(strict=True, gt=0)
    data_transferencia: date


class TransferenciaResposta(BaseModel):
    matricula_anterior: MatriculaResposta
    nova_matricula: MatriculaResposta
