
"""Consultas de alunos vinculados ao responsavel — E4b."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    Autenticado,
    exigir_responsavel,
    get_db,
    get_relogio,
)
from app.domain.relogio import Relogio
from app.models import Aluno, Responsavel, ResponsavelAluno
from app.schemas.alunos import AlunoResposta

router = APIRouter(
    prefix="/responsavel/alunos",
    tags=["Responsavel - Alunos"],
)

def consulta_alunos_autorizados(
    usuario_id: int,
    instante: datetime,
):
    """Seleciona alunos ativos com vinculo vigente."""

    return (
        select(Aluno)
        .join(
            ResponsavelAluno,
            ResponsavelAluno.aluno_id == Aluno.id,
        )
        .join(
            Responsavel,
            Responsavel.id == ResponsavelAluno.responsavel_id,
        )
        .where(
            Responsavel.usuario_id == usuario_id,
            Responsavel.ativo.is_(True),
            Aluno.ativo.is_(True),
            ResponsavelAluno.vigente_desde <= instante,
            (
                (ResponsavelAluno.revogado_em.is_(None))
                | (ResponsavelAluno.revogado_em > instante)
            ),
        )
    )


@router.get("", response_model=list[AlunoResposta])
def listar_meus_alunos(
    db: Session = Depends(get_db),
    autenticacao: Autenticado = Depends(exigir_responsavel),
    relogio: Relogio = Depends(get_relogio),
):
    consulta = (
        consulta_alunos_autorizados(
            autenticacao.usuario.id,
            relogio.agora(),
        )
        .order_by(Aluno.id)
    )

    return db.scalars(consulta).all()


@router.get("/{aluno_id}", response_model=AlunoResposta)
def consultar_meu_aluno(
    aluno_id: int,
    db: Session = Depends(get_db),
    autenticacao: Autenticado = Depends(exigir_responsavel),
    relogio: Relogio = Depends(get_relogio),
):
    consulta = consulta_alunos_autorizados(
        autenticacao.usuario.id,
        relogio.agora(),
    ).where(Aluno.id == aluno_id)

    aluno = db.scalars(consulta).first()

    if aluno is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    return aluno
