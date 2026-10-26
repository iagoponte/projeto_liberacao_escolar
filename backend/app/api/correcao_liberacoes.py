
"""Correção administrativa auditável de liberações."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings

from app.api.deps import (
    autenticado,
    exigir_admin,
    get_db,
    get_relogio,
)
from app.schemas.correcao_liberacoes import (
    CorrecaoLiberacaoEntrada,
    CorrecaoLiberacaoResposta,
)
from app.services.liberacoes import executar_correcao_admin

# Importar get_settings do mesmo módulo já utilizado
# pelo endpoint de liberação do responsável.
# from ... import get_settings


router = APIRouter(
    prefix="/admin/alunos",
    tags=["Admin - Correcao de Liberacoes"],
    dependencies=[Depends(exigir_admin)],
)


@router.patch(
    "/{aluno_id}/liberacao",
    response_model=CorrecaoLiberacaoResposta,
)
def corrigir_liberacao(
    aluno_id: int,
    dados: CorrecaoLiberacaoEntrada,
    db: Session = Depends(get_db),
    auth=Depends(autenticado),
    relogio=Depends(get_relogio),
    settings=Depends(get_settings),
):
    liberacao = executar_correcao_admin(
        db,
        aluno_id=aluno_id,
        usuario_id=auth.usuario.id,
        novo_estado=dados.estado,
        motivo=dados.motivo,
        agora=relogio.agora(),
        fuso=settings.school_timezone,
    )

    return CorrecaoLiberacaoResposta(
        aluno_id=liberacao.aluno_id,
        data=liberacao.data,
        estado=liberacao.estado,
    )
