
"""API administrativa de grades horárias."""

from datetime import date, time

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db
from app.models import GradeHorario, Turma
from app.services.grades_horarios import (
    ErroGrade,
    salvar_grade,
)
from app.services.importacao_grade import (
    GradeCSVInvalida,
    importar_grade_csv,
)


router = APIRouter(
    prefix="/admin/turmas",
    tags=["Administracao - Grades horarias"],
    dependencies=[Depends(exigir_admin)],
)

MAX_CSV_BYTES = 64 * 1024


class GradeResposta(BaseModel):
    id: int
    turma_id: int
    vigente_desde: date
    vigente_ate: date | None
    horarios: list[str]
    total_atividades: int
    hora_termino: time | None


@router.get(
    "/{turma_id}/grades",
    response_model=list[GradeResposta],
)
def listar_grades(
    turma_id: int,
    db: Session = Depends(get_db),
):
    if db.get(Turma, turma_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Turma nao encontrada.",
        )

    grades = db.scalars(
        select(GradeHorario)
        .where(GradeHorario.turma_id == turma_id)
        .order_by(GradeHorario.vigente_desde.desc())
    ).all()

    from app.models import AulaRecorrente
    from sqlalchemy import func

    respostas = []

    for grade in grades:
        total = db.scalar(
            select(func.count(AulaRecorrente.id))
            .where(AulaRecorrente.grade_id == grade.id)
        )

        respostas.append(
            GradeResposta(
                id=grade.id,
                turma_id=grade.turma_id,
                vigente_desde=grade.vigente_desde,
                vigente_ate=grade.vigente_ate,
                horarios=grade.horarios,
                total_atividades=total or 0,
                hora_termino=grade.hora_termino,
            )
        )

    return respostas


@router.post(
    "/{turma_id}/grade/importar",
    response_model=GradeResposta,
    status_code=201,
)
async def importar_grade(
    turma_id: int,
    arquivo: UploadFile = File(...),
    vigente_desde: date = Form(...),
    hora_termino: time = Form(...),
    db: Session = Depends(get_db),
):
    nome = (arquivo.filename or "").lower()

    if not nome.endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="Envie um arquivo CSV.",
        )

    conteudo_bytes = await arquivo.read(
        MAX_CSV_BYTES + 1
    )

    if len(conteudo_bytes) > MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Arquivo CSV muito grande.",
        )

    try:
        conteudo = conteudo_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="O CSV deve utilizar UTF-8.",
        ) from exc

    try:
        grade_importada = importar_grade_csv(
            conteudo
        )

        nova = salvar_grade(
            db=db,
            turma_id=turma_id,
            vigente_desde=vigente_desde,
            grade_importada=grade_importada,
            hora_termino=hora_termino,
        )

    except GradeCSVInvalida as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except ErroGrade as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return GradeResposta(
        id=nova.id,
        turma_id=nova.turma_id,
        vigente_desde=nova.vigente_desde,
        vigente_ate=nova.vigente_ate,
        horarios=nova.horarios,
        total_atividades=len(grade_importada.aulas),
        hora_termino=nova.hora_termino,
    )
