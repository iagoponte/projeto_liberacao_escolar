"""Fixtures dos testes de API que usam PostgreSQL real, relogio controlavel e settings de teste."""
from datetime import UTC, datetime, timedelta, date, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Responsavel

from app.api.deps import get_db, get_relogio
from app.core.config import Settings, get_settings
from app.core.seguranca import hash_senha
from app.domain.estados import Perfil
from app.models import Auditoria, Usuario
from tests.integration.conftest import db, engine, session  # noqa: F401
from app.models import GradeHorario, AulaRecorrente

SENHA = "senha-correta-123"
_HASH_SENHA = hash_senha(SENHA)  # calculado uma vez: Argon2 e propositalmente lento


class RelogioMutavel:
    """Relogio de teste que pode ser avancado."""

    def __init__(self, instante: datetime) -> None:
        self._instante = instante

    def agora(self) -> datetime:
        return self._instante

    def avancar(self, **kw) -> None:
        self._instante += timedelta(**kw)


@pytest.fixture
def relogio():
    # 10:00 UTC = 07:00 em Brasilia, 20/out/2026
    return RelogioMutavel(datetime(2026, 10, 20, 10, 0, tzinfo=UTC))


@pytest.fixture
def settings_teste():
    return Settings(
        _env_file=None,
        DATABASE_URL="postgresql+psycopg://nao-usado:x@localhost/nao_usado_test",
        SCHOOL_TIMEZONE="America/Sao_Paulo",
        SECRET_KEY="segredo-somente-para-testes-" + "x" * 20,
        COOKIE_SECURE=False,  # o TestClient usa http://
    )


@pytest.fixture
def client_db(db, relogio, settings_teste):  # noqa: F811
    from app.main import app

    def _get_db():
        with Session(db) as s:
            yield s

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_settings] = lambda: settings_teste
    app.dependency_overrides[get_relogio] = lambda: relogio
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def criar_usuario(db):  # noqa: F811
    def _criar(email=f"pessoa@exemplo.test", perfil=Perfil.RESPONSAVEL, ativo=True, senha_hash=None):
        with Session(db) as s:
            u = Usuario(
                email=email,
                senha_hash=senha_hash or _HASH_SENHA,
                perfil=perfil,
                ativo=ativo,
            )
            s.add(u)
            s.commit()
            return u.id

    return _criar


@pytest.fixture
def eventos(db):  # noqa: F811
    """Lista os eventos de auditoria de um tipo (mais antigos primeiro)."""

    def _listar(tipo):
        with Session(db) as s:
            consulta = select(Auditoria).where(Auditoria.tipo_evento == tipo).order_by(Auditoria.id)
            return list(s.scalars(consulta))

    return _listar


def login(client, email="pessoa@exemplo.test", senha=SENHA):
    return client.post("/auth/login", json={"email": email, "senha": senha})


@pytest.fixture
def cenario_liberacao(
    client_db,
    criar_usuario,
    criar_responsavel,
):
    """Prepara aluno matriculado e responsável vinculado.

    Retorna uma função para criar cenários independentes.
    """
    from tests.api.test_matriculas import (
        autenticar_admin,
        criar_aluno,
        criar_ano,
        criar_turma,
        payload_matricula,
    )
    from tests.api.test_vinculos import criar_vinculo

    contador = 0

    def _preparar():
        nonlocal contador
        contador += 1

        responsavel_id = criar_responsavel()

        headers_admin = autenticar_admin(
            client_db,
            criar_usuario,
        )

        ano_id = criar_ano(
            client_db,
            headers_admin,
            ano=2026,
        )

        turma_id = criar_turma(
            client_db,
            headers_admin,
            ano_id,
            identificacao="1 Ano A",
        )

        aluno_id = criar_aluno(
            client_db,
            headers_admin,
            matricula=f"CEN-LIB-{contador:03d}",
        )

        matricula = client_db.post(
            "/admin/matriculas",
            json=payload_matricula(
                aluno_id,
                turma_id,
                ano_id,
                inicio="2026-02-01",
            ),
            headers=headers_admin,
        )

        assert matricula.status_code == 201

        vinculo = criar_vinculo(
            client_db,
            headers_admin,
            responsavel_id,
            aluno_id,
        )

        assert vinculo.status_code == 201

        return {
            "responsavel_id": responsavel_id,
            "aluno_id": aluno_id,
            "ano_id": ano_id,
            "turma_id": turma_id,
            "vinculo_id": vinculo.json()["id"],
            "headers_admin": headers_admin,
        }

    return _preparar


@pytest.fixture
def criar_grade_liberacao(db):
    def _criar(
        turma_id: int,
        data_referencia: date,
        hora_inicio: time = time(8, 0),
    ):
        with Session(db) as session:
            grade = GradeHorario(
                turma_id=turma_id,
                vigente_desde=date(
                    data_referencia.year, 1, 1
                ),
                vigente_ate=None,
                horarios=["08:00", "08:50"],
                hora_termino=time(9, 40),
            )

            session.add(grade)
            session.flush()

            session.add(
                AulaRecorrente(
                    grade_id=grade.id,
                    dia_semana=data_referencia.weekday(),
                    hora_inicio=hora_inicio,
                    descricao="Aula de teste",
                    tipo="AULA",
                )
            )

            session.commit()

        return grade.id

    return _criar