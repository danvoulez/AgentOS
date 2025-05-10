import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_query_inventory_endpoint(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/v1/query/inventory?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_query_timeline_endpoint(authenticated_client: AsyncClient):
    resp = await authenticated_client.get("/api/v1/timeline?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data