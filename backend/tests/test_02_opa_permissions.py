import pytest
from app.models import AcionarLogEventActionAPIPayload
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_acionar_log_permission_granted_for_admin(admin_client: AsyncClient, db_session):
    from tests.utils import create_log_event_in_db
    log_original = await create_log_event_in_db(db_session, type="entrada_estoque", author="system", witness="test")
    acionar_payload = AcionarLogEventActionAPIPayload(
        target_log_id=log_original.id,
        acionamento_type="propor_ajuste",
        motivo="Estoque parece errado."
    )
    response = await admin_client.post("/api/v1/actions/acionar_log", json=acionar_payload.model_dump())
    assert response.status_code == 200
    assert response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_acionar_log_permission_denied_for_customer(customer_client: AsyncClient, db_session):
    from tests.utils import create_log_event_in_db
    log_original = await create_log_event_in_db(db_session, type="entrada_estoque", author="system", witness="test")
    acionar_payload = AcionarLogEventActionAPIPayload(
        target_log_id=log_original.id,
        acionamento_type="propor_ajuste",
        motivo="Estoque parece errado."
    )
    response = await customer_client.post("/api/v1/actions/acionar_log", json=acionar_payload.model_dump())
    assert response.status_code == 403
    assert "Role" in response.json()["detail"] or "not authorized" in response.text.lower()