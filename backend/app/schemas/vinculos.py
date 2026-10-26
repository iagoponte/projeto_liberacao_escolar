
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class VinculoCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    responsavel_id: int = Field(strict=True, gt=0)
    aluno_id: int = Field(strict=True, gt=0)


class VinculoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    responsavel_id: int
    aluno_id: int
    vigente_desde: datetime
    revogado_em: datetime | None
    ativo: bool
