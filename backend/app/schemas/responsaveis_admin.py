
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class ResponsavelCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome_completo: str = Field(min_length=1, max_length=200)
    email: EmailStr
    senha: str = Field(min_length=12, max_length=128)

    @field_validator("nome_completo")
    @classmethod
    def normalizar_nome(cls, valor: str) -> str:
        nome = valor.strip()

        if not nome:
            raise ValueError("Nome completo nao pode ser vazio.")

        return nome


class ResponsavelAdminResposta(BaseModel):
    id: int
    usuario_id: int
    nome_completo: str
    email: str
    ativo: bool
    usuario_ativo: bool
