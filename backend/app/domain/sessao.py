"""Regras puras de sessao: revogacao, expiracao absoluta e por inatividade."""
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.relogio import exigir_instante_com_fuso

INTERVALO_RENOVACAO = timedelta(seconds=60)


class MotivoSessaoInvalida(StrEnum):
    REVOGADA = "REVOGADA"
    EXPIRADA_ABSOLUTA = "EXPIRADA_ABSOLUTA"
    EXPIRADA_INATIVIDADE = "EXPIRADA_INATIVIDADE"


def calcular_expiracao(agora: datetime, minutos: int) -> datetime:
    return exigir_instante_com_fuso(agora) + timedelta(minutes=minutos)


def avaliar_sessao(
    *,
    agora: datetime,
    expira_em: datetime,
    ultimo_acesso_em: datetime,
    revogada_em: datetime | None,
    inatividade_maxima: timedelta,
) -> MotivoSessaoInvalida | None:
    """None se a sessao e valida. Limites EXCLUSIVOS: no instante exato ela ja expirou."""
    exigir_instante_com_fuso(agora)
    exigir_instante_com_fuso(expira_em)
    exigir_instante_com_fuso(ultimo_acesso_em)
    if revogada_em is not None:
        return MotivoSessaoInvalida.REVOGADA
    if agora >= expira_em:
        return MotivoSessaoInvalida.EXPIRADA_ABSOLUTA
    if agora - ultimo_acesso_em >= inatividade_maxima:
        return MotivoSessaoInvalida.EXPIRADA_INATIVIDADE
    return None


def deve_renovar_ultimo_acesso(agora: datetime, ultimo_acesso_em: datetime) -> bool:
    """Evita gravar no banco a cada requisicao: renova no maximo uma vez por minuto."""
    return agora - ultimo_acesso_em >= INTERVALO_RENOVACAO