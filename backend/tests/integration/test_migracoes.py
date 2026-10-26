"""E3 - migracoes versionadas: reproduziveis em banco limpo e fieis aos modelos."""
import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.models import Base
from tests.integration.conftest import alembic_config

pytestmark = pytest.mark.integration

TABELAS = {
    "usuarios",
    "alunos",
    "responsaveis",
    "responsaveis_alunos",
    "anos_letivos",
    "turmas",
    "matriculas",
    "eventos_agenda",
    "liberacoes",
    "historico_liberacoes",
    "auditoria",
    "sessoes",
}


def tabelas(engine):
    return set(inspect(engine).get_table_names())


def test_upgrade_em_banco_limpo_cria_todas_as_tabelas(db):
    assert TABELAS <= tabelas(db)


def test_modelos_e_migracao_nao_divergem(db):
    with db.connect() as conn:
        contexto = MigrationContext.configure(conn, opts={"compare_type": True})
        assert compare_metadata(contexto, Base.metadata) == []


def test_downgrade_e_novo_upgrade_sao_reproduziveis(db):
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    assert tabelas(db) - {"alembic_version"} == set()
    command.upgrade(cfg, "head")
    assert TABELAS <= tabelas(db)