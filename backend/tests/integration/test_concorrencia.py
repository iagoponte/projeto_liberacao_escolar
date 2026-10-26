"""E3 - concorrencia real: varias conexoes simultaneas contra o mesmo PostgreSQL."""
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.integration import factories as f

pytestmark = pytest.mark.integration

N = 8


@pytest.fixture
def ids(db):
    with Session(db) as s:
        u, a = f.novo_usuario(s), f.novo_aluno(s)
        s.commit()
        return u.id, a.id


def disparar(funcao, n=N):
    """Executa `funcao(i)` em n threads, todas liberadas ao mesmo tempo."""
    barreira = threading.Barrier(n)

    def alvo(i):
        barreira.wait()
        return funcao(i)

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(alvo, range(n)))


def total(db, tabela):
    with db.connect() as c:
        return c.execute(text(f"SELECT count(*) FROM {tabela}")).scalar()


def test_insercoes_simultaneas_geram_um_unico_registro(db, ids):
    _, aluno_id = ids

    def inserir(_):
        try:
            with db.begin() as c:
                c.execute(
                    text(
                        "INSERT INTO liberacoes (aluno_id, data, estado) "
                        "VALUES (:a, '2026-10-20', 'LIBERADO')"
                    ),
                    {"a": aluno_id},
                )
            return "ok"
        except IntegrityError:
            return "duplicado"

    resultados = disparar(inserir)
    assert resultados.count("ok") == 1
    assert resultados.count("duplicado") == N - 1
    assert total(db, "liberacoes") == 1


def test_on_conflict_do_nothing_cria_um_registro_sem_erros(db, ids):
    _, aluno_id = ids

    def inserir(_):
        with db.begin() as c:
            return c.execute(
                text(
                    "INSERT INTO liberacoes (aluno_id, data, estado) "
                    "VALUES (:a, '2026-10-20', 'LIBERADO') "
                    "ON CONFLICT (aluno_id, data) DO NOTHING"
                ),
                {"a": aluno_id},
            ).rowcount

    criadas = disparar(inserir)
    assert sum(criadas) == 1
    assert total(db, "liberacoes") == 1


def test_for_update_serializa_alteracoes_e_mantem_estado_e_historico_consistentes(db, ids):
    usuario_id, aluno_id = ids
    with db.begin() as c:
        lib_id = c.execute(
            text(
                "INSERT INTO liberacoes (aluno_id, data, estado) "
                "VALUES (:a, '2026-10-20', 'LIBERADO') RETURNING id"
            ),
            {"a": aluno_id},
        ).scalar()

    def alternar(_):
        """Le o estado sob bloqueio, grava o oposto e o historico na mesma transacao."""
        with db.begin() as c:
            atual = c.execute(
                text("SELECT estado FROM liberacoes WHERE id = :i FOR UPDATE"), {"i": lib_id}
            ).scalar()
            time.sleep(0.2)  # amplia a janela de corrida
            novo = "CANCELADO" if atual == "LIBERADO" else "LIBERADO"
            tipo = "CANCELAMENTO" if novo == "CANCELADO" else "LIBERACAO"
            c.execute(
                text("UPDATE liberacoes SET estado = :n WHERE id = :i"), {"n": novo, "i": lib_id}
            )
            c.execute(
                text(
                    "INSERT INTO historico_liberacoes (liberacao_id, aluno_id, usuario_id, "
                    "perfil, estado_anterior, novo_estado, tipo_acao) "
                    "VALUES (:i, :a, :u, 'RESPONSAVEL', :ant, :n, :t)"
                ),
                {"i": lib_id, "a": aluno_id, "u": usuario_id, "ant": atual, "n": novo, "t": tipo},
            )

    disparar(alternar, n=4)

    with db.connect() as c:
        historico = c.execute(
            text(
                "SELECT estado_anterior, novo_estado FROM historico_liberacoes "
                "WHERE liberacao_id = :i ORDER BY id"
            ),
            {"i": lib_id},
        ).all()
        estado_final = c.execute(
            text("SELECT estado FROM liberacoes WHERE id = :i"), {"i": lib_id}
        ).scalar()

    assert len(historico) == 4
    assert historico[0][0] == "LIBERADO"
    for anterior, atual in zip(historico, historico[1:], strict=False):
        assert atual[0] == anterior[1], "a cadeia do historico deve ser continua"
    assert historico[-1][1] == estado_final