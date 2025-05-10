import pytest
import asyncio
from httpx import AsyncClient
from app.models import ActionResponseAPI, LogEvent
from starlette.websockets import WebSocketDisconnect

@pytest.mark.asyncio
async def test_action_registrar_venda_success_with_ws(test_app_instance, db_session, get_test_user_token):
    # Setup: create a user and get token
    admin_token = await get_test_user_token(db_session, email="ws_staff@example.com", roles=["staff"])
    admin_client = AsyncClient(app=test_app_instance, base_url="http://testserver", headers={"Authorization": f"Bearer {admin_token}"})
    sale_payload = {
        "customer_id": "test_cust",
        "items": [
            {"product_id": "prod_1", "quantity": 2, "price_per_unit_str": "10.00", "name": "Produto 1"}
        ],
        "channel": "test_ws",
        "notes": "Venda via WS test",
        "client_order_ref": "order_ws1"
    }
    async with test_app_instance.websocket_connect(f"/ws/updates?token={admin_token}") as websocket:
        response = await admin_client.post("/api/v1/actions/registrar_venda", json=sale_payload)
        assert response.status_code == 200
        action_data = ActionResponseAPI(**response.json())
        created_log_id = action_data.log_id

        try:
            ws_message_json = await asyncio.wait_for(websocket.receive_json(), timeout=2.0)
        except asyncio.TimeoutError:
            pytest.fail("WebSocket message not received within timeout.")

        assert ws_message_json["type"] == "new_log_event_v2"
        ws_log_event_payload = LogEvent(**ws_message_json["payload"])
        assert ws_log_event_payload.id == created_log_id
        assert ws_log_event_payload.type == "registrar_venda"
        assert ws_log_event_payload.data["customer_id"] == "test_cust"