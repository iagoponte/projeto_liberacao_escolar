
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from psycopg import errors
from sqlalchemy.exc import IntegrityError

from app.api.anos_letivos import confirmar_alteracao


def simular_erro(origem):
    return IntegrityError(
        statement="INSERT INTO anos_letivos ...",
        params={},
        orig=origem,
    )


def test_violacao_unica_retorna_409():
    db = Mock()
    db.commit.side_effect = simular_erro(
        errors.UniqueViolation("duplicado")
    )

    with pytest.raises(HTTPException) as erro:
        confirmar_alteracao(db)

    assert erro.value.status_code == 409
    db.rollback.assert_called_once()


def test_outra_violacao_nao_e_tratada_como_duplicidade():
    db = Mock()
    db.commit.side_effect = simular_erro(
        errors.ForeignKeyViolation("referencia invalida")
    )

    with pytest.raises(IntegrityError):
        confirmar_alteracao(db)

    db.rollback.assert_called_once()


def test_transacao_valida_e_confirmada():
    db = Mock()

    confirmar_alteracao(db)

    db.commit.assert_called_once()
    db.rollback.assert_not_called()
