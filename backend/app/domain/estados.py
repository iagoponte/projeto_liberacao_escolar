from dataclasses import dataclass
from enum import StrEnum

from app.domain.erros import MotivoObrigatorio, TransicaoInvalida


class Estado(StrEnum):
    LIBERADO = "LIBERADO"
    CANCELADO = "CANCELADO"


class Acao(StrEnum):
    LIBERAR = "LIBERAR"
    CANCELAR = "CANCELAR"


class Perfil(StrEnum):
    RESPONSAVEL = "RESPONSAVEL"
    ADMIN = "ADMIN"


class TipoAcao(StrEnum):
    LIBERACAO = "LIBERACAO"
    CANCELAMENTO = "CANCELAMENTO"
    CORRECAO_ADMIN = "CORRECAO_ADMIN"


@dataclass(frozen=True)
class Mudanca:
    estado_anterior: Estado | None
    novo_estado: Estado
    tipo_acao: TipoAcao


@dataclass(frozen=True)
class Redundante:
    """Nenhuma mudanca real de estado: nao gera evento de historico."""

    estado: Estado


_DESTINO = {Acao.LIBERAR: Estado.LIBERADO, Acao.CANCELAR: Estado.CANCELADO}
_TIPO_RESPONSAVEL = {Acao.LIBERAR: TipoAcao.LIBERACAO, Acao.CANCELAR: TipoAcao.CANCELAMENTO}


def decidir_transicao(
    atual: Estado | None, acao: Acao, perfil: Perfil, motivo: str | None = None
) -> Mudanca | Redundante:
    if perfil is Perfil.ADMIN and not (motivo and motivo.strip()):
        raise MotivoObrigatorio("Correcao administrativa exige motivo.")

    destino = _DESTINO[acao]
    if atual is destino:
        return Redundante(estado=atual)

    if perfil is Perfil.RESPONSAVEL:
        if atual is None and acao is Acao.CANCELAR:
            raise TransicaoInvalida("Nao ha liberacao registrada para cancelar.")
        tipo = _TIPO_RESPONSAVEL[acao]
    else:
        tipo = TipoAcao.CORRECAO_ADMIN

    return Mudanca(estado_anterior=atual, novo_estado=destino, tipo_acao=tipo)