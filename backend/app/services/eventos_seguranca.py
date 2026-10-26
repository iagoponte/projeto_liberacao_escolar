"""Registro de eventos de seguranca na tabela `auditoria` (append-only)."""
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.estados import Perfil
from app.models import Auditoria


def registrar_evento(
    db: Session,
    agora: datetime,
    tipo: str,
    *,
    usuario_id: int | None = None,
    perfil: Perfil | None = None,
    entidade: str = "usuarios",
    entidade_id: int | None = None,
    detalhes: dict[str, Any] | None = None,
) -> Auditoria:
    """Adiciona o evento a sessao; quem chama decide o commit.

    Nunca inclua senhas, tokens ou e-mails em claro em `detalhes`.
    """
    evento = Auditoria(
        ocorrido_em=agora,
        usuario_id=usuario_id,
        perfil=perfil,
        tipo_evento=tipo,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
    )
    db.add(evento)
    return evento