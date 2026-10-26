from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao lida exclusivamente do ambiente (ou de .env em desenvolvimento).

    Nenhum valor tem padrao para banco, fuso ou segredo: o fuso da escola deve ser
    explicito e nunca depender do fuso da maquina (Aditivo, secao 1), e o segredo
    nunca pode ter um valor conhecido embutido no codigo.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    database_url: str = Field(alias="DATABASE_URL")
    school_timezone: str = Field(alias="SCHOOL_TIMEZONE")
    secret_key: str = Field(alias="SECRET_KEY", min_length=32)

    # Sessao: 8 horas no total e 30 minutos de inatividade (decisao da E4).
    session_absolute_minutes: int = Field(default=480, alias="SESSION_ABSOLUTE_MINUTES", gt=0)
    session_idle_minutes: int = Field(default=30, alias="SESSION_IDLE_MINUTES", gt=0)
    # Em desenvolvimento local sem HTTPS, defina COOKIE_SECURE=false.
    cookie_secure: bool = Field(default=True, alias="COOKIE_SECURE")

    # Protecao contra tentativas abusivas de login.
    login_max_falhas: int = Field(default=5, alias="LOGIN_MAX_FALHAS", gt=0)
    login_janela_minutos: int = Field(default=15, alias="LOGIN_JANELA_MINUTOS", gt=0)
    login_max_falhas_por_ip: int = Field(default=20, alias="LOGIN_MAX_FALHAS_POR_IP", gt=0)

    @field_validator("school_timezone")
    @classmethod
    def _fuso_valido(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Fuso horario invalido: {value!r}") from exc
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()