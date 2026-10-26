
"""Consulta das liberações do dia para o responsável autenticado."""

from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    Autenticado,
    exigir_responsavel,
    get_db,
    get_relogio,
)
from app.api.responsavel_alunos import consulta_alunos_autorizados
from app.core.config import Settings, get_settings
from app.domain.relogio import Relogio
from app.models import Liberacao
from app.schemas.liberacoes_responsavel import (
    SituacaoLiberacaoResponsavel,
)


router = APIRouter(
    prefix="/responsavel/liberacoes",
    tags=["Responsavel - Consultas de Liberacoes"],
)


@router.get(
    "/hoje",
    response_model=list[SituacaoLiberacaoResponsavel],
)

def consultar_liberacoes_hoje(
    db: Session = Depends(get_db),
    autenticacao: Autenticado = Depends(exigir_responsavel),
    relogio: Relogio = Depends(get_relogio),
    settings: Settings = Depends(get_settings),
):
    agora = relogio.agora()

    data_escolar = agora.astimezone(
        ZoneInfo(settings.school_timezone)
    ).date()

    # 1. Recuperar somente os alunos autorizados.
    consulta_alunos = (
        consulta_alunos_autorizados(
            autenticacao.usuario.id,
            agora,
        )
        .order_by()
    )

    alunos = db.scalars(
        consulta_alunos
    ).unique().all()

    if not alunos:
        return []

    ids_alunos = [
        aluno.id
        for aluno in alunos
    ]

    # 2. Consultar todas as liberações do dia.
    consulta_liberacoes = select(Liberacao).where(
        Liberacao.aluno_id.in_(ids_alunos),
        Liberacao.data == data_escolar,
    )

    liberacoes = db.scalars(
        consulta_liberacoes
    ).all()

    # 3. Indexar as liberações pelo ID do aluno.
    # Preservamos o objeto completo para acessar
    # tanto o estado quanto o horário autorizado.
    liberacoes_por_aluno = {
        liberacao.aluno_id: liberacao
        for liberacao in liberacoes
    }

    # 4. Montar as respostas.
    resultado = []

    for aluno in alunos:
        liberacao = liberacoes_por_aluno.get(
            aluno.id
        )

        if liberacao is None:
            estado = "SEM_REGISTRO"
            horario = None
        else:
            estado = liberacao.estado.value

            horario = (
                liberacao.horario_inicio_liberacao
                if estado == "LIBERADO"
                else None
            )

        resultado.append(
            SituacaoLiberacaoResponsavel(
                aluno_id=aluno.id,
                data=data_escolar,
                estado=estado,
                horario_inicio_liberacao=horario,
            )
        )

    return resultado
