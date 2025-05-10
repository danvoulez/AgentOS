from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorDatabase
import uuid
from datetime import datetime, timezone
from app.models import LogEventConsequenceDetail, TriggeredConsequenceData

async def create_log_event_in_db(db, **kwargs):
    doc = dict(id=kwargs.get("id") or f"evt_{uuid.uuid4().hex[:12]}", timestamp=datetime.now(timezone.utc), **kwargs)
    await db["logs"].insert_one(doc)
    return type("Obj", (), doc)

async def test_workflow_trigger_consequence_of_log_event(
    admin_client: AsyncClient,
    db_session: AsyncIOMotorDatabase,
):
    original_log_id = f"evt_orig_with_conseq_{uuid.uuid4().hex[:10]}"
    consequence_type_to_trigger = "gerar_relatorio_mensal_exemplo"
    original_log_consequence = LogEventConsequenceDetail(
        type=consequence_type_to_trigger,
        status="awaiting_trigger"
    )
    await create_log_event_in_db(
        db_session, id=original_log_id, type="solicitacao_relatorio",
        author="user_solicitante", witness="sistema",
        data={"tipo_relatorio": "mensal", "mes_ano": "05/2024"},
        consequence=original_log_consequence.model_dump()
    )

    trigger_payload = {"target_log_id": original_log_id, "trigger_notes": "Acionamento manual do relatório mensal conforme solicitado."}
    response = await admin_client.post(
        "/api/v1/actions/trigger_consequence",
        json=trigger_payload
    )
    assert response.status_code == 200
    action_resp_data = response.json()
    trigger_log_id = action_resp_data["log_id"]

    triggered_consequence_log_doc = await db_session["logs"].find_one({"id": trigger_log_id})
    assert triggered_consequence_log_doc is not None
    assert triggered_consequence_log_doc["type"] == "triggered_consequence"
    triggered_data = TriggeredConsequenceData(**triggered_consequence_log_doc["data"])
    assert triggered_data.target_log_id == original_log_id
    assert triggered_data.target_consequence_type == consequence_type_to_trigger

    updated_original_log_doc = await db_session["logs"].find_one({"id": original_log_id})
    assert updated_original_log_doc is not None
    assert updated_original_log_doc["consequence"]["status"] == "triggered"
    assert updated_original_log_doc["consequence"]["triggered_by_log_event_id"] == trigger_log_id