import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"

@pytest.mark.asyncio
async def test_token_brute_force_limit(client: AsyncClient):
    # Exemplo: tentar muitas requisições e verificar headers de rate-limit
    for _ in range(6):
        res = await client.post("/api/v1/auth/token", data={"username": "fake", "password": "fake"})
    assert res.status_code in (429, 401)
    assert "X-RateLimit-Limit" in res.headers or "Retry-After" in res.headers

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, db_session, get_test_user_token):
    # Gera um refresh_token válido (assume implementação no backend)
    user_token, refresh_token = await get_test_user_token(db_session, return_refresh=True)
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"