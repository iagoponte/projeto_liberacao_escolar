import os
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy.orm import Session
from app.domain.estados import Perfil
from app.models import Auditoria, Responsavel, Usuario

RAIZ_BACKEND = Path(__file__).resolve().parents[1]
_URL_PADRAO = "postgresql+psycopg://user:senha@localhost:5432/liberacao_test"


def url_do_banco_de_teste() -> str | None:
    """TEST_DATABASE_URL: variavel de ambiente primeiro, depois backend/.env."""
    return os.environ.get("TEST_DATABASE_URL") or dotenv_values(RAIZ_BACKEND / ".env").get(
        "TEST_DATABASE_URL"
    )


# Os testes usam SEMPRE o banco de teste, nunca o de desenvolvimento.
# Sem TEST_DATABASE_URL, os testes unitarios ainda rodam (nao tocam no banco);
# os de integracao param com uma mensagem clara (ver tests/integration/conftest.py).
os.environ["DATABASE_URL"] = url_do_banco_de_teste() or _URL_PADRAO
os.environ.setdefault("SCHOOL_TIMEZONE", "America/Sao_Paulo")
# Segredo exclusivo dos testes (nunca use este valor fora deles).
os.environ.setdefault("SECRET_KEY", "segredo-somente-para-testes-" + "x" * 20)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture
def criar_responsavel(db, criar_usuario):
    contador = 0

    def _criar(ativo=True):
        nonlocal contador
        contador += 1

        usuario_id = criar_usuario(
            email=f"responsavel{contador}@exemplo.test",
            perfil=Perfil.RESPONSAVEL,
            ativo=ativo,
        )

        with Session(db) as sessao:
            responsavel = Responsavel(
                usuario_id=usuario_id,
                nome_completo=f"Responsavel {contador}",
                ativo=ativo,
            )

            sessao.add(responsavel)
            sessao.flush()
            responsavel_id = responsavel.id
            sessao.commit()

            return responsavel_id

    return _criar
