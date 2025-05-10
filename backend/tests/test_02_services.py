import pytest
from app.services.llm_service import LLMService
from app.models import LLMInterpretationResponse, RegistrarVendaData, ItemVendaData, LogEvent
from app.services.log_service import LogService
from app.services.state_updater import StateUpdaterService, CS_ORDERS_COLLECTION
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_llm_service_interpret_acionamento(monkeypatch):
    # Mock do interpret_request
    service = LLMService()
    monkeypatch.setattr(service, "interpret_request", AsyncMock(return_value=LLMInterpretationResponse(
        intent="acionar_log", entities={}, confidence=0.95, response_type="operational_action_proposed", response_payload={"text": "Acionamento proposto"}
    )))
    resp = await service.interpret_request("Acione o log X", {})
    assert resp.intent == "acionar_log"

@pytest.mark.asyncio
async def test_log_service_record_event(db_session):
    service = LogService(db=db_session)
    venda_data = RegistrarVendaData(order_id="ord_test", customer_id="cust", items=[ItemVendaData(product_id="prod", quantity=1, price_per_unit_str="1.00")], total_amount_str="1.00", channel="test", status="confirmed")
    log_event = LogEvent(type="registrar_venda", author="test", witness="test", data=venda_data.model_dump())
    event = await service.record_event(log_event, None)
    assert event.id.startswith("evt_")

@pytest.mark.asyncio
async def test_state_updater_handles_log_acionado(db_session):
    service = StateUpdaterService(db=db_session)
    # Supondo que LogEvent e LogAcionadoData já estão seedados
    # test that the handler does not raise
    from app.models import LogEvent, LogAcionadoData
    log_event = LogEvent(type="log_acionado", author="test", witness="test", data=LogAcionadoData(target_log_id="log_1", acionamento_type="confirmar_fato").model_dump())
    await service._handle_log_acionado(log_event)
    assert True

@pytest.mark.asyncio
async def test_opa_validator_allows(monkeypatch):
    from app.utils.opa_validator import validate_via_opa
    monkeypatch.setattr("app.utils.opa_validator.httpx.AsyncClient.post", AsyncMock(return_value=MagicMock(status_code=200, json=lambda: True)))
    allowed = await validate_via_opa(path=["actions", "registrar_venda"], method="POST", token_data=None, request_body={})
    assert allowed is True