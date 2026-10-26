
"""Operações de liberação escolar com histórico transacional."""

from datetime import datetime, time

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.avaliacao import PedidoOperacao, avaliar_operacao
from app.domain.erros import (
    DataNaoPermitida,
    ForaDoHorarioLimite,
    TransicaoInvalida,
    VinculoInvalido,
)
from app.domain.estados import Acao, Mudanca, Perfil, TipoAcao, Estado
from app.domain.relogio import data_escolar
from app.domain.vinculo import Vinculo
from app.models import (
    Aluno,
    AnoLetivo,
    HistoricoLiberacao,
    Liberacao,
    Matricula,
    Responsavel,
    ResponsavelAluno,
    Turma,
)
from app.schemas.liberacoes import LiberacaoResposta
from app.services.horarios_liberacao import (
    HorarioLiberacaoInvalido,
    validar_horario_liberacao,
)
from app.services.consulta_agenda_efetiva import (
    ErroConsultaAgenda,
    consultar_agenda_efetiva,
)




def executar_liberacao_responsavel(
    db: Session,
    *,
    aluno_id: int,
    usuario_id: int,
    acao: Acao,
    horario_inicio_liberacao: time | None = None,
    agora: datetime,
    settings: Settings,
) -> LiberacaoResposta:
    """Executa liberação/cancelamento com auditoria de horário."""

    hoje = data_escolar(
        agora,
        settings.school_timezone,
    )

    # --------------------------------------------------------
    # 1. Bloquear o aluno e validar cadastro
    # --------------------------------------------------------

    aluno = db.scalar(
        select(Aluno)
        .where(Aluno.id == aluno_id)
        .with_for_update()
    )

    if aluno is None or not aluno.ativo:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    # --------------------------------------------------------
    # 2. Identificar responsável ativo
    # --------------------------------------------------------

    responsavel = db.scalar(
        select(Responsavel)
        .where(
            Responsavel.usuario_id == usuario_id,
            Responsavel.ativo.is_(True),
        )
    )

    if responsavel is None:
        raise HTTPException(
            status_code=403,
            detail="Responsavel inativo ou nao cadastrado.",
        )

    # --------------------------------------------------------
    # 3. Validar vínculo vigente
    # --------------------------------------------------------

    registro_vinculo = db.scalar(
        select(ResponsavelAluno)
        .where(
            ResponsavelAluno.responsavel_id == responsavel.id,
            ResponsavelAluno.aluno_id == aluno_id,
            ResponsavelAluno.vigente_desde <= agora,
            or_(
                ResponsavelAluno.revogado_em.is_(None),
                ResponsavelAluno.revogado_em > agora,
            ),
        )
    )

    if registro_vinculo is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    vinculo = Vinculo(
        responsavel_id=registro_vinculo.responsavel_id,
        aluno_id=registro_vinculo.aluno_id,
        vigente_desde=registro_vinculo.vigente_desde,
        revogado_em=registro_vinculo.revogado_em,
    )

    # --------------------------------------------------------
    # 4. Identificar turma e turno da matrícula atual
    # --------------------------------------------------------

    matricula_turma = db.execute(
        select(
            Turma.id,
            Turma.turno,
        )
        .join(
            Matricula,
            Matricula.turma_id == Turma.id,
        )
        .join(
            AnoLetivo,
            Matricula.ano_letivo_id == AnoLetivo.id,
        )
        .where(
            Matricula.aluno_id == aluno_id,
            Matricula.ano_letivo_id == Turma.ano_letivo_id,
            Matricula.data_inicio <= hoje,
            or_(
                Matricula.data_fim.is_(None),
                Matricula.data_fim >= hoje,
            ),
            Turma.ativo.is_(True),
            AnoLetivo.ativo.is_(True),
        )
        .limit(1)
    ).first()

    if matricula_turma is None:
        raise HTTPException(
            status_code=409,
            detail="Aluno sem matricula vigente.",
        )

    turma_id, turno = matricula_turma

    # --------------------------------------------------------
    # 5. Consultar estado e horário atuais
    # --------------------------------------------------------

    liberacao = db.scalar(
        select(Liberacao)
        .where(
            Liberacao.aluno_id == aluno_id,
            Liberacao.data == hoje,
        )
    )

    estado_atual = (
        liberacao.estado
        if liberacao is not None
        else None
    )

    horario_anterior = (
        liberacao.horario_inicio_liberacao
        if liberacao is not None
        else None
    )

    # --------------------------------------------------------
    # 6. Preservar regras existentes do domínio
    # --------------------------------------------------------

    try:
        resultado = avaliar_operacao(
            PedidoOperacao(
                perfil=Perfil.RESPONSAVEL,
                acao=acao,
                estado_atual=estado_atual,
                agora=agora,
                fuso=settings.school_timezone,
                turno=turno,
                vinculo=vinculo,
            )
        )

    except VinculoInvalido as exc:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        ) from exc

    except (
        DataNaoPermitida,
        ForaDoHorarioLimite,
        TransicaoInvalida,
    ) as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    decisao = resultado.decisao

    # --------------------------------------------------------
    # 7. Validar o horário solicitado
    # --------------------------------------------------------

    if acao == Acao.LIBERAR:
        if horario_inicio_liberacao is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Informe o horario de inicio "
                    "da liberacao."
                ),
            )

        try:
            agenda = consultar_agenda_efetiva(
                db,
                turma_id=turma_id,
                data=hoje,
            )

            validar_horario_liberacao(
                data_solicitada=hoje,
                data_escolar_atual=hoje,
                horario_solicitado=horario_inicio_liberacao,
                agenda=agenda,
            )

        except (
            HorarioLiberacaoInvalido,
            ErroConsultaAgenda,
        ) as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        novo_horario = horario_inicio_liberacao

    else:
        if horario_inicio_liberacao is not None:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Cancelamentos nao devem "
                    "informar horario de liberacao."
                ),
            )

        novo_horario = None

    # --------------------------------------------------------
    # 8. Identificar se houve mudança real
    # --------------------------------------------------------

    novo_estado = (
        decisao.novo_estado
        if isinstance(decisao, Mudanca)
        else decisao.estado
    )

    mudou_estado = estado_atual != novo_estado

    mudou_horario = (
        horario_anterior != novo_horario
    )

    # Repetir a mesma decisão e o mesmo horário
    # não modifica a liberação nem gera auditoria.
    if not mudou_estado and not mudou_horario:
        return LiberacaoResposta(
            aluno_id=aluno_id,
            data=resultado.data_alvo,
            estado=novo_estado,
            horario_inicio_liberacao=horario_anterior,
        )

    # --------------------------------------------------------
    # 9. Criar ou atualizar o estado atual
    # --------------------------------------------------------

    if liberacao is None:
        liberacao = Liberacao(
            aluno_id=aluno_id,
            data=resultado.data_alvo,
            estado=novo_estado,
            horario_inicio_liberacao=novo_horario,
            atualizado_por_usuario_id=usuario_id,
        )

        db.add(liberacao)
        db.flush()

    else:
        liberacao.estado = novo_estado
        liberacao.horario_inicio_liberacao = novo_horario
        liberacao.atualizado_por_usuario_id = usuario_id

    # --------------------------------------------------------
    # 10. Registrar histórico da operação
    # --------------------------------------------------------

    # Uma correção parental de horário mantém o estado
    # LIBERADO, mas é uma mudança real auditável.
    tipo_acao = (
        TipoAcao.LIBERACAO
        if acao == Acao.LIBERAR
        else TipoAcao.CANCELAMENTO
    )

    historico = HistoricoLiberacao(
        liberacao_id=liberacao.id,
        aluno_id=aluno_id,
        usuario_id=usuario_id,
        perfil=Perfil.RESPONSAVEL,
        estado_anterior=estado_atual,
        novo_estado=novo_estado,
        horario_anterior=horario_anterior,
        horario_novo=novo_horario,
        tipo_acao=tipo_acao,
        motivo=None,
    )

    db.add(historico)

    # --------------------------------------------------------
    # 11. Persistir liberação e auditoria atomicamente
    # --------------------------------------------------------

    db.commit()

    return LiberacaoResposta(
        aluno_id=aluno_id,
        data=resultado.data_alvo,
        estado=novo_estado,
        horario_inicio_liberacao=novo_horario,
    )



def executar_correcao_admin(
    db: Session,
    *,
    aluno_id: int,
    usuario_id: int,
    novo_estado: Estado,
    motivo: str,
    agora: datetime,
    fuso: str,
) -> Liberacao:
    """Corrige a liberação com histórico transacional."""

    hoje = data_escolar(agora, fuso)

    # 1. Bloquear o aluno.
    aluno = db.scalar(
        select(Aluno)
        .where(Aluno.id == aluno_id)
        .with_for_update()
    )

    if aluno is None or not aluno.ativo:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado ou inativo.",
        )

    # 2. Conferir matrícula válida.
    matricula_id = db.scalar(
        select(Matricula.id)
        .join(
            Turma,
            Matricula.turma_id == Turma.id,
        )
        .join(
            AnoLetivo,
            Matricula.ano_letivo_id == AnoLetivo.id,
        )
        .where(
            Matricula.aluno_id == aluno_id,
            Matricula.ano_letivo_id == Turma.ano_letivo_id,
            Matricula.data_inicio <= hoje,
            or_(
                Matricula.data_fim.is_(None),
                Matricula.data_fim >= hoje,
            ),
            Turma.ativo.is_(True),
            AnoLetivo.ativo.is_(True),
        )
        .limit(1)
    )

    if matricula_id is None:
        raise HTTPException(
            status_code=409,
            detail="Aluno sem matricula valida na data atual.",
        )

    # 3. Localizar estado e horário atuais.
    liberacao = db.scalar(
        select(Liberacao)
        .where(
            Liberacao.aluno_id == aluno_id,
            Liberacao.data == hoje,
        )
    )

    estado_anterior = (
        liberacao.estado
        if liberacao is not None
        else None
    )

    horario_anterior = (
        liberacao.horario_inicio_liberacao
        if liberacao is not None
        else None
    )

    if estado_anterior == novo_estado:
        raise HTTPException(
            status_code=409,
            detail="O aluno ja possui o estado solicitado.",
        )

    # Cancelamento não pode manter um horário ativo.
    # Ao liberar, preservamos um eventual horário anterior,
    # sem criar um horário fictício.
    horario_novo = (
        horario_anterior
        if novo_estado == Estado.LIBERADO
        else None
    )

    # 4. Criar ou atualizar a liberação.
    if liberacao is None:
        liberacao = Liberacao(
            aluno_id=aluno_id,
            data=hoje,
            estado=novo_estado,
            horario_inicio_liberacao=horario_novo,
            atualizado_por_usuario_id=usuario_id,
        )

        db.add(liberacao)
        db.flush()

    else:
        liberacao.estado = novo_estado
        liberacao.horario_inicio_liberacao = horario_novo
        liberacao.atualizado_por_usuario_id = usuario_id

    # 5. Registrar a correção.
    historico = HistoricoLiberacao(
        liberacao_id=liberacao.id,
        aluno_id=aluno_id,
        usuario_id=usuario_id,
        perfil=Perfil.ADMIN,
        ocorrido_em=agora,
        estado_anterior=estado_anterior,
        novo_estado=novo_estado,
        horario_anterior=horario_anterior,
        horario_novo=horario_novo,
        tipo_acao=TipoAcao.CORRECAO_ADMIN,
        motivo=motivo,
    )

    db.add(historico)

    # 6. Persistência atômica.
    db.commit()
    db.refresh(liberacao)

    return liberacao
