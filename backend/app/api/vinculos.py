
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from psycopg import errors
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.api.deps import get_relogio
from app.domain.relogio import Relogio
from app.api.deps import exigir_admin, get_db
from app.domain.estados import Perfil
from app.models import Aluno, Responsavel, ResponsavelAluno, Usuario
from app.schemas.vinculos import VinculoCriar, VinculoResposta


router = APIRouter(
    prefix="/admin/vinculos",
    tags=["Vinculos"],
    dependencies=[Depends(exigir_admin)],
)


def montar_resposta_vinculo(
    vinculo: ResponsavelAluno,
) -> VinculoResposta:
    return VinculoResposta(
        id=vinculo.id,
        responsavel_id=vinculo.responsavel_id,
        aluno_id=vinculo.aluno_id,
        vigente_desde=vinculo.vigente_desde,
        revogado_em=vinculo.revogado_em,
        ativo=vinculo.revogado_em is None,
    )
   


@router.post(
    "",
    response_model=VinculoResposta,
    status_code=201,
)
def criar_vinculo(
    dados: VinculoCriar,
    db: Session = Depends(get_db),
    relogio: Relogio = Depends(get_relogio),
):
    responsavel = db.get(Responsavel, dados.responsavel_id)

    if responsavel is None:
        raise HTTPException(
            status_code=404,
            detail="Responsavel nao encontrado.",
        )

    usuario = db.get(Usuario, responsavel.usuario_id)

    if usuario is None:
        raise HTTPException(
            status_code=404,
            detail="Usuario nao encontrado.",
        )

    if usuario.perfil != Perfil.RESPONSAVEL:
        raise HTTPException(
            status_code=409,
            detail="Usuario nao possui perfil RESPONSAVEL.",
        )

    if not usuario.ativo or not responsavel.ativo:
        raise HTTPException(
            status_code=409,
            detail="Responsavel inativo.",
        )

    aluno = db.scalar(
        select(Aluno)
        .where(Aluno.id == dados.aluno_id)
        .with_for_update()
    )

    if aluno is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    if not aluno.ativo:
        raise HTTPException(
            status_code=409,
            detail="Aluno inativo.",
        )

    vinculo = ResponsavelAluno(
        responsavel_id=responsavel.id,
        aluno_id=aluno.id,
        vigente_desde=relogio.agora(),
        revogado_em=None,
    )

    db.add(vinculo)

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        diagnostico = getattr(exc.orig, "diag", None)
        constraint = getattr(
            diagnostico,
            "constraint_name",
            None,
        )

        if (
            isinstance(exc.orig, errors.UniqueViolation)
            and constraint == "uq_responsaveis_alunos_vinculo_ativo"
        ):
            raise HTTPException(
                status_code=409,
                detail="Vinculo ativo ja existente.",
            ) from exc

        raise

    db.refresh(vinculo)

    return montar_resposta_vinculo(vinculo)


@router.get(
    "/{vinculo_id}",
    response_model=VinculoResposta,
)
def consultar_vinculo(
    vinculo_id: int,
    db: Session = Depends(get_db),
):
    vinculo = db.get(ResponsavelAluno, vinculo_id)

    if vinculo is None:
        raise HTTPException(
            status_code=404,
            detail="Vinculo nao encontrado.",
        )

    return montar_resposta_vinculo(vinculo)


@router.get(
    "",
    response_model=list[VinculoResposta],
)
def listar_vinculos(
    aluno_id: int,
    db: Session = Depends(get_db),
):
    aluno = db.get(Aluno, aluno_id)

    if aluno is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    consulta = (
        select(ResponsavelAluno)
        .where(ResponsavelAluno.aluno_id == aluno_id)
        .order_by(
            ResponsavelAluno.vigente_desde.desc(),
            ResponsavelAluno.id.desc(),
        )
    )

    vinculos = db.scalars(consulta).all()

    return [
        montar_resposta_vinculo(vinculo)
        for vinculo in vinculos
    ]


@router.post(
    "/{vinculo_id}/revogar",
    response_model=VinculoResposta,
)

def revogar_vinculo(
    vinculo_id: int,
    db: Session = Depends(get_db),
    relogio: Relogio = Depends(get_relogio),
):
    # 1. Descobrir o aluno sem bloquear o vínculo.
    # Consultamos apenas a coluna, não a entidade ORM.
    aluno_id = db.scalar(
        select(ResponsavelAluno.aluno_id)
        .where(ResponsavelAluno.id == vinculo_id)
    )

    if aluno_id is None:
        raise HTTPException(
            status_code=404,
            detail="Vinculo nao encontrado.",
        )

    # 2. Bloquear primeiro o aluno.
    # É o mesmo registro bloqueado pelo serviço
    # executar_liberacao_responsavel().
    aluno = db.scalar(
        select(Aluno)
        .where(Aluno.id == aluno_id)
        .with_for_update()
    )

    if aluno is None:
        raise HTTPException(
            status_code=404,
            detail="Aluno nao encontrado.",
        )

    # 3. Agora bloquear e RECONSULTAR o vínculo.
    # A verificação ocorre depois de adquirir
    # o bloqueio compartilhado de coordenação.
    vinculo = db.scalar(
        select(ResponsavelAluno)
        .where(ResponsavelAluno.id == vinculo_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if vinculo is None:
        raise HTTPException(
            status_code=404,
            detail="Vinculo nao encontrado.",
        )

    if vinculo.revogado_em is not None:
        raise HTTPException(
            status_code=409,
            detail="Vinculo ja revogado.",
        )

    agora = relogio.agora()

    # Restrição já existente no banco.
    if agora <= vinculo.vigente_desde:
        raise HTTPException(
            status_code=409,
            detail="Vinculo ainda nao pode ser revogado.",
        )

    # 4. Registrar a revogação.
    vinculo.revogado_em = agora

    # 5. Confirmar a transação e liberar os bloqueios.
    db.commit()
    db.refresh(vinculo)

    return montar_resposta_vinculo(vinculo)

@router.post(
    "/{vinculo_id}/reativar",
    response_model=VinculoResposta,
    status_code=201,
)
def reativar_vinculo(
    vinculo_id: int,
    db: Session = Depends(get_db),
    relogio: Relogio = Depends(get_relogio),
):
    # Identificar o aluno sem bloquear o vínculo.
    aluno_id = db.scalar(
        select(ResponsavelAluno.aluno_id)
        .where(ResponsavelAluno.id == vinculo_id)
    )

    if aluno_id is None:
        raise HTTPException(
            status_code=404,
            detail="Vinculo nao encontrado.",
        )

    # Primeiro bloqueio: aluno.
    aluno = db.scalar(
        select(Aluno)
        .where(Aluno.id == aluno_id)
        .with_for_update()
    )

    if aluno is None or not aluno.ativo:
        raise HTTPException(
            status_code=409,
            detail="Aluno inexistente ou inativo.",
        )

    # Segundo bloqueio: vínculo histórico.
    vinculo_anterior = db.scalar(
        select(ResponsavelAluno)
        .where(ResponsavelAluno.id == vinculo_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if vinculo_anterior is None:
        raise HTTPException(
            status_code=404,
            detail="Vinculo nao encontrado.",
        )

    if vinculo_anterior.revogado_em is None:
        raise HTTPException(
            status_code=409,
            detail="Vinculo ainda esta ativo.",
        )

    # Verificar o responsável do vínculo original.
    responsavel = db.get(
        Responsavel,
        vinculo_anterior.responsavel_id,
    )

    if responsavel is None or not responsavel.ativo:
        raise HTTPException(
            status_code=409,
            detail="Responsavel inexistente ou inativo.",
        )

    usuario = db.get(
        Usuario,
        responsavel.usuario_id,
    )

    if (
        usuario is None
        or not usuario.ativo
        or usuario.perfil != Perfil.RESPONSAVEL
    ):
        raise HTTPException(
            status_code=409,
            detail="Usuario responsavel invalido ou inativo.",
        )

    # Criar NOVO registro, preservando o vínculo anterior.
    novo_vinculo = ResponsavelAluno(
        responsavel_id=responsavel.id,
        aluno_id=aluno.id,
        vigente_desde=relogio.agora(),
        revogado_em=None,
    )

    db.add(novo_vinculo)

    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        diagnostico = getattr(exc.orig, "diag", None)
        constraint = getattr(
            diagnostico,
            "constraint_name",
            None,
        )

        if (
            isinstance(exc.orig, errors.UniqueViolation)
            and constraint == "uq_responsaveis_alunos_vinculo_ativo"
        ):
            raise HTTPException(
                status_code=409,
                detail="Ja existe vinculo ativo para este par.",
            ) from exc

        raise

    db.refresh(novo_vinculo)

    return montar_resposta_vinculo(novo_vinculo)
