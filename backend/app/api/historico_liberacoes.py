
"""Consulta administrativa do histórico auditável de liberações."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db
from app.models import Aluno, HistoricoLiberacao
from app.schemas.historico_liberacoes import (
    HistoricoLiberacaoResposta,
)


router = APIRouter(
    prefix="/admin/alunos",
    tags=["Admin - Historico de Liberacoes"],
    dependencies=[Depends(exigir_admin)],
)


@router.get(
    "/{aluno_id}/liberacoes/historico",
    response_model=list[HistoricoLiberacaoResposta],
)
def consultar_historico_liberacoes(
    aluno_id: int,
    db: Session = Depends(get_db),
):
    # 1. Verificar se o aluno existe.
    aluno = db.get(Aluno, aluno_id)

    if aluno is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    # 2. Consultar o histórico completo do aluno.
    consulta = (
        select(HistoricoLiberacao)
        .where(
            HistoricoLiberacao.aluno_id == aluno_id
        )
        .order_by(
            HistoricoLiberacao.ocorrido_em.desc(),
            HistoricoLiberacao.id.desc(),
        )
    )

    registros = db.scalars(consulta).all()

    # 3. Retornar os registros sem modificá-los.
    return registros
