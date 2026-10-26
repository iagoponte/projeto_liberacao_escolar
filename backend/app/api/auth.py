from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import (
    COOKIE_SESSAO,
    Autenticado,
    autenticado,
    get_db,
    get_relogio,
    ip_do_cliente,
)
from app.core.config import Settings, get_settings
from app.core.seguranca import token_csrf
from app.domain.relogio import Relogio
from app.schemas.auth import LoginIn, SessaoOut, UsuarioOut
from app.services.autenticacao import (
    Autenticacao,
    CredenciaisInvalidas,
    LoginBloqueado,
    encerrar_sessao,
    tentar_login,
)

router = APIRouter(prefix="/auth", tags=["autenticacao"])


@router.post("/login", response_model=SessaoOut)
def login(
    dados: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    relogio: Relogio = Depends(get_relogio),
) -> SessaoOut:
    try:
        realizado = tentar_login(
            db, settings, relogio, dados.email, dados.senha, ip_do_cliente(request)
        )
    except LoginBloqueado as exc:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except CredenciaisInvalidas as exc:
        raise HTTPException(status_code=401, detail="Credenciais invalidas.") from exc

    response.set_cookie(
        key=COOKIE_SESSAO,
        value=realizado.token,
        max_age=settings.session_absolute_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return SessaoOut(
        usuario=UsuarioOut.model_validate(realizado.usuario),
        csrf_token=token_csrf(settings.secret_key, realizado.token),
    )


@router.get("/me", response_model=SessaoOut)
def me(
    auth: Autenticado = Depends(autenticado),
    settings: Settings = Depends(get_settings),
) -> SessaoOut:
    return SessaoOut(
        usuario=UsuarioOut.model_validate(auth.usuario),
        csrf_token=token_csrf(settings.secret_key, auth.token),
    )


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    auth: Autenticado = Depends(autenticado),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    relogio: Relogio = Depends(get_relogio),
) -> None:
    encerrar_sessao(db, relogio, Autenticacao(usuario=auth.usuario, sessao=auth.sessao))
    response.delete_cookie(
        key=COOKIE_SESSAO,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )