"""E1 - a API sobe e responde ao health check sem exigir autenticacao nem banco."""


def test_health_retorna_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_rota_inexistente_retorna_404(client):
    assert client.get("/nao-existe").status_code == 404
