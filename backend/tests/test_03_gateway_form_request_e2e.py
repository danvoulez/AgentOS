import pytest
import uuid
from unittest.mock import AsyncMock, patch
from app.models import LLMFormSchema, LLMFormSchemaField, RegistrarVendaData, ItemVendaData, GatewayResponseAPI, LLMInterpretationResponse, ActionResponseAPI, LogEvent
from app.services.state_updater import CS_ORDERS_COLLECTION, CS_INVENTORY_COLLECTION
from httpx import AsyncClient
import asyncio

@pytest.mark.asyncio
@patch("app.routes.gateway.validate_via_opa", AsyncMock(return_value=True))
@patch("app.services.llm_service.LLMService.interpret_request", new_callable=AsyncMock)
async def test_workflow_gateway_form_request_to_log(
    mock_interpret_request: AsyncMock,
    authenticated_client: AsyncClient,
    db_session,
):
    form_id_from_llm = f"form_sale_{uuid.uuid4().hex[:4]}"
    llm_form_schema = LLMFormSchema(
        form_id=form_id_from_llm, title="Detalhes da Venda",
        fields=[
            LLMFormSchemaField(name="customer_id", type="string", label="ID do Cliente", required=False),
            LLMFormSchemaField(name="product_ids_and_qtys", type="text_area", label="Produtos e Quantidades (ex: prod_a:2, prod_b:1)", required=True)
        ]
    )
    llm_response_1_dict = {
        "intent": "clarify_sale_details", "response_type": "form_request",
        "response_payload": {"schema": llm_form_schema.model_dump()}, "conversation_id": "conv_form_test_1"
    }
    mock_interpret_request.return_value = LLMInterpretationResponse(**llm_response_1_dict)

    response1 = await authenticated_client.post(
        "/api/v1/gateway/process",
        json={"text": "Quero fazer uma venda.", "source": "test_form_flow"}
    )
    assert response1.status_code == 200
    data1 = GatewayResponseAPI(**response1.json())
    assert data1.response_type == "form_request"
    assert data1.payload["schema"]["form_id"] == form_id_from_llm
    current_conversation_id = data1.conversation_id

    # --- Segunda chamada: preencher formulário e enviar ---
    form_data_submitted = {"customer_id": "cust_form_123", "product_ids_and_qtys": "prod_alpha:3:10.00, prod_beta:1:25.50"}
    generated_order_id_llm = f"ord_llm_{uuid.uuid4().hex[:8]}"
    sale_entities_from_llm = RegistrarVendaData(
        order_id=generated_order_id_llm, customer_id="cust_form_123",
        items=[
            ItemVendaData(product_id="prod_alpha", quantity=3, price_per_unit_str="10.00", name="Produto Alpha Form"),
            ItemVendaData(product_id="prod_beta", quantity=1, price_per_unit_str="25.50", name="Produto Beta Form"),
        ],
        total_amount_str="55.50",
        channel="form_submission_channel", status="confirmed"
    ).model_dump()
    llm_response_2_dict = {
        "intent": "registrar_venda", "entities": sale_entities_from_llm,
        "response_type": "operational_action_proposed",
        "response_payload": {"message": f"Venda {generated_order_id_llm} proposta a partir do formulário."},
        "conversation_id": current_conversation_id
    }
    mock_interpret_request.return_value = LLMInterpretationResponse(**llm_response_2_dict)

    with patch("app.services.log_service.ws_manager.broadcast", new_callable=AsyncMock) as mock_ws_broadcast_final:
        response2 = await authenticated_client.post(
            "/api/v1/gateway/process",
            json={
                "text": f"Formulário '{llm_form_schema.title}' submetido.",
                "source": "test_form_submission",
                "context": {
                    "conversation_id": current_conversation_id,
                    "form_submission": {"form_id": form_id_from_llm, "data": form_data_submitted}
                }
            }
        )
        assert response2.status_code == 200
        data2 = GatewayResponseAPI(**response2.json())
        created_log_id = data2.log_id
        await asyncio.sleep(0.1)
        mock_ws_broadcast_final.assert_called_once()
        ws_msg = mock_ws_broadcast_final.call_args[0][0]
        assert ws_msg["type"] == "new_log_event_v2"
        assert ws_msg["payload"]["id"] == created_log_id
        assert ws_msg["payload"]["type"] == "registrar_venda"
    # DB checks
    log_doc = await db_session["logs"].find_one({"id": created_log_id})
    assert log_doc is not None
    assert log_doc["type"] == "registrar_venda"
    assert log_doc["data"]["order_id"] == generated_order_id_llm
    assert "_raw_user_input_payload" in log_doc["data"]
    order_state = await db_session[CS_ORDERS_COLLECTION].find_one({"_id": generated_order_id_llm})
    assert order_state is not None
    assert order_state["total_amount_str"] == "55.50"
    inv_alpha = await db_session[CS_INVENTORY_COLLECTION].find_one({"_id": "prod_alpha"})
    assert inv_alpha["current_stock"] == -3