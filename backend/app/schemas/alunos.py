
"""Contratos de resposta dos endpoints de alunos."""

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator



class AlunoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome_completo: str
    matricula_institucional: str | None


class AlunoAdminResposta(AlunoResposta):
    ativo: bool

class AlunoCriar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome_completo: str = Field(
        min_length=1,
        max_length=200,
    )
    matricula_institucional: str | None = None
    
    @field_validator("nome_completo")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        return normalizar_nome(valor)

    @field_validator("matricula_institucional")
    @classmethod
    def validar_matricula(
        cls, valor: str | None
    ) -> str | None:
        return normalizar_matricula(valor)



class AlunoAtualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome_completo: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    matricula_institucional: str | None = None
    ativo: bool | None = None

    @model_validator(mode="after")
    def validar_atualizacao(self):
        campos = self.model_fields_set

        if not campos:
            raise ValueError(
                "Informe ao menos um campo para atualizar."
            )

        if "nome_completo" in campos and self.nome_completo is None:
            raise ValueError("Nome completo nao pode ser nulo.")

        if "ativo" in campos and self.ativo is None:
            raise ValueError("Situacao ativa nao pode ser nula.")

        return self
    
    
    @field_validator("nome_completo")
    @classmethod
    def validar_nome(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return normalizar_nome(valor)

    @field_validator("matricula_institucional")
    @classmethod
    def validar_matricula(
        cls, valor: str | None
    ) -> str | None:
        return normalizar_matricula(valor)



def normalizar_nome(valor: str) -> str:
    nome = valor.strip()

    if not nome:
        raise ValueError(
            "Nome completo nao pode conter apenas espacos."
        )

    return nome


def normalizar_matricula(
    valor: str | None,
) -> str | None:
    if valor is None:
        return None

    matricula = valor.strip()
    return matricula or None
