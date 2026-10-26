from pydantic import BaseModel, ConfigDict, Field

from app.domain.estados import Perfil


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=256)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    perfil: Perfil


class SessaoOut(BaseModel):
    usuario: UsuarioOut
    csrf_token: str