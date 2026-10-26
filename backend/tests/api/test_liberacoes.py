
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from datetime import date, time
from threading import Event, Lock

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.domain.estados import Acao, Estado, Perfil, TipoAcao
from app.models import (
    Aluno,
    AulaRecorrente,
    GradeHorario,
    HistoricoLiberacao,
    Liberacao,
    Responsavel,
    ResponsavelAluno,
)
from app.services import liberacoes as servico_liberacoes
from app.services.liberacoes import executar_liberacao_responsavel
from tests.api.conftest import login
from tests.api.test_matriculas import (
    autenticar_admin,
    criar_aluno,
    criar_ano,
    criar_turma,
    payload_matricula,
)
from tests.api.test_vinculos import criar_vinculo

pytestmark = pytest.mark.integration

DATA_TESTE = date(2026, 10, 20)  # Terça-feira, conforme relógio dos testes existentes.
HORA_LIBERACAO = time(8, 0)
HORARIO_API = "08:00"


def payload_liberar(horario: str = HORARIO_API) -> dict[str, str]:
    return {"acao": "LIBERAR", "horario_inicio_liberacao": horario}


def criar_grade_teste(db, turma_id: int, data: date = DATA_TESTE) -> None:
    """Cria grade vigente com período elegível para liberação na data do teste."""
    with Session(db) as sessao:
        grade = GradeHorario(
            turma_id=turma_id,
            vigente_desde=date(data.year, 2, 1),
            vigente_ate=None,
            horarios=["08:00", "08:50"],
            hora_termino=time(9, 40),
        )
        sessao.add(grade)
        sessao.flush()
        sessao.add_all([
            AulaRecorrente(
                grade_id=grade.id,
                dia_semana=data.weekday(),
                hora_inicio=time(8, 0),
                descricao="Matemática",
                tipo="AULA",
            ),
            AulaRecorrente(
                grade_id=grade.id,
                dia_semana=data.weekday(),
                hora_inicio=time(8, 50),
                descricao="Português",
                tipo="AULA",
            ),
        ])
        sessao.commit()


def preparar_aluno(
    client_db,
    criar_usuario,
    criar_responsavel,
    db,
    *,
    matricula_codigo: str,
    vincular: bool = True,
    criar_grade: bool = True,
):
    """Prepara cadastros comuns; não autentica o responsável automaticamente."""
    responsavel_id = criar_responsavel()
    headers_admin = autenticar_admin(client_db, criar_usuario)
    ano_id = criar_ano(client_db, headers_admin, ano=2026)
    turma_id = criar_turma(
        client_db, headers_admin, ano_id, identificacao="1 Ano A"
    )
    aluno_id = criar_aluno(
        client_db, headers_admin, matricula=matricula_codigo
    )
    resposta = client_db.post(
        "/admin/matriculas",
        json=payload_matricula(
            aluno_id, turma_id, ano_id, inicio="2026-02-01"
        ),
        headers=headers_admin,
    )
    assert resposta.status_code == 201, resposta.json()

    if criar_grade:
        criar_grade_teste(db, turma_id)

    vinculo_id = None
    if vincular:
        resposta = criar_vinculo(
            client_db, headers_admin, responsavel_id, aluno_id
        )
        assert resposta.status_code == 201, resposta.json()
        vinculo_id = resposta.json()["id"]

    return {
        "aluno_id": aluno_id,
        "turma_id": turma_id,
        "responsavel_id": responsavel_id,
        "vinculo_id": vinculo_id,
        "headers_admin": headers_admin,
    }


def autenticar_responsavel(client_db):
    resposta = login(client_db, email="responsavel1@exemplo.test")
    assert resposta.status_code == 200, resposta.json()
    return (
        {"X-CSRF-Token": resposta.json()["csrf_token"]},
        resposta.json()["usuario"]["id"],
    )


def consultar_registros(db, aluno_id):
    with Session(db) as sessao:
        liberacoes = sessao.scalars(
            select(Liberacao).where(Liberacao.aluno_id == aluno_id)
        ).all()
        historicos = sessao.scalars(
            select(HistoricoLiberacao)
            .where(HistoricoLiberacao.aluno_id == aluno_id)
            .order_by(HistoricoLiberacao.id)
        ).all()
        return liberacoes, historicos


def test_responsavel_libera_aluno_vinculado_na_data_atual(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIB-001",
    )
    headers, usuario_id = autenticar_responsavel(client_db)
    aluno_id = ctx["aluno_id"]

    resposta = client_db.post(
        f"/responsavel/alunos/{aluno_id}/liberacao",
        json=payload_liberar(), headers=headers,
    )
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json() == {
        "aluno_id": aluno_id,
        "data": DATA_TESTE.isoformat(),
        "estado": "LIBERADO",
        "horario_inicio_liberacao": "08:00:00",
    }

    liberacoes, historicos = consultar_registros(db, aluno_id)
    assert len(liberacoes) == 1
    assert liberacoes[0].data == DATA_TESTE
    assert liberacoes[0].estado == Estado.LIBERADO
    assert liberacoes[0].horario_inicio_liberacao == HORA_LIBERACAO
    assert liberacoes[0].atualizado_por_usuario_id == usuario_id
    assert len(historicos) == 1
    assert historicos[0].liberacao_id == liberacoes[0].id
    assert historicos[0].usuario_id == usuario_id
    assert historicos[0].perfil == Perfil.RESPONSAVEL
    assert historicos[0].estado_anterior is None
    assert historicos[0].novo_estado == Estado.LIBERADO
    assert historicos[0].tipo_acao == TipoAcao.LIBERACAO
    assert historicos[0].horario_anterior is None
    assert historicos[0].horario_novo == HORA_LIBERACAO


def test_liberacao_repetida_nao_gera_novo_historico(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIB-REDUND-001",
    )
    headers, _ = autenticar_responsavel(client_db)
    url = f"/responsavel/alunos/{ctx['aluno_id']}/liberacao"
    primeira = client_db.post(url, json=payload_liberar(), headers=headers)
    segunda = client_db.post(url, json=payload_liberar(), headers=headers)
    assert primeira.status_code == 200, primeira.json()
    assert segunda.status_code == 200, segunda.json()
    assert primeira.json()["horario_inicio_liberacao"] == "08:00:00"
    assert segunda.json()["horario_inicio_liberacao"] == "08:00:00"
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert len(historicos) == 1
    assert historicos[0].tipo_acao == TipoAcao.LIBERACAO


def test_responsavel_nao_libera_aluno_sem_vinculo(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="SEM-VINC-001", vincular=False,
        criar_grade=False,
    )
    headers, _ = autenticar_responsavel(client_db)
    resposta = client_db.post(
        f"/responsavel/alunos/{ctx['aluno_id']}/liberacao",
        json=payload_liberar(), headers=headers,
    )
    assert resposta.status_code == 404, resposta.json()
    assert resposta.json()["detail"] == "Aluno nao encontrado."
    assert consultar_registros(db, ctx["aluno_id"]) == ([], [])


def test_responsavel_nao_libera_aluno_com_vinculo_revogado(
    client_db, criar_usuario, criar_responsavel, relogio, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="VINC-REV-LIB-001", criar_grade=False,
    )
    relogio.avancar(seconds=1)
    revogado = client_db.post(
        f"/admin/vinculos/{ctx['vinculo_id']}/revogar",
        headers=ctx["headers_admin"],
    )
    assert revogado.status_code == 200, revogado.json()
    assert revogado.json()["ativo"] is False
    headers, _ = autenticar_responsavel(client_db)
    resposta = client_db.post(
        f"/responsavel/alunos/{ctx['aluno_id']}/liberacao",
        json=payload_liberar(), headers=headers,
    )
    assert resposta.status_code == 404, resposta.json()
    assert resposta.json()["detail"] == "Aluno nao encontrado."
    assert consultar_registros(db, ctx["aluno_id"]) == ([], [])


def test_responsavel_nao_libera_apos_horario_limite(
    client_db, criar_usuario, criar_responsavel, relogio, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIMITE-001", criar_grade=False,
    )
    relogio.avancar(hours=6)
    headers, _ = autenticar_responsavel(client_db)
    resposta = client_db.post(
        f"/responsavel/alunos/{ctx['aluno_id']}/liberacao",
        json=payload_liberar(), headers=headers,
    )
    assert resposta.status_code == 409, resposta.json()
    assert "Horario-limite" in resposta.json()["detail"]
    assert consultar_registros(db, ctx["aluno_id"]) == ([], [])


def test_responsavel_cancela_liberacao_e_preserva_historico(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIB-CANC-001",
    )
    headers, usuario_id = autenticar_responsavel(client_db)
    url = f"/responsavel/alunos/{ctx['aluno_id']}/liberacao"
    primeira = client_db.post(url, json=payload_liberar(), headers=headers)
    segunda = client_db.post(
        url, json={"acao": "CANCELAR"}, headers=headers
    )
    assert primeira.status_code == 200, primeira.json()
    assert segunda.status_code == 200, segunda.json()
    assert segunda.json()["estado"] == "CANCELADO"
    assert segunda.json()["horario_inicio_liberacao"] is None
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert liberacoes[0].estado == Estado.CANCELADO
    assert liberacoes[0].horario_inicio_liberacao is None
    assert liberacoes[0].atualizado_por_usuario_id == usuario_id
    assert len(historicos) == 2
    primeiro, segundo = historicos
    assert (primeiro.estado_anterior, primeiro.novo_estado, primeiro.tipo_acao) == (
        None, Estado.LIBERADO, TipoAcao.LIBERACAO
    )
    assert (segundo.estado_anterior, segundo.novo_estado, segundo.tipo_acao) == (
        Estado.LIBERADO, Estado.CANCELADO, TipoAcao.CANCELAMENTO
    )
    assert (segundo.horario_anterior, segundo.horario_novo) == (
        HORA_LIBERACAO, None
    )
    assert all(h.usuario_id == usuario_id and h.perfil == Perfil.RESPONSAVEL
               for h in historicos)


def test_responsavel_libera_novamente_apos_cancelamento(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIB-RELIB-001",
    )
    headers, usuario_id = autenticar_responsavel(client_db)
    url = f"/responsavel/alunos/{ctx['aluno_id']}/liberacao"
    respostas = [
        client_db.post(url, json=payload_liberar(), headers=headers),
        client_db.post(url, json={"acao": "CANCELAR"}, headers=headers),
        client_db.post(url, json=payload_liberar(), headers=headers),
    ]
    assert [r.status_code for r in respostas] == [200, 200, 200], [
        r.json() for r in respostas
    ]
    assert [r.json()["estado"] for r in respostas] == [
        "LIBERADO", "CANCELADO", "LIBERADO"
    ]
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert liberacoes[0].estado == Estado.LIBERADO
    assert liberacoes[0].horario_inicio_liberacao == HORA_LIBERACAO
    assert liberacoes[0].atualizado_por_usuario_id == usuario_id
    assert len(historicos) == 3
    assert [(h.estado_anterior, h.novo_estado, h.tipo_acao) for h in historicos] == [
        (None, Estado.LIBERADO, TipoAcao.LIBERACAO),
        (Estado.LIBERADO, Estado.CANCELADO, TipoAcao.CANCELAMENTO),
        (Estado.CANCELADO, Estado.LIBERADO, TipoAcao.LIBERACAO),
    ]
    assert [(h.horario_anterior, h.horario_novo) for h in historicos] == [
        (None, HORA_LIBERACAO),
        (HORA_LIBERACAO, None),
        (None, HORA_LIBERACAO),
    ]
    assert all(h.usuario_id == usuario_id and h.perfil == Perfil.RESPONSAVEL
               for h in historicos)


def test_correcao_horario_audita_sem_mudar_estado(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIB-HORA-001",
    )
    headers, _ = autenticar_responsavel(client_db)
    url = f"/responsavel/alunos/{ctx['aluno_id']}/liberacao"
    primeira = client_db.post(url, json=payload_liberar("08:00"), headers=headers)
    segunda = client_db.post(url, json=payload_liberar("08:50"), headers=headers)
    assert primeira.status_code == 200, primeira.json()
    assert segunda.status_code == 200, segunda.json()
    assert segunda.json()["horario_inicio_liberacao"] == "08:50:00"
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert liberacoes[0].horario_inicio_liberacao == time(8, 50)
    assert len(historicos) == 2
    assert historicos[1].estado_anterior == Estado.LIBERADO
    assert historicos[1].novo_estado == Estado.LIBERADO
    assert historicos[1].horario_anterior == time(8, 0)
    assert historicos[1].horario_novo == time(8, 50)
    assert historicos[1].tipo_acao == TipoAcao.LIBERACAO


def test_liberacao_sem_horario_e_rejeitada(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="LIB-SEM-HORA-001", criar_grade=False,
    )
    headers, _ = autenticar_responsavel(client_db)
    resposta = client_db.post(
        f"/responsavel/alunos/{ctx['aluno_id']}/liberacao",
        json={"acao": "LIBERAR"}, headers=headers,
    )
    assert resposta.status_code == 422, resposta.json()
    assert consultar_registros(db, ctx["aluno_id"]) == ([], [])


def test_falha_no_historico_reverte_liberacao(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="ROLLBACK-001",
    )
    headers, _ = autenticar_responsavel(client_db)

    def falhar_persistencia_historico(sessao, flush_context, instances):
        if any(isinstance(obj, HistoricoLiberacao) for obj in sessao.new):
            raise RuntimeError("Falha simulada na persistencia do historico")

    event.listen(Session, "before_flush", falhar_persistencia_historico)
    try:
        with pytest.raises(RuntimeError, match="Falha simulada"):
            client_db.post(
                f"/responsavel/alunos/{ctx['aluno_id']}/liberacao",
                json=payload_liberar(), headers=headers,
            )
    finally:
        event.remove(Session, "before_flush", falhar_persistencia_historico)
    assert consultar_registros(db, ctx["aluno_id"]) == ([], [])


def test_falha_no_historico_reverte_cancelamento(
    client_db, criar_usuario, criar_responsavel, db
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="ROLLBACK-CANC-001",
    )
    headers, usuario_id = autenticar_responsavel(client_db)
    url = f"/responsavel/alunos/{ctx['aluno_id']}/liberacao"
    primeira = client_db.post(url, json=payload_liberar(), headers=headers)
    assert primeira.status_code == 200, primeira.json()
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == len(historicos) == 1
    liberacao_id, historico_id = liberacoes[0].id, historicos[0].id

    def falhar_persistencia_historico(sessao, flush_context, instances):
        if any(isinstance(obj, HistoricoLiberacao) for obj in sessao.new):
            raise RuntimeError("Falha simulada no historico do cancelamento")

    event.listen(Session, "before_flush", falhar_persistencia_historico)
    try:
        with pytest.raises(RuntimeError, match="Falha simulada"):
            client_db.post(url, json={"acao": "CANCELAR"}, headers=headers)
    finally:
        event.remove(Session, "before_flush", falhar_persistencia_historico)

    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == len(historicos) == 1
    assert liberacoes[0].id == liberacao_id
    assert liberacoes[0].estado == Estado.LIBERADO
    assert liberacoes[0].horario_inicio_liberacao == HORA_LIBERACAO
    assert liberacoes[0].atualizado_por_usuario_id == usuario_id
    assert historicos[0].id == historico_id
    assert historicos[0].novo_estado == Estado.LIBERADO


def test_duas_liberacoes_simultaneas_nao_duplicam_historico(
    client_db, criar_usuario, criar_responsavel, db,
    relogio, settings_teste, monkeypatch,
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="CONC-LIB-001",
    )
    headers, usuario_id = autenticar_responsavel(client_db)
    _ = headers
    primeira_avaliando = Event()
    segunda_avaliando = Event()
    controle = Lock()
    chamadas = 0
    avaliar_original = servico_liberacoes.avaliar_operacao

    def avaliacao_controlada(pedido):
        nonlocal chamadas
        with controle:
            chamadas += 1
            numero = chamadas
        if numero == 1:
            primeira_avaliando.set()
            segunda_avaliando.wait(timeout=2)
        elif numero == 2:
            segunda_avaliando.set()
        return avaliar_original(pedido)

    monkeypatch.setattr(servico_liberacoes, "avaliar_operacao", avaliacao_controlada)

    def executar():
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao, aluno_id=ctx["aluno_id"], usuario_id=usuario_id,
                acao=Acao.LIBERAR, horario_inicio_liberacao=HORA_LIBERACAO,
                agora=relogio.agora(), settings=settings_teste,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        primeiro = executor.submit(executar)
        assert primeira_avaliando.wait(timeout=10)
        segundo = executor.submit(executar)
        resultados = [primeiro.result(timeout=15), segundo.result(timeout=15)]

    assert all(r.estado == Estado.LIBERADO for r in resultados)
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert liberacoes[0].horario_inicio_liberacao == HORA_LIBERACAO
    assert len(historicos) == 1
    assert historicos[0].tipo_acao == TipoAcao.LIBERACAO


def test_liberacao_e_cancelamento_concorrentes_preservam_historico(
    client_db, criar_usuario, criar_responsavel, db,
    relogio, settings_teste, monkeypatch,
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="CONC-CANCEL-001",
    )
    _, usuario_id = autenticar_responsavel(client_db)
    primeira_em_avaliacao = Event()
    liberar_primeira = Event()
    avaliar_original = servico_liberacoes.avaliar_operacao

    def avaliacao_controlada(pedido):
        if pedido.acao == Acao.LIBERAR:
            primeira_em_avaliacao.set()
            if not liberar_primeira.wait(timeout=10):
                raise TimeoutError("Primeira operacao nao foi liberada.")
        return avaliar_original(pedido)

    monkeypatch.setattr(servico_liberacoes, "avaliar_operacao", avaliacao_controlada)

    def executar(acao):
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao, aluno_id=ctx["aluno_id"], usuario_id=usuario_id,
                acao=acao,
                horario_inicio_liberacao=(
                    HORA_LIBERACAO if acao == Acao.LIBERAR else None
                ),
                agora=relogio.agora(), settings=settings_teste,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        primeira = executor.submit(executar, Acao.LIBERAR)
        try:
            assert primeira_em_avaliacao.wait(timeout=10)
            segunda = executor.submit(executar, Acao.CANCELAR)
        finally:
            liberar_primeira.set()
        resultado_primeiro = primeira.result(timeout=15)
        resultado_segundo = segunda.result(timeout=15)

    assert resultado_primeiro.estado == Estado.LIBERADO
    assert resultado_segundo.estado == Estado.CANCELADO
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert liberacoes[0].estado == Estado.CANCELADO
    assert liberacoes[0].horario_inicio_liberacao is None
    assert len(historicos) == 2
    assert [(h.estado_anterior, h.novo_estado, h.tipo_acao) for h in historicos] == [
        (None, Estado.LIBERADO, TipoAcao.LIBERACAO),
        (Estado.LIBERADO, Estado.CANCELADO, TipoAcao.CANCELAMENTO),
    ]


def test_revogacao_aguarda_liberacao_em_andamento(
    client_db, criar_usuario, criar_responsavel, db,
    relogio, settings_teste, monkeypatch,
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="CONC-REV-001",
    )
    with Session(db) as sessao:
        responsavel = sessao.get(Responsavel, ctx["responsavel_id"])
        assert responsavel is not None
        usuario_id = responsavel.usuario_id
    relogio.avancar(seconds=1)
    liberacao_em_avaliacao = Event()
    permitir_liberacao = Event()
    avaliar_original = servico_liberacoes.avaliar_operacao

    def avaliacao_controlada(pedido):
        liberacao_em_avaliacao.set()
        if not permitir_liberacao.wait(timeout=10):
            raise TimeoutError("Liberacao nao foi desbloqueada.")
        return avaliar_original(pedido)

    monkeypatch.setattr(servico_liberacoes, "avaliar_operacao", avaliacao_controlada)

    def executar_liberacao():
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao, aluno_id=ctx["aluno_id"], usuario_id=usuario_id,
                acao=Acao.LIBERAR, horario_inicio_liberacao=HORA_LIBERACAO,
                agora=relogio.agora(), settings=settings_teste,
            )

    def executar_revogacao():
        return client_db.post(
            f"/admin/vinculos/{ctx['vinculo_id']}/revogar",
            headers=ctx["headers_admin"],
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_liberacao = executor.submit(executar_liberacao)
        try:
            assert liberacao_em_avaliacao.wait(timeout=10)
            futuro_revogacao = executor.submit(executar_revogacao)
            with pytest.raises(FutureTimeoutError):
                futuro_revogacao.result(timeout=0.5)
        finally:
            permitir_liberacao.set()
        resultado_liberacao = futuro_liberacao.result(timeout=15)
        resultado_revogacao = futuro_revogacao.result(timeout=15)

    assert resultado_liberacao.estado == Estado.LIBERADO
    assert resultado_revogacao.status_code == 200, resultado_revogacao.json()
    assert resultado_revogacao.json()["ativo"] is False
    liberacoes, historicos = consultar_registros(db, ctx["aluno_id"])
    assert len(liberacoes) == 1
    assert liberacoes[0].estado == Estado.LIBERADO
    assert len(historicos) == 1
    assert historicos[0].tipo_acao == TipoAcao.LIBERACAO


def test_liberacao_aguarda_revogacao_e_e_rejeitada(
    client_db, criar_usuario, criar_responsavel, db,
    relogio, settings_teste,
):
    ctx = preparar_aluno(
        client_db, criar_usuario, criar_responsavel, db,
        matricula_codigo="REV-PRIMEIRO-001", criar_grade=False,
    )
    with Session(db) as sessao:
        responsavel = sessao.get(Responsavel, ctx["responsavel_id"])
        assert responsavel is not None
        usuario_id = responsavel.usuario_id

    relogio.avancar(seconds=1)
    revogacao_bloqueou = Event()
    permitir_revogacao = Event()
    controle = Lock()
    pausou = False

    def pausar_revogacao(sessao, flush_context, instances):
        nonlocal pausou
        if not any(
            isinstance(obj, ResponsavelAluno) and obj.revogado_em is not None
            for obj in sessao.dirty
        ):
            return
        with controle:
            if pausou:
                return
            pausou = True
        revogacao_bloqueou.set()
        if not permitir_revogacao.wait(timeout=10):
            raise TimeoutError("Revogacao nao foi liberada.")

    event.listen(Session, "before_flush", pausar_revogacao)

    def executar_revogacao():
        return client_db.post(
            f"/admin/vinculos/{ctx['vinculo_id']}/revogar",
            headers=ctx["headers_admin"],
        )

    def executar_liberacao():
        with Session(db) as sessao:
            return executar_liberacao_responsavel(
                sessao, aluno_id=ctx["aluno_id"], usuario_id=usuario_id,
                acao=Acao.LIBERAR, horario_inicio_liberacao=HORA_LIBERACAO,
                agora=relogio.agora(), settings=settings_teste,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_revogacao = executor.submit(executar_revogacao)
            try:
                assert revogacao_bloqueou.wait(timeout=10)
                futuro_liberacao = executor.submit(executar_liberacao)
                with pytest.raises(FutureTimeoutError):
                    futuro_liberacao.result(timeout=0.5)
            finally:
                permitir_revogacao.set()
            resposta_revogacao = futuro_revogacao.result(timeout=15)
            with pytest.raises(HTTPException) as exc:
                futuro_liberacao.result(timeout=15)
            assert exc.value.status_code == 404
    finally:
        permitir_revogacao.set()
        event.remove(Session, "before_flush", pausar_revogacao)

    assert resposta_revogacao.status_code == 200, resposta_revogacao.json()
    with Session(db) as sessao:
        vinculo = sessao.get(ResponsavelAluno, ctx["vinculo_id"])
        assert vinculo is not None and vinculo.revogado_em is not None
    assert consultar_registros(db, ctx["aluno_id"]) == ([], [])


def test_fixture_cenario_liberacao_prepara_dados_validos(
    client_db, cenario_liberacao
):
    ctx = cenario_liberacao()
    assert isinstance(ctx["responsavel_id"], int)
    assert isinstance(ctx["aluno_id"], int)
    assert isinstance(ctx["vinculo_id"], int)
    resposta = client_db.get(f"/admin/vinculos/{ctx['vinculo_id']}")
    assert resposta.status_code == 200, resposta.json()
    assert resposta.json()["aluno_id"] == ctx["aluno_id"]
    assert resposta.json()["responsavel_id"] == ctx["responsavel_id"]
