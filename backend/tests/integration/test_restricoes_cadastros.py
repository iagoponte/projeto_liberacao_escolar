"""E3 - restricoes dos cadastros aplicadas pelo proprio PostgreSQL."""
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Aluno, EventoAgenda, Liberacao, Matricula, ResponsavelAluno, Turma, Usuario
from tests.integration import factories as f

pytestmark = pytest.mark.integration


def test_email_de_usuario_e_unico(session):
    u = f.novo_usuario(session)
    session.add(Usuario(email=u.email, senha_hash="x", perfil=u.perfil))
    with pytest.raises(IntegrityError):
        session.flush()


def test_perfil_de_usuario_invalido_e_rejeitado(session):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO usuarios (email, senha_hash, perfil) "
                "VALUES ('x@exemplo.test', 'h', 'FUNCIONARIO')"
            )
        )


def test_matricula_institucional_unica_quando_informada(session):
    f.novo_aluno(session, matricula_institucional="2026-0001")
    session.add(Aluno(nome_completo="Outro Aluno", matricula_institucional="2026-0001"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_varios_alunos_sem_matricula_institucional_sao_permitidos(session):
    f.novo_aluno(session)
    f.novo_aluno(session)
    assert session.scalar(select(func.count()).select_from(Aluno)) == 2


def test_vinculo_ativo_duplicado_e_rejeitado(session):
    r, a = f.novo_responsavel(session), f.novo_aluno(session)
    f.novo_vinculo(session, r, a)
    session.add(ResponsavelAluno(responsavel_id=r.id, aluno_id=a.id, vigente_desde=f.INICIO_2026))
    with pytest.raises(IntegrityError):
        session.flush()


def test_novo_vinculo_apos_revogacao_preserva_o_anterior(session):
    r, a = f.novo_responsavel(session), f.novo_aluno(session)
    antigo = f.novo_vinculo(session, r, a)
    antigo.revogado_em = datetime(2026, 6, 1, tzinfo=UTC)
    session.flush()
    f.novo_vinculo(session, r, a, vigente_desde=datetime(2026, 8, 1, tzinfo=UTC))
    total = session.scalar(
        select(func.count()).select_from(ResponsavelAluno).where(ResponsavelAluno.aluno_id == a.id)
    )
    assert total == 2


def test_vinculo_revogado_antes_de_comecar_e_rejeitado(session):
    r, a = f.novo_responsavel(session), f.novo_aluno(session)
    session.add(
        ResponsavelAluno(
            responsavel_id=r.id,
            aluno_id=a.id,
            vigente_desde=datetime(2026, 6, 1, tzinfo=UTC),
            revogado_em=datetime(2026, 5, 1, tzinfo=UTC),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_responsavel_e_vinculado_a_um_unico_usuario(session):
    r = f.novo_responsavel(session)
    session.add(f.Responsavel(usuario_id=r.usuario_id, nome_completo="Duplicado"))
    with pytest.raises(IntegrityError):
        session.flush()


def test_identificacao_de_turma_e_unica_por_ano_letivo(session):
    al = f.novo_ano_letivo(session)
    f.nova_turma(session, al, "1o Ano A")
    session.add(
        Turma(
            identificacao="1o Ano A",
            ano_escolar=1,
            ano_letivo_id=al.id,
            turno=f.Turno.NOITE,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_mesma_identificacao_em_outro_ano_letivo_e_permitida(session):
    f.nova_turma(session, f.novo_ano_letivo(session, 2026), "1o Ano A")
    f.nova_turma(session, f.novo_ano_letivo(session, 2027), "1o Ano A")


def test_turno_invalido_e_rejeitado(session):
    al = f.novo_ano_letivo(session)
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO turmas (identificacao, ano_escolar, ano_letivo_id, turno, ativo) "
                f"VALUES ('1o Ano Z', 1, {al.id}, 'TARDE', true)"
            )
        )


def test_matricula_exige_turma_do_mesmo_ano_letivo(session):
    a = f.novo_aluno(session)
    turma_2026 = f.nova_turma(session, f.novo_ano_letivo(session, 2026))
    outro_ano = f.novo_ano_letivo(session, 2027)
    session.add(
        Matricula(
            aluno_id=a.id,
            turma_id=turma_2026.id,
            ano_letivo_id=outro_ano.id,
            data_inicio=date(2026, 2, 1),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_so_uma_matricula_aberta_por_aluno_e_ano_letivo(session):
    a = f.novo_aluno(session)
    turma = f.nova_turma(session)
    for _ in range(2):
        session.add(
            Matricula(
                aluno_id=a.id,
                turma_id=turma.id,
                ano_letivo_id=turma.ano_letivo_id,
                data_inicio=date(2026, 2, 1),
            )
        )
    with pytest.raises(IntegrityError):
        session.flush()


def test_mudanca_de_turma_preserva_a_matricula_anterior(session):
    a = f.novo_aluno(session)
    al = f.novo_ano_letivo(session)
    t1, t2 = f.nova_turma(session, al, "1o Ano A"), f.nova_turma(session, al, "1o Ano E")
    m1 = Matricula(
        aluno_id=a.id, turma_id=t1.id, ano_letivo_id=al.id, data_inicio=date(2026, 2, 1)
    )
    session.add(m1)
    session.flush()
    m1.data_fim = date(2026, 5, 31)
    session.flush()
    session.add(
        Matricula(aluno_id=a.id, turma_id=t2.id, ano_letivo_id=al.id, data_inicio=date(2026, 6, 1))
    )
    session.flush()
    assert session.scalar(select(func.count()).select_from(Matricula)) == 2


def test_matricula_com_fim_antes_do_inicio_e_rejeitada(session):
    a = f.novo_aluno(session)
    turma = f.nova_turma(session)
    session.add(
        Matricula(
            aluno_id=a.id,
            turma_id=turma.id,
            ano_letivo_id=turma.ano_letivo_id,
            data_inicio=date(2026, 6, 1),
            data_fim=date(2026, 5, 1),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_evento_com_fim_antes_do_inicio_e_rejeitado(session):
    turma = f.nova_turma(session)
    session.add(
        EventoAgenda(
            turma_id=turma.id,
            titulo="Passeio",
            data_inicio=date(2026, 10, 21),
            data_fim=date(2026, 10, 20),
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()


def test_evento_de_agenda_nao_cria_liberacoes(session):
    turma = f.nova_turma(session)
    f.novo_aluno(session)
    session.add(
        EventoAgenda(
            turma_id=turma.id,
            titulo="Feira de Ciencias",
            data_inicio=f.HOJE,
            data_fim=f.HOJE,
        )
    )
    session.flush()
    assert session.scalar(select(func.count()).select_from(Liberacao)) == 0


def test_aluno_com_liberacao_nao_pode_ser_excluido(session):
    a = f.novo_aluno(session)
    f.nova_liberacao(session, a)
    with pytest.raises(IntegrityError):
        session.execute(text(f"DELETE FROM alunos WHERE id = {a.id}"))