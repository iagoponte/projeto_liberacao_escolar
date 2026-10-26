
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import errors
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db
from app.models import Aluno, AnoLetivo, Matricula, Turma
from app.schemas.matriculas import (
    MatriculaAtualizar,
    MatriculaCriar,
    MatriculaResposta,
    TransferenciaCriar,
    TransferenciaResposta,
)




router = APIRouter(
    prefix="/admin/matriculas",
    tags=["Matriculas"],
    dependencies=[Depends(exigir_admin)],
)


def obter_ou_404(db: Session, modelo, identificador: int):
    objeto = db.get(modelo, identificador)

    if objeto is None:
        raise HTTPException(
            status_code=404,
            detail="Registro nao encontrado.",
        )

    return objeto



def confirmar_alteracao(db: Session) -> None:
    try:
        db.commit()

    except IntegrityError as exc:
        db.rollback()

        diagnostico = getattr(exc.orig, "diag", None)
        nome_constraint = getattr(
            diagnostico, "constraint_name", None
        )

        if (
            isinstance(exc.orig, errors.ExclusionViolation)
            and nome_constraint
            == "ex_matriculas_periodo_sem_sobreposicao"
        ):
            raise HTTPException(
                status_code=409,
                detail="Periodo de matricula sobreposto.",
            ) from exc

        if (
            isinstance(exc.orig, errors.UniqueViolation)
            and nome_constraint
            == "uq_matriculas_aberta_por_aluno_e_ano"
        ):
            raise HTTPException(
                status_code=409,
                detail="Ja existe matricula aberta para o aluno neste ano.",
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise



def verificar_cadastros_ativos(
    aluno: Aluno,
    turma: Turma,
    ano: AnoLetivo,
):
    if not aluno.ativo:
        raise HTTPException(
            status_code=409,
            detail="Aluno inativo.",
        )

    if not turma.ativo:
        raise HTTPException(
            status_code=409,
            detail="Turma inativa.",
        )

    if not ano.ativo:
        raise HTTPException(
            status_code=409,
            detail="Ano letivo inativo.",
        )


def verificar_periodo(
    inicio: date,
    fim: date | None,
):
    if fim is not None and fim < inicio:
        raise HTTPException(
            status_code=422,
            detail="Data final anterior a data inicial.",
        )


def verificar_sobreposicao(
    db: Session,
    aluno_id: int,
    ano_letivo_id: int,
    inicio: date,
    fim: date | None,
    ignorar_id: int | None = None,
):
    consulta = select(Matricula).where(
        Matricula.aluno_id == aluno_id,
        Matricula.ano_letivo_id == ano_letivo_id,
        or_(
            Matricula.data_fim.is_(None),
            Matricula.data_fim >= inicio,
        ),
    )

    if fim is not None:
        consulta = consulta.where(
            Matricula.data_inicio <= fim
        )

    if ignorar_id is not None:
        consulta = consulta.where(
            Matricula.id != ignorar_id
        )

    existente = db.scalar(consulta.limit(1))

    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail="Periodo de matricula sobreposto.",
        )


@router.post(
    "",
    response_model=MatriculaResposta,
    status_code=201,
)
def criar_matricula(
    dados: MatriculaCriar,
    db: Session = Depends(get_db),
):
    aluno = obter_ou_404(db, Aluno, dados.aluno_id)
    turma = obter_ou_404(db, Turma, dados.turma_id)
    ano = obter_ou_404(db, AnoLetivo, dados.ano_letivo_id)

    verificar_cadastros_ativos(aluno, turma, ano)

    if turma.ano_letivo_id != ano.id:
        raise HTTPException(
            status_code=422,
            detail="Turma nao pertence ao ano letivo.",
        )

    verificar_periodo(dados.data_inicio, dados.data_fim)

    verificar_sobreposicao(
        db,
        aluno_id=dados.aluno_id,
        ano_letivo_id=dados.ano_letivo_id,
        inicio=dados.data_inicio,
        fim=dados.data_fim,
    )

    matricula = Matricula(
        aluno_id=dados.aluno_id,
        turma_id=dados.turma_id,
        ano_letivo_id=dados.ano_letivo_id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
    )

    db.add(matricula)
    confirmar_alteracao(db)
    db.refresh(matricula)

    return matricula


@router.get(
    "",
    response_model=list[MatriculaResposta],
)
def listar_matriculas(
    aluno_id: int | None = Query(default=None, gt=0),
    turma_id: int | None = Query(default=None, gt=0),
    ano_letivo_id: int | None = Query(default=None, gt=0),
    aberta: bool | None = None,
    db: Session = Depends(get_db),
):
    consulta = select(Matricula)

    if aluno_id is not None:
        consulta = consulta.where(
            Matricula.aluno_id == aluno_id
        )

    if turma_id is not None:
        consulta = consulta.where(
            Matricula.turma_id == turma_id
        )

    if ano_letivo_id is not None:
        consulta = consulta.where(
            Matricula.ano_letivo_id == ano_letivo_id
        )

    if aberta is not None:
        consulta = consulta.where(
            Matricula.data_fim.is_(None)
            if aberta
            else Matricula.data_fim.is_not(None)
        )

    consulta = consulta.order_by(Matricula.id)

    return list(db.scalars(consulta).all())


@router.get(
    "/{matricula_id}",
    response_model=MatriculaResposta,
)
def consultar_matricula(
    matricula_id: int,
    db: Session = Depends(get_db),
):
    return obter_ou_404(db, Matricula, matricula_id)


@router.patch(
    "/{matricula_id}",
    response_model=MatriculaResposta,
)
def atualizar_matricula(
    matricula_id: int,
    dados: MatriculaAtualizar,
    db: Session = Depends(get_db),
):
    matricula = obter_ou_404(
        db, Matricula, matricula_id
    )

    verificar_periodo(
        matricula.data_inicio,
        dados.data_fim,
    )

    verificar_sobreposicao(
        db,
        aluno_id=matricula.aluno_id,
        ano_letivo_id=matricula.ano_letivo_id,
        inicio=matricula.data_inicio,
        fim=dados.data_fim,
        ignorar_id=matricula.id,
    )

    matricula.data_fim = dados.data_fim

    confirmar_alteracao(db)
    db.refresh(matricula)

    return matricula



@router.post(
    "/{matricula_id}/transferir",
    response_model=TransferenciaResposta,
    status_code=201,
)
def transferir_matricula(
    matricula_id: int,
    dados: TransferenciaCriar,
    db: Session = Depends(get_db),
):
    # 1. Localizar matrícula de origem
    origem = db.scalar(
    select(Matricula)
    .where(Matricula.id == matricula_id)
    .with_for_update()
)

    if origem is None:
        raise HTTPException(
            status_code=404,
            detail="Matricula nao encontrada.",
        )

    if origem.data_fim is not None:
        raise HTTPException(
            status_code=409,
            detail="A matricula de origem ja esta encerrada.",
        )
        
    # Validar o estado cadastral do aluno
    aluno = db.get(Aluno, origem.aluno_id)

    if aluno is None or not aluno.ativo:
        raise HTTPException(
            status_code=409,
            detail="Aluno inexistente ou inativo.",
        )

    # Validar o estado do ano letivo
    ano_letivo = db.get(AnoLetivo, origem.ano_letivo_id)

    if ano_letivo is None or not ano_letivo.ativo:
        raise HTTPException(
            status_code=409,
            detail="Ano letivo inexistente ou inativo.",
        )

    # 2. Validar a turma de destino
    destino = db.get(Turma, dados.turma_destino_id)

    if destino is None:
        raise HTTPException(
            status_code=404,
            detail="Turma de destino nao encontrada.",
        )

    if not destino.ativo:
        raise HTTPException(
            status_code=409,
            detail="Turma de destino inativa.",
        )

    if destino.ano_letivo_id != origem.ano_letivo_id:
        raise HTTPException(
            status_code=409,
            detail="Transferencia entre anos letivos nao permitida.",
        )

    if destino.id == origem.turma_id:
        raise HTTPException(
            status_code=409,
            detail="A turma de destino deve ser diferente.",
        )

    # 3. Validar a data
    if dados.data_transferencia <= origem.data_inicio:
        raise HTTPException(
            status_code=422,
            detail=(
                "A transferencia deve ocorrer depois "
                "do inicio da matricula."
            ),
        )

    fim_origem = dados.data_transferencia - timedelta(days=1)

    # 4. Encerrar matrícula original
    origem.data_fim = fim_origem

    # 5. Criar nova matrícula
    nova = Matricula(
        aluno_id=origem.aluno_id,
        turma_id=destino.id,
        ano_letivo_id=origem.ano_letivo_id,
        data_inicio=dados.data_transferencia,
        data_fim=None,
    )

    db.add(nova)

    # 6. Persistir as duas operações atomicamente
    confirmar_alteracao(db)

    db.refresh(origem)
    db.refresh(nova)

    return TransferenciaResposta(
        matricula_anterior=origem,
        nova_matricula=nova,
    )
