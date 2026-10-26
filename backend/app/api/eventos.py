
"""Endpoints administrativos da agenda escolar."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.services.conflitos_eventos import encontrar_conflito_evento
from datetime import date, time
from fastapi import Query

from fastapi import APIRouter, Depends, HTTPException, Response
from app.schemas.eventos import (
    EventoAtualizar,
    EventoCriar,
    EventoResposta,
    ModoAplicacaoEvento,
)

from app.api.deps import exigir_admin, get_db
from app.models import EventoAgenda, Turma
from app.schemas.eventos import EventoCriar, EventoResposta



router = APIRouter(
    prefix="/admin/eventos",
    tags=["Admin - Eventos"],
    dependencies=[Depends(exigir_admin)],
)

@router.post(
    "",
    response_model=EventoResposta,
    status_code=201,
)
def criar_evento(
    dados: EventoCriar,
    db: Session = Depends(get_db),
) -> EventoResposta:
    # Verificar a existência da turma.
    turma = db.get(Turma, dados.turma_id)

    if turma is None:
        raise HTTPException(
            status_code=404,
            detail="Turma nao encontrada.",
        )

    # Impedir eventos em turmas inativas.
    if not turma.ativo:
        raise HTTPException(
            status_code=409,
            detail="Turma inativa.",
        )

    # Bloqueia a turma durante a validação e a gravação,
    # evitando importações concorrentes de eventos conflitantes.
    db.execute(
        select(Turma)
        .where(Turma.id == dados.turma_id)
        .with_for_update()
    ).scalar_one()

    conflito = encontrar_conflito_evento(
        db,
        turma_id=dados.turma_id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        modo_aplicacao=dados.modo_aplicacao,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
    )

    if conflito is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Existe um evento substitutivo conflitante: "
                f"{conflito.titulo} (ID {conflito.id})."
            ),
        )
    # Utilizar o modelo SQLAlchemy já existente.
    evento = EventoAgenda(
        turma_id=dados.turma_id,
        titulo=dados.titulo,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        ativo=True,
        modo_aplicacao=dados.modo_aplicacao,
        hora_inicio=dados.hora_inicio,
        hora_fim=dados.hora_fim,
    )

    db.add(evento)
    db.commit()
    db.refresh(evento)

    return EventoResposta.model_validate(evento)


@router.get(
    "",
    response_model=list[EventoResposta],
)
def listar_eventos(
    turma_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
):
    # O intervalo informado precisa ser válido.
    if (
        data_inicio is not None
        and data_fim is not None
        and data_fim < data_inicio
    ):
        raise HTTPException(
            status_code=422,
            detail="A data final nao pode ser anterior a inicial.",
        )

    consulta = select(EventoAgenda).where(
        EventoAgenda.ativo.is_(True)
    )

    if turma_id is not None:
        consulta = consulta.where(
            EventoAgenda.turma_id == turma_id
        )

    # Quando há uma data final, o evento precisa
    # começar até esse dia.
    if data_fim is not None:
        consulta = consulta.where(
            EventoAgenda.data_inicio <= data_fim
        )

    # Quando há uma data inicial, o evento precisa
    # terminar nesse dia ou posteriormente.
    if data_inicio is not None:
        consulta = consulta.where(
            EventoAgenda.data_fim >= data_inicio
        )

    consulta = consulta.order_by(
        EventoAgenda.data_inicio,
        EventoAgenda.id,
    )

    return db.scalars(consulta).all()



@router.get(
    "/{evento_id}",
    response_model=EventoResposta,
)
def consultar_evento(
    evento_id: int,
    db: Session = Depends(get_db),
):
    evento = db.get(
        EventoAgenda,
        evento_id,
    )

    if evento is None or not evento.ativo:
        raise HTTPException(
            status_code=404,
            detail="Evento nao encontrado.",
        )

    return evento


@router.patch(
    "/{evento_id}",
    response_model=EventoResposta,
)
def atualizar_evento(
    evento_id: int,
    dados: EventoAtualizar,
    db: Session = Depends(get_db),
):
    evento = db.get(EventoAgenda, evento_id)

    if evento is None or not evento.ativo:
        raise HTTPException(
            status_code=404,
            detail="Evento nao encontrado.",
        )

    alteracoes = dados.model_dump(exclude_unset=True)

    campos_obrigatorios = {
        "turma_id",
        "titulo",
        "data_inicio",
        "data_fim",
        "modo_aplicacao",
    }

    if any(
        campo in alteracoes and alteracoes[campo] is None
        for campo in campos_obrigatorios
    ):
        raise HTTPException(
            status_code=422,
            detail="Campos obrigatorios nao podem ser nulos.",
        )

    # Validar o intervalo após combinar dados novos
    # com os valores atuais do evento.
    inicio = alteracoes.get(
        "data_inicio",
        evento.data_inicio,
    )
    fim = alteracoes.get(
        "data_fim",
        evento.data_fim,
    )
    
    modo = alteracoes.get("modo_aplicacao", evento.modo_aplicacao)
    hora_inicio = alteracoes.get("hora_inicio", evento.hora_inicio)
    hora_fim = alteracoes.get("hora_fim", evento.hora_fim)

    if (hora_inicio is None) != (hora_fim is None):
        raise HTTPException(
            status_code=422,
            detail="Informe ou remova ambos os horarios.",
        )

    if hora_inicio is not None and hora_fim <= hora_inicio:
        raise HTTPException(
            status_code=422,
            detail="A hora final deve ser posterior a inicial.",
        )

    if modo == ModoAplicacaoEvento.SUBSTITUICAO_PARCIAL:
        if hora_inicio is None or inicio != fim:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Substituicao parcial exige horarios "
                    "e uma unica data."
                ),
            )
            
    # if fim < inicio:
    #     raise HTTPException(
    #         status_code=422,
    #         detail="A data final nao pode ser anterior a inicial.",
    #     )

    if "turma_id" in alteracoes:
        turma = db.get(
            Turma,
            alteracoes["turma_id"],
        )

        if turma is None:
            raise HTTPException(
                status_code=404,
                detail="Turma nao encontrada.",
            )

        if not turma.ativo:
            raise HTTPException(
                status_code=409,
                detail="Turma inativa.",
            )

    turma_destino_id = alteracoes.get(
        "turma_id",
        evento.turma_id,
    )

    modo_final = alteracoes.get(
        "modo_aplicacao",
        evento.modo_aplicacao,
    )

    hora_inicio_final = alteracoes.get(
        "hora_inicio",
        evento.hora_inicio,
    )

    hora_fim_final = alteracoes.get(
        "hora_fim",
        evento.hora_fim,
    )

    # Bloqueia as duas turmas, quando houver mudança,
    # sempre na mesma ordem para reduzir risco de deadlock.
    ids_para_bloquear = sorted(
        {evento.turma_id, turma_destino_id}
    )

    db.scalars(
        select(Turma)
        .where(Turma.id.in_(ids_para_bloquear))
        .order_by(Turma.id)
        .with_for_update()
    ).all()

    conflito = encontrar_conflito_evento(
        db,
        turma_id=turma_destino_id,
        data_inicio=inicio,
        data_fim=fim,
        modo_aplicacao=modo_final,
        hora_inicio=hora_inicio_final,
        hora_fim=hora_fim_final,
        ignorar_evento_id=evento.id,
    )

    if conflito is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "A alteração conflita com o evento "
                f"{conflito.titulo} (ID {conflito.id})."
            ),
        )
    for campo, valor in alteracoes.items():
        setattr(evento, campo, valor)

    db.commit()
    db.refresh(evento)

    return evento


@router.delete(
    "/{evento_id}",
    status_code=204,
)
def desativar_evento(
    evento_id: int,
    db: Session = Depends(get_db),
):
    evento = db.get(EventoAgenda, evento_id)

    if evento is None or not evento.ativo:
        raise HTTPException(
            status_code=404,
            detail="Evento nao encontrado.",
        )

    evento.ativo = False

    db.commit()

    return Response(status_code=204)
