"""E1/E4 - configuracao vem do ambiente; fuso e segredo sao explicitos e obrigatorios."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

SEGREDO = "x" * 48

BASE = {
    "DATABASE_URL": "postgresql+psycopg://user:senha@localhost:5432/liberacao_dev",
    "SCHOOL_TIMEZONE": "America/Sao_Paulo",
    "SECRET_KEY": SEGREDO,
}


def make(**overrides):
    values = {**BASE, **overrides}
    return Settings(_env_file=None, **values)


def test_carrega_valores_do_ambiente():
    s = make()
    assert s.school_timezone == "America/Sao_Paulo"
    assert s.database_url.startswith("postgresql+psycopg://")


def test_fuso_da_escola_e_obrigatorio(monkeypatch):
    monkeypatch.delenv("SCHOOL_TIMEZONE", raising=False)
    sem_fuso = {k: v for k, v in BASE.items() if k != "SCHOOL_TIMEZONE"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **sem_fuso)


def test_fuso_invalido_e_rejeitado():
    with pytest.raises(ValidationError):
        make(SCHOOL_TIMEZONE="Marte/Olympus")


def test_url_do_banco_e_obrigatoria(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    sem_url = {k: v for k, v in BASE.items() if k != "DATABASE_URL"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **sem_url)


def test_segredo_e_obrigatorio(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    sem_segredo = {k: v for k, v in BASE.items() if k != "SECRET_KEY"}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **sem_segredo)


def test_segredo_curto_e_rejeitado():
    with pytest.raises(ValidationError):
        make(SECRET_KEY="curto")


def test_padroes_de_sessao_e_login():
    s = make()
    assert s.session_absolute_minutes == 480  # 8 horas
    assert s.session_idle_minutes == 30
    assert s.login_max_falhas == 5
    assert s.login_janela_minutos == 15
    assert s.login_max_falhas_por_ip == 20


def test_cookie_de_sessao_e_seguro_por_padrao():
    assert make().cookie_secure is True


def test_valores_de_sessao_devem_ser_positivos():
    with pytest.raises(ValidationError):
        make(SESSION_IDLE_MINUTES=0)
    with pytest.raises(ValidationError):
        make(SESSION_ABSOLUTE_MINUTES=-5)