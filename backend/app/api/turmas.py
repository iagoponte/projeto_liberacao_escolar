
"""Endpoints administrativos de turmas — E5.1-B."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import errors
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db
from app.models import AnoLetivo, Turma
from app.schemas.turmas import (
    TurmaAtualizar,
    TurmaCriar,
    TurmaResposta,
)

router = APIRouter(
    prefix="/admin/turmas",
    tags=["Administracao - Turmas"],
    dependencies=[Depends(exigir_admin)],
)


def obter_turma_ou_404(db: Session, turma_id: int) -> Turma:
    turma = db.get(Turma, turma_id)

    if turma is None:
        raise HTTPException(
            status_code=404,
            detail="Turma nao encontrada.",
        )

    return turma


def confirmar_alteracao(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()

        if isinstance(exc.orig, errors.UniqueViolation):
            raise HTTPException(
                status_code=409,
                detail="Ja existe turma com essa identificacao no ano letivo.",
            ) from exc

        raise


@router.post(
    "",
    response_model=TurmaResposta,
    status_code=status.HTTP_201_CREATED,
)
def criar_turma(
    dados: TurmaCriar,
    db: Session = Depends(get_db),
):
    ano = db.get(AnoLetivo, dados.ano_letivo_id)

    if ano is None:
        raise HTTPException(
            status_code=404,
            detail="Ano letivo nao encontrado.",
        )

    if not ano.ativo:
        raise HTTPException(
            status_code=409,
            detail="Nao e permitido criar turma em ano letivo inativo.",
        )

    turma = Turma(
        identificacao=dados.identificacao,
        ano_escolar=dados.ano_escolar,
        ano_letivo_id=dados.ano_letivo_id,
        turno=dados.turno,
        ativo=True,
    )

    db.add(turma)
    confirmar_alteracao(db)
    db.refresh(turma)

    return turma


@router.get("", response_model=list[TurmaResposta])
def listar_turmas(
    ano_letivo_id: int | None = Query(default=None, gt=0),
    ativo: bool | None = None,
    db: Session = Depends(get_db),
):
    consulta = select(Turma)

    if ano_letivo_id is not None:
        consulta = consulta.where(
            Turma.ano_letivo_id == ano_letivo_id
        )

    if ativo is not None:
        consulta = consulta.where(Turma.ativo == ativo)

    consulta = consulta.order_by(Turma.id)

    return db.scalars(consulta).all()


@router.get("/{turma_id}", response_model=TurmaResposta)
def consultar_turma(
    turma_id: int,
    db: Session = Depends(get_db),
):
    return obter_turma_ou_404(db, turma_id)


@router.patch("/{turma_id}", response_model=TurmaResposta)
def atualizar_turma(
    turma_id: int,
    dados: TurmaAtualizar,
    db: Session = Depends(get_db),
):
    turma = obter_turma_ou_404(db, turma_id)

    alteracoes = dados.model_dump(exclude_unset=True)

    for campo, valor in alteracoes.items():
        setattr(turma, campo, valor)

    confirmar_alteracao(db)
    db.refresh(turma)

    return turma
