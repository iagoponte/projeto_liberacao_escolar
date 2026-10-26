
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin_alunos,
    anos_letivos,
    auth,
    eventos,
    liberacoes,
    matriculas,
    responsavel_alunos,
    turmas,
    vinculos,
    agenda_responsavel,
    consultas_liberacoes,
    historico_liberacoes,
    correcao_liberacoes,
    consultas_liberacoes_responsavel,
    admin_responsaveis,
    grades_horarios,
    agenda_efetiva_admin,
)

app = FastAPI(title="Liberacao Escolar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)

app.include_router(auth.router)
app.include_router(admin_alunos.router)
app.include_router(responsavel_alunos.router)
app.include_router(anos_letivos.router)
app.include_router(turmas.router)
app.include_router(matriculas.router)
app.include_router(vinculos.router)
app.include_router(liberacoes.router)
app.include_router(eventos.router)
app.include_router(agenda_responsavel.router)
app.include_router(consultas_liberacoes.router)
app.include_router(historico_liberacoes.router)
app.include_router(correcao_liberacoes.router)
app.include_router(consultas_liberacoes_responsavel.router)
app.include_router(admin_responsaveis.router)
app.include_router(grades_horarios.router)
app.include_router(agenda_efetiva_admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
