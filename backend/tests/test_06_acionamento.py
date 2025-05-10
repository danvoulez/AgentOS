import uuid
from datetime import datetime
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import RegistrarVendaData, ItemVendaData, AcionarLogEventActionAPIPayload, LogAcionadoData, CurrentStateOrderStatus, LogAcionamentoInfo
from app.services.state_updater import CS_ORDERS_COLLECTION

async def create_log_event_in_db(db, **kwargs):
    # Simula criação de LogEvent no banco
    doc = dict(id=kwargs.get("id") or f"evt_{uuid.uuid4().hex[:12]}", timestamp=datetime.now(), **kwargs)
    await db["logs"].insert_one(doc)
    return type("Obj", (), doc)

async def test_workflow_acionar_log_negar_fato_em_venda(
    admin_client: AsyncClient,
    db_session: AsyncIOMotorDatabase
):
    author_venda = "user_vendedor@example.com"
    order_id_original = f"ord_acionar_{uuid.uuid4().hex[:8]}"
    venda_data = RegistrarVendaData(
        order_id=order_id_original, customer_id="cust_acionar",
        items=[ItemVendaData(product_id="prod_test", quantity=1, price_per_unit_str="100.00")],
        total_amount_str="100.00", channel="test", status="confirmed"
    )
    log_venda = await create_log_event_in_db(db_session, type="registrar_venda", author=author_venda, witness="test", data=venda_data.model_dump())

    order_state_original = CurrentStateOrderStatus(
        id=order_id_original, order_ref=f"SALE-{order_id_original}", customer_id="cust_acionar", status="confirmed",
        total_amount_str="100.00", item_count=1, created_at=log_venda.timestamp,
        last_log_event_id=log_venda.id, last_updated_at=log_venda.timestamp
    )
    await db_session[CS_ORDERS_COLLECTION].insert_one(order_state_original.model_dump(by_alias=True))

    acionar_payload = AcionarLogEventActionAPIPayload(
        target_log_id=log_venda.id,
        acionamento_type="negar_fato",
        motivo="Cliente alega que a venda não ocorreu ou foi cancelada verbalmente no ato.",
        dados_adicionais={"referencia_cliente": "Protocolo XYZ789"}
    )
    response = await admin_client.post(
        "/api/v1/actions/acionar_log",
        json=acionar_payload.model_dump()
    )
    assert response.status_code == 200
    data_resp_acionar = response.json()
    log_acionado_event_id = data_resp_acionar["log_id"]
    assert log_acionado_event_id.startswith("evt_")

    log_acionado_doc = await db_session["logs"].find_one({"id": log_acionado_event_id})
    assert log_acionado_doc is not None
    assert log_acionado_doc["type"] == "log_acionado"
    assert "author" in log_acionado_doc

    log_acionado_data = LogAcionadoData(**log_acionado_doc["data"])
    assert log_acionado_data.target_log_id == log_venda.id
    assert log_acionado_data.acionamento_type == "negar_fato"
    assert "Cliente alega" in log_acionado_data.motivo
    assert log_acionado_data.dados_adicionais["referencia_cliente"] == "Protocolo XYZ789"

    order_state_updated_doc = await db_session[CS_ORDERS_COLLECTION].find_one({"_id": order_id_original})
    assert order_state_updated_doc is not None
    order_state_updated = CurrentStateOrderStatus(**order_state_updated_doc)
    assert len(order_state_updated.acionamentos) == 1
    acionamento_registrado: LogAcionamentoInfo = order_state_updated.acionamentos[0]
    assert acionamento_registrado.log_acionado_event_id == log_acionado_event_id
    assert acionamento_registrado.acionamento_type == "negar_fato"
    assert "Cliente alega" in acionamento_registrado.motivo
    assert order_state_updated.meta["last_acionamento_status"]["negar_fato"] == "pendente"
    assert order_state_updated.meta["has_pending_acionamentos"] is True
    assert order_state_updated.last_log_event_id == log_acionado_event_id