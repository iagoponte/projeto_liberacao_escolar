"""E4 - os CHECK do banco devem listar exatamente os valores dos enums do Python.

O `alembic check` nao compara CHECK; sem este teste, acrescentar um valor ao enum
e esquecer a migracao passaria despercebido.
"""
import re

import pytest
from sqlalchemy import Enum, text

from app.models import Base

pytestmark = pytest.mark.integration


def colunas_enum():
    for tabela in Base.metadata.sorted_tables:
        for coluna in tabela.columns:
            if isinstance(coluna.type, Enum):
                yield tabela.name, coluna.name, coluna.type


CASOS = list(colunas_enum())


def test_existem_colunas_enum_para_verificar():
    assert len(CASOS) >= 8


@pytest.mark.parametrize(
    ("tabela", "coluna", "tipo"), CASOS, ids=[f"{t}.{c}" for t, c, _ in CASOS]
)
def test_check_do_banco_lista_os_valores_do_enum(db, tabela, coluna, tipo):
    nome = f"ck_{tabela}_{tipo.name}"
    with db.connect() as conn:
        definicao = conn.execute(
            text("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :n"),
            {"n": nome},
        ).scalar()
    assert definicao is not None, f"CHECK {nome} nao existe no banco"
    valores_no_banco = set(re.findall(r"'([A-Z_]+)'", definicao))
    assert valores_no_banco == set(tipo.enums)