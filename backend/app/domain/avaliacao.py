from dataclasses import dataclass
from datetime import date, datetime

from app.domain.erros import ForaDoHorarioLimite, VinculoInvalido
from app.domain.estados import Acao, Estado, Mudanca, Perfil, Redundante, decidir_transicao
from app.domain.relogio import data_escolar, validar_data_alvo
from app.domain.turno import Turno, dentro_do_limite
from app.domain.vinculo import Vinculo


@dataclass(frozen=True)
class PedidoOperacao:
    perfil: Perfil
    acao: Acao
    estado_atual: Estado | None
    agora: datetime
    fuso: str
    turno: Turno
    vinculo: Vinculo | None
    motivo: str | None = None
    data_solicitada: date | None = None


@dataclass(frozen=True)
class ResultadoAvaliacao:
    data_alvo: date
    decisao: Mudanca | Redundante


def avaliar_operacao(p: PedidoOperacao) -> ResultadoAvaliacao:
    """Aplica, nesta ordem: data, vinculo e limite (so responsavel) e transicao."""
    hoje = data_escolar(p.agora, p.fuso)
    if p.data_solicitada is not None:
        validar_data_alvo(p.data_solicitada, hoje=hoje)

    if p.perfil is Perfil.RESPONSAVEL:
        if p.vinculo is None or not p.vinculo.vigente_em(p.agora):
            raise VinculoInvalido("Nao ha vinculo vigente com o aluno.")
        if not dentro_do_limite(p.agora, p.fuso, p.turno):
            raise ForaDoHorarioLimite("Horario-limite do turno ultrapassado.")

    decisao = decidir_transicao(p.estado_atual, p.acao, p.perfil, p.motivo)
    return ResultadoAvaliacao(data_alvo=hoje, decisao=decisao)