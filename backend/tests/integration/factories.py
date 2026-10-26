"""Fabricas de dados FICTICIOS para os testes de integracao."""
from datetime import UTC, date, datetime
from itertools import count

from app.domain.estados import Estado, Perfil, TipoAcao
from app.domain.turno import Turno
from app.models import (
    Aluno,
    AnoLetivo,
    HistoricoLiberacao,
    Liberacao,
    Responsavel,
    ResponsavelAluno,
    Turma,
    Usuario,
)

_seq = count(1)
HOJE = date(2026, 10, 20)
INICIO_2026 = datetime(2026, 1, 1, tzinfo=UTC)


def novo_usuario(s, perfil=Perfil.RESPONSAVEL, **kw):
    n = next(_seq)
    u = Usuario(email=f"pessoa{n}@exemplo.test", senha_hash="hash-ficticio", perfil=perfil, **kw)
    s.add(u)
    s.flush()
    return u


def novo_responsavel(s, **kw):
    n = next(_seq)
    usuario = kw.pop("usuario", None) or novo_usuario(s)
    r = Responsavel(usuario_id=usuario.id, nome_completo=f"Responsavel Ficticio {n}", **kw)
    s.add(r)
    s.flush()
    return r


def novo_aluno(s, **kw):
    n = next(_seq)
    a = Aluno(nome_completo=f"Aluno Ficticio {n}", **kw)
    s.add(a)
    s.flush()
    return a


def novo_ano_letivo(s, ano=2026):
    al = AnoLetivo(ano=ano)
    s.add(al)
    s.flush()
    return al


def nova_turma(s, ano_letivo=None, identificacao="1o Ano A", turno=Turno.MANHA, **kw):
    ano_letivo = ano_letivo or novo_ano_letivo(s)
    t = Turma(
        identificacao=identificacao,
        ano_escolar=1,
        ano_letivo_id=ano_letivo.id,
        turno=turno,
        **kw,
    )
    s.add(t)
    s.flush()
    return t


def novo_vinculo(s, responsavel, aluno, **kw):
    kw.setdefault("vigente_desde", INICIO_2026)
    v = ResponsavelAluno(responsavel_id=responsavel.id, aluno_id=aluno.id, **kw)
    s.add(v)
    s.flush()
    return v


def nova_liberacao(s, aluno, usuario=None, estado=Estado.LIBERADO, data=HOJE):
    lib = Liberacao(
        aluno_id=aluno.id,
        data=data,
        estado=estado,
        atualizado_por_usuario_id=usuario.id if usuario else None,
    )
    s.add(lib)
    s.flush()
    return lib


def novo_historico(s, liberacao, usuario, **kw):
    campos = dict(
        liberacao_id=liberacao.id,
        aluno_id=liberacao.aluno_id,
        usuario_id=usuario.id,
        perfil=Perfil.RESPONSAVEL,
        estado_anterior=None,
        novo_estado=Estado.LIBERADO,
        tipo_acao=TipoAcao.LIBERACAO,
    )
    campos.update(kw)
    h = HistoricoLiberacao(**campos)
    s.add(h)
    s.flush()
    return h