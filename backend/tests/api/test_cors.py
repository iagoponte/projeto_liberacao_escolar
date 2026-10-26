
from fastapi.testclient import TestClient

from app.main import app


def test_cors_permite_frontend_local_com_credenciais():
    with TestClient(app) as client:
        resposta = client.options(
            "/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert resposta.status_code == 200

    assert (
        resposta.headers["access-control-allow-origin"]
        == "http://localhost:3000"
    )

    assert (
        resposta.headers["access-control-allow-credentials"]
        == "true"
    )


def test_cors_nao_autoriza_origem_desconhecida():
    with TestClient(app) as client:
        resposta = client.options(
            "/auth/login",
            headers={
                "Origin": "http://site-nao-autorizado.test",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert resposta.status_code == 400

    assert (
        resposta.headers.get("access-control-allow-origin")
        != "http://site-nao-autorizado.test"
    )
