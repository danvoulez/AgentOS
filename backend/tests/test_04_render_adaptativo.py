import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_admin_test_render_data_endpoint(admin_client: AsyncClient):
    # Test key-value rendering
    payload = {
        "data_content": {"chave1": "valor1", "chave2": "valor2"},
        "display_meta": {"title": "Teste KeyValue"}
    }
    resp = await admin_client.post("/api/v1/admin/test_render_data", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_type"] == "structured_data_response"
    assert "data" in data["payload"]
    # Test DataTable rendering
    payload = {
        "data_content": [{"col1": "a", "col2": 1}, {"col1": "b", "col2": 2}],
        "display_meta": {"title": "Teste Tabela"}
    }
    resp = await admin_client.post("/api/v1/admin/test_render_data", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["response_type"] == "structured_data_response"
    assert isinstance(data["payload"]["data"], list)