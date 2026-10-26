
from unittest.mock import Mock, PropertyMock, patch

import pytest
from fastapi import HTTPException
from psycopg import errors
from sqlalchemy.exc import IntegrityError

from app.api.matriculas import confirmar_alteracao


def simular_integrity_error(erro_original):
    return IntegrityError(
        statement="INSERT INTO matriculas (...) VALUES (...)",
        params={},
        orig=erro_original,
    )


def test_exclusion_constraint_retorna_409():
    db = Mock()

    erro = errors.ExclusionViolation(
        "conflicting key value violates exclusion constraint"
    )

    db.commit.side_effect = simular_integrity_error(erro)

    with patch.object(
        errors.ExclusionViolation,
        "diag",
        new_callable=PropertyMock,
    ) as diagnostico:
        diagnostico.return_value = Mock(
            constraint_name="ex_matriculas_periodo_sem_sobreposicao"
        )

        with pytest.raises(HTTPException) as exc:
            confirmar_alteracao(db)

    assert exc.value.status_code == 409
    db.rollback.assert_called_once()


def test_outra_exclusion_constraint_nao_e_mascarada():
    db = Mock()

    erro = errors.ExclusionViolation("exclusion violation")
    db.commit.side_effect = simular_integrity_error(erro)

    with patch.object(
        errors.ExclusionViolation,
        "diag",
        new_callable=PropertyMock,
    ) as diagnostico:
        diagnostico.return_value = Mock(
            constraint_name="outra_constraint"
        )

        with pytest.raises(IntegrityError):
            confirmar_alteracao(db)

    db.rollback.assert_called_once()


def test_violacao_inesperada_nao_e_mascarada():
    db = Mock()

    erro = errors.ForeignKeyViolation("foreign key violation")
    db.commit.side_effect = simular_integrity_error(erro)

    with pytest.raises(IntegrityError):
        confirmar_alteracao(db)

    db.rollback.assert_called_once()


def test_commit_valido():
    db = Mock()

    confirmar_alteracao(db)

    db.commit.assert_called_once()
    db.rollback.assert_not_called()
