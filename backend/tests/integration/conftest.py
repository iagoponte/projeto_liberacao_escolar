"""Fixtures de integracao: PostgreSQL real, isolado, migrado pelo Alembic a cada teste."""
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests.conftest import url_do_banco_de_teste

RAIZ_BACKEND = Path(__file__).resolve().parents[2]


def alembic_config() -> Config:
    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "migrations"))
    return cfg


@pytest.fixture(scope="session")
def engine():
    if url_do_banco_de_teste() is None:
        pytest.exit(
            "TEST_DATABASE_URL nao configurada. Defina-a em backend/.env "
            "(veja backend/.env.example) ou como variavel de ambiente.",
            returncode=2,
        )
    eng = create_engine(os.environ["DATABASE_URL"])
    try:
        with eng.connect() as conn:
            nome = conn.execute(text("SELECT current_database()")).scalar()
    except OperationalError as exc:
        causa = str(exc.orig).strip().splitlines()[0] if exc.orig else "erro de conexao"
        pytest.exit(
            f"Nao foi possivel conectar ao banco de teste "
            f"({eng.url.render_as_string(hide_password=True)}): {causa}\n"
            "Confira: o PostgreSQL esta no ar (docker compose up -d db)? "
            "usuario e senha de TEST_DATABASE_URL conferem com o .env da raiz? "
            "o banco liberacao_test existe? (o script de init so roda em volume novo)",
            returncode=2,
        )
    # Protecao critica: o schema inteiro e recriado a cada teste.
    if not nome.endswith("_test"):
        pytest.exit(f"Recusando resetar o banco {nome!r}: o nome deve terminar em _test.")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    """Banco limpo, com todas as migracoes aplicadas."""
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(alembic_config(), "head")
    return engine


@pytest.fixture
def session(db):
    with Session(db) as s:
        yield s