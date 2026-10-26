
from unittest.mock import Mock, PropertyMock, patch

import pytest
from fastapi import HTTPException
from psycopg import errors
from sqlalchemy.exc import IntegrityError

from app.api.admin_alunos import confirmar_alteracao


def simular_integrity_error(
    erro_original: Exception,
) -> IntegrityError:
    return IntegrityError(
        statement="INSERT INTO alunos (...) VALUES (...)",
        params={},
        orig=erro_original,
    )


def test_matricula_duplicada_retorna_409():
    db = Mock()

    erro = errors.UniqueViolation(
        "duplicate key value violates unique constraint"
    )

    db.commit.side_effect = simular_integrity_error(erro)

    with patch.object(
        errors.UniqueViolation,
        "diag",
        new_callable=PropertyMock,
    ) as diagnostico:
        diagnostico.return_value = Mock(
            constraint_name="uq_alunos_matricula_institucional"
        )

        with pytest.raises(HTTPException) as exc:
            confirmar_alteracao(db)

    assert exc.value.status_code == 409
    db.rollback.assert_called_once()


def test_outra_violacao_unicidade_nao_e_mascarada():
    db = Mock()

    erro = errors.UniqueViolation(
        "duplicate key value violates unique constraint"
    )

    db.commit.side_effect = simular_integrity_error(erro)

    with patch.object(
        errors.UniqueViolation,
        "diag",
        new_callable=PropertyMock,
    ) as diagnostico:
        diagnostico.return_value = Mock(
            constraint_name="outra_constraint"
        )

        with pytest.raises(IntegrityError):
            confirmar_alteracao(db)

    db.rollback.assert_called_once()


def test_violacao_chave_estrangeira_nao_e_mascarada():
    db = Mock()

    erro = errors.ForeignKeyViolation(
        "foreign key violation"
    )

    db.commit.side_effect = simular_integrity_error(erro)

    with pytest.raises(IntegrityError):
        confirmar_alteracao(db)

    db.rollback.assert_called_once()


def test_commit_sem_erro():
    db = Mock()

    confirmar_alteracao(db)

    db.commit.assert_called_once()
    db.rollback.assert_not_called()
