
"""Endpoints de liberação escolar."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import (
    Autenticado,
    exigir_responsavel,
    get_db,
    get_relogio,
)
from app.core.config import Settings, get_settings
from app.domain.relogio import Relogio
from app.schemas.liberacoes import (
    LiberacaoPedido,
    LiberacaoResposta,
)
from app.services.liberacoes import executar_liberacao_responsavel


router = APIRouter(
    prefix="/responsavel/alunos",
    tags=["Responsavel - Liberacoes"],
)


@router.post(
    "/{aluno_id}/liberacao",
    response_model=LiberacaoResposta,
)
def alterar_liberacao(
    aluno_id: int,
    dados: LiberacaoPedido,
    db: Session = Depends(get_db),
    auth: Autenticado = Depends(exigir_responsavel),
    relogio: Relogio = Depends(get_relogio),
    settings: Settings = Depends(get_settings),
) -> LiberacaoResposta:
    return executar_liberacao_responsavel(
        db,
        aluno_id=aluno_id,
        usuario_id=auth.usuario.id,
        acao=dados.acao,
        horario_inicio_liberacao=dados.horario_inicio_liberacao,
        agora=relogio.agora(),
        settings=settings,
    )