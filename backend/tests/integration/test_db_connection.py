"""E1 - o banco de TESTE e alcancavel e esta isolado do banco de desenvolvimento."""
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


def test_banco_de_teste_responde(engine):
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1


def test_nome_do_banco_e_de_teste(engine):
    with engine.connect() as conn:
        nome = conn.execute(text("SELECT current_database()")).scalar()
    assert nome.endswith("_test")