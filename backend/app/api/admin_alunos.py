
"""Consultas administrativas de alunos — E4b."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from psycopg import errors

from app.api.deps import Autenticado, exigir_admin, get_db
from app.models import Aluno
from app.schemas.alunos import (
    AlunoAdminResposta,
    AlunoAtualizar,
    AlunoCriar,
)

router = APIRouter(
    prefix="/admin/alunos",
    tags=["Administracao - Alunos"],
)


@router.get("", response_model=list[AlunoAdminResposta])
def listar_alunos(
    db: Session = Depends(get_db),
    _: Autenticado = Depends(exigir_admin),
):
    """Lista alunos cadastrados, inclusive os inativos."""
    consulta = select(Aluno).order_by(Aluno.id)

    return db.scalars(consulta).all()


def obter_aluno_ou_404(
    db: Session,
    aluno_id: int,
) -> Aluno:
    aluno = db.get(Aluno, aluno_id)

    if aluno is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    return aluno



def confirmar_alteracao(db: Session) -> None:
    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        violacao_unicidade = isinstance(
            exc.orig,
            errors.UniqueViolation,
        )

        nome_constraint = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if (
            violacao_unicidade
            and nome_constraint
            == "uq_alunos_matricula_institucional"
        ):
            raise HTTPException(
                status_code=409,
                detail="Matricula institucional ja cadastrada.",
            ) from exc

        raise



@router.post(
    "",
    response_model=AlunoAdminResposta,
    status_code=status.HTTP_201_CREATED,
)
def criar_aluno(
    dados: AlunoCriar,
    db: Session = Depends(get_db),
    _admin: Autenticado = Depends(exigir_admin),
):
    aluno = Aluno(
        nome_completo=dados.nome_completo,
        matricula_institucional=dados.matricula_institucional,
        ativo=True,
    )

    db.add(aluno)
    confirmar_alteracao(db)
    db.refresh(aluno)

    return aluno


@router.get(
    "/{aluno_id}",
    response_model=AlunoAdminResposta,
)
def consultar_aluno(
    aluno_id: int,
    db: Session = Depends(get_db),
    _admin: Autenticado = Depends(exigir_admin),
):
    return obter_aluno_ou_404(db, aluno_id)


@router.patch(
    "/{aluno_id}",
    response_model=AlunoAdminResposta,
)
def atualizar_aluno(
    aluno_id: int,
    dados: AlunoAtualizar,
    db: Session = Depends(get_db),
    _admin: Autenticado = Depends(exigir_admin),
):
    aluno = obter_aluno_ou_404(db, aluno_id)

    alteracoes = dados.model_dump(exclude_unset=True)

    for campo, valor in alteracoes.items():
        setattr(aluno, campo, valor)

    confirmar_alteracao(db)
    db.refresh(aluno)

    return aluno
