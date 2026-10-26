
"""API administrativa de anos letivos — E5.1."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from psycopg import errors

from app.api.deps import Autenticado, exigir_admin, get_db
from app.models import AnoLetivo
from app.schemas.anos_letivos import (
    AnoLetivoAtualizar,
    AnoLetivoCriar,
    AnoLetivoResposta,
)

router = APIRouter(
    prefix="/admin/anos-letivos",
    tags=["Administracao - Anos letivos"],
    dependencies=[Depends(exigir_admin)],
)


def obter_ano_ou_404(db: Session, ano_id: int) -> AnoLetivo:
    ano = db.get(AnoLetivo, ano_id)

    if ano is None:
        raise HTTPException(
            status_code=404,
            detail="Ano letivo nao encontrado.",
        )

    return ano


def confirmar_alteracao(db: Session) -> None:
    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        if isinstance(exc.orig, errors.UniqueViolation):
            raise HTTPException(
                status_code=409,
                detail="Ano letivo ja cadastrado.",
            ) from exc

        raise

@router.post(
    "",
    response_model=AnoLetivoResposta,
    status_code=status.HTTP_201_CREATED,
)
def criar_ano_letivo(
    dados: AnoLetivoCriar,
    db: Session = Depends(get_db),
):
    ano = AnoLetivo(ano=dados.ano, ativo=True)

    db.add(ano)
    confirmar_alteracao(db)
    db.refresh(ano)

    return ano


@router.get("", response_model=list[AnoLetivoResposta])
def listar_anos_letivos(
    db: Session = Depends(get_db),
):
    consulta = select(AnoLetivo).order_by(AnoLetivo.ano)

    return db.scalars(consulta).all()


@router.get("/{ano_id}", response_model=AnoLetivoResposta)
def consultar_ano_letivo(
    ano_id: int,
    db: Session = Depends(get_db),
):
    return obter_ano_ou_404(db, ano_id)


@router.patch("/{ano_id}", response_model=AnoLetivoResposta)
def atualizar_ano_letivo(
    ano_id: int,
    dados: AnoLetivoAtualizar,
    db: Session = Depends(get_db),
):
    ano = obter_ano_ou_404(db, ano_id)

    alteracoes = dados.model_dump(exclude_unset=True)

    for campo, valor in alteracoes.items():
        setattr(ano, campo, valor)

    confirmar_alteracao(db)
    db.refresh(ano)

    return ano
