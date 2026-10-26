

"""Consultas administrativas do estado de liberação dos alunos."""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db
from app.domain.estados import Estado
from app.models import (
    Aluno,
    AnoLetivo,
    Liberacao,
    Matricula,
    Turma,
)
from app.schemas.consultas_liberacoes import (
    SituacaoLiberacaoAluno,
)


router = APIRouter(
    prefix="/admin/liberacoes",
    tags=["Admin - Liberacoes"],
    dependencies=[Depends(exigir_admin)],
)


@router.get(
    "",
    response_model=list[SituacaoLiberacaoAluno],
)
def consultar_liberacoes_por_turma(
    turma_id: int = Query(gt=0),
    data: date = Query(),
    estado: Literal[
        "LIBERADO",
        "CANCELADO",
        "SEM_REGISTRO",
    ] | None = Query(default=None),
    busca: str | None = Query(
        default=None,
        max_length=100,
    ),
    db: Session = Depends(get_db),
) -> list[SituacaoLiberacaoAluno]:
    """
    Consulta a situação dos alunos de uma turma
    em determinada data.

    Retorna:
    - Alunos sem liberação;
    - Alunos liberados, com horário autorizado;
    - Alunos com liberação cancelada.

    Permite filtrar por estado, nome ou matrícula.
    """

    # --------------------------------------------------------
    # 1. Validar existência e situação da turma
    # --------------------------------------------------------

    turma = db.get(Turma, turma_id)

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

    # --------------------------------------------------------
    # 2. Construir consulta administrativa
    # --------------------------------------------------------

    consulta = (
        select(
            Aluno.id.label("aluno_id"),
            Aluno.nome_completo,
            Aluno.matricula_institucional,
            Liberacao.estado.label("estado_atual"),
            Liberacao.horario_inicio_liberacao.label(
                "horario_liberacao"
            ),
        )
        .join(
            Matricula,
            Matricula.aluno_id == Aluno.id,
        )
        .join(
            Turma,
            Matricula.turma_id == Turma.id,
        )
        .join(
            AnoLetivo,
            Matricula.ano_letivo_id == AnoLetivo.id,
        )
        .outerjoin(
            Liberacao,
            and_(
                Liberacao.aluno_id == Aluno.id,
                Liberacao.data == data,
            ),
        )
        .where(
            Matricula.turma_id == turma_id,
            Matricula.ano_letivo_id
            == Turma.ano_letivo_id,
            Matricula.data_inicio <= data,
            or_(
                Matricula.data_fim.is_(None),
                Matricula.data_fim >= data,
            ),
            Aluno.ativo.is_(True),
            Turma.ativo.is_(True),
            AnoLetivo.ativo.is_(True),
        )
    )

    # --------------------------------------------------------
    # 3. Filtrar por situação
    # --------------------------------------------------------

    if estado == "SEM_REGISTRO":
        consulta = consulta.where(
            Liberacao.id.is_(None)
        )

    elif estado is not None:
        consulta = consulta.where(
            Liberacao.estado == Estado(estado)
        )

    # --------------------------------------------------------
    # 4. Filtrar por nome ou matrícula institucional
    # --------------------------------------------------------

    if busca is not None and busca.strip():
        termo = (
            busca.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

        consulta = consulta.where(
            or_(
                Aluno.nome_completo.ilike(
                    f"%{termo}%",
                    escape="\\",
                ),
                Aluno.matricula_institucional.ilike(
                    f"%{termo}%",
                    escape="\\",
                ),
            )
        )

    # --------------------------------------------------------
    # 5. Ordenação
    # --------------------------------------------------------

    consulta = consulta.order_by(
        Aluno.nome_completo,
        Aluno.id,
    )

    # --------------------------------------------------------
    # 6. Executar consulta
    # --------------------------------------------------------

    registros = db.execute(consulta).all()

    # --------------------------------------------------------
    # 7. Construir resposta
    # --------------------------------------------------------

    resultado: list[SituacaoLiberacaoAluno] = []

    for registro in registros:
        estado_atual = registro.estado_atual

        situacao = (
            estado_atual.value
            if estado_atual is not None
            else "SEM_REGISTRO"
        )

        # O horário só representa uma autorização ativa
        # quando o estado da liberação é LIBERADO.
        #
        # Cancelamentos e ausência de registro
        # não possuem horário autorizado.
        horario = (
            registro.horario_liberacao
            if situacao == "LIBERADO"
            else None
        )

        resultado.append(
            SituacaoLiberacaoAluno(
                aluno_id=registro.aluno_id,
                nome_completo=registro.nome_completo,
                matricula_institucional=(
                    registro.matricula_institucional
                ),
                turma_id=turma_id,
                data=data,
                estado=situacao,
                horario_inicio_liberacao=horario,
            )
        )

    return resultado
