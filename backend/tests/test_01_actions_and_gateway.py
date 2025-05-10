import pytest
from httpx import AsyncClient
from app.models import AcionarLogEventActionAPIPayload, ActionResponseAPI, LogEvent

@pytest.mark.asyncio
async def test_action_registrar_venda_success_with_ws(test_app_instance, db_session, get_test_user_token):
    admin_token = await get_test_user_token(db_session, email="ws_staff@example.com", roles=["staff"])
    admin_client = AsyncClient(app=test_app_instance, base_url="http://testserver", headers={"Authorization": f"Bearer {admin_token}"})
    sale_payload = {
        "customer_id": "test_cust",
        "items": [{"product_id": "prod_1", "quantity": 2, "price_per_unit_str": "10.00", "name": "Produto 1"}],
        "channel": "test_ws",
        "notes": "Venda via WS test",
        "client_order_ref": "order_ws1"
    }
    async with test_app_instance.websocket_connect(f"/ws/updates?token={admin_token}") as websocket:
        response = await admin_client.post("/api/v1/actions/registrar_venda", json=sale_payload)
        assert response.status_code == 200
        action_data = ActionResponseAPI(**response.json())
        created_log_id = action_data.log_id
        import asyncio
        try:
            ws_message_json = await asyncio.wait_for(websocket.receive_json(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("WebSocket message not received within timeout.")
        assert ws_message_json["type"] == "new_log_event_v2"
        ws_log_event_payload = LogEvent(**ws_message_json["payload"])
        assert ws_log_event_payload.id == created_log_id
        assert ws_log_event_payload.type == "registrar_venda"

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