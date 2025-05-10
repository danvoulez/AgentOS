import pytest
import asyncio
from app.models import LogEvent

@pytest.mark.asyncio
async def test_websocket_receives_broadcast_after_action(test_app_instance, db_session, get_test_user_token):
    staff_token = await get_test_user_token(db_session, email="ws_action_user@example.com", roles=["staff"])
    async with test_app_instance.websocket_connect(f"/ws/updates?token={staff_token}") as websocket:
        # Simule criação de log
        from app.models import RegistrarVendaData, ItemVendaData, LogEvent
        venda = RegistrarVendaData(order_id="ord_ws", customer_id="cust", items=[ItemVendaData(product_id="prod", quantity=1, price_per_unit_str="1.00")], total_amount_str="1.00", channel="ws", status="confirmed")
        log_event = LogEvent(type="registrar_venda", author="ws_action_user@example.com", witness="test", data=venda.model_dump())
        # Insira diretamente (em um teste real, use o endpoint)
        db = db_session
        await db["logs"].insert_one(log_event.model_dump())
        import asyncio
        await asyncio.sleep(0.2)
        # Espera receber broadcast do evento
        msg = await websocket.receive_json()
        assert msg["type"] == "new_log_event_v2"
        payload = msg["payload"]
        assert payload["type"] == "registrar_venda"