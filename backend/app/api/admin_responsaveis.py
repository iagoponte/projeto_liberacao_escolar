
from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import errors
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import exigir_admin, get_db
from app.core.seguranca import hash_senha
from app.domain.estados import Perfil
from app.models import Responsavel, Usuario
from app.schemas.responsaveis_admin import (
    ResponsavelAdminResposta,
    ResponsavelCriar,
)


router = APIRouter(
    prefix="/admin/responsaveis",
    tags=["Administracao - Responsaveis"],
    dependencies=[Depends(exigir_admin)],
)


def montar_resposta(
    responsavel: Responsavel,
    usuario: Usuario,
) -> ResponsavelAdminResposta:
    return ResponsavelAdminResposta(
        id=responsavel.id,
        usuario_id=usuario.id,
        nome_completo=responsavel.nome_completo,
        email=usuario.email,
        ativo=responsavel.ativo,
        usuario_ativo=usuario.ativo,
    )


@router.get(
    "",
    response_model=list[ResponsavelAdminResposta],
)
def listar_responsaveis(
    db: Session = Depends(get_db),
):
    consulta = (
        select(Responsavel, Usuario)
        .join(Usuario, Usuario.id == Responsavel.usuario_id)
        .order_by(Responsavel.nome_completo, Responsavel.id)
    )

    registros = db.execute(consulta).all()

    return [
        montar_resposta(responsavel, usuario)
        for responsavel, usuario in registros
    ]


@router.post(
    "",
    response_model=ResponsavelAdminResposta,
    status_code=status.HTTP_201_CREATED,
)
def criar_responsavel(
    dados: ResponsavelCriar,
    db: Session = Depends(get_db),
):
    email = str(dados.email).strip().lower()

    existente = db.scalar(
        select(Usuario.id).where(
            func.lower(Usuario.email) == email
        )
    )

    if existente is not None:
        raise HTTPException(
            status_code=409,
            detail="E-mail ja cadastrado.",
        )

    usuario = Usuario(
        email=email,
        senha_hash=hash_senha(dados.senha),
        perfil=Perfil.RESPONSAVEL,
        ativo=True,
    )

    try:
        db.add(usuario)
        db.flush()

        responsavel = Responsavel(
            usuario_id=usuario.id,
            nome_completo=dados.nome_completo,
            ativo=True,
        )

        db.add(responsavel)
        db.flush()

        resposta = montar_resposta(responsavel, usuario)

        db.commit()
        return resposta

    except IntegrityError as exc:
        db.rollback()

        # A restricao UNIQUE do banco protege contra
        # cadastros simultaneos com o mesmo e-mail.
        if isinstance(exc.orig, errors.UniqueViolation):
            raise HTTPException(
                status_code=409,
                detail="Cadastro duplicado.",
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise
