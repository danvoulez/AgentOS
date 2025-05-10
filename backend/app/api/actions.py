from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from app.models import (
    AcionarLogInstitucionalActionAPIPayload, LogAcionadoInstitucionalmenteData,
    ActionResponseAPI, LogEvent, TokenData, CurrentUser
)
from app.utils.opa_validator import validate_via_opa
from app.services.log_service import LogService, get_log_service
from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import settings

router = APIRouter()

@router.post(
    "/acionar_log_institucional",
    response_model=ActionResponseAPI,
    dependencies=[Depends(lambda: True)],  # Substitute with require_role([...]) as needed
    summary="Inicia um acionamento institucional sobre um LogEvent existente."
)
async def action_acionar_log_institucional(
    payload: AcionarLogInstitucionalActionAPIPayload,
    background_tasks: BackgroundTasks,
    token_data: TokenData = Depends(),
    current_user: CurrentUser = Depends(),
    log_service: LogService = Depends(get_log_service),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    author_id_acionamento = str(current_user.id)
    intent_type_log_acionado_inst = "log_acionado_institucionalmente"

    # 1. Verificar se o target_log_id existe
    target_log = await db["logs"].find_one({"id": payload.target_log_id})
    if not target_log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log original para acionamento não encontrado.")

    # 2. OPA Validation
    await validate_via_opa(
        path=["actions", "acionar_log_institucional"], method="POST", token_data=token_data,
        request_body=payload.model_dump(),
        extra_context={"target_log_type": target_log.get("type"), "target_log_author": target_log.get("author")}
    )

    # 3. Construir event.data
    event_data_for_log = LogAcionadoInstitucionalmenteData(
        target_log_id=payload.target_log_id,
        acionamento_type=payload.acionamento_type,
        motivo_detalhado=payload.motivo_detalhado,
        evidencias_anexas=payload.evidencias_anexas
    ).model_dump(exclude_none=True)

    # 4. Construir LogEvent Draft
    log_event_draft = LogEvent(
        type=intent_type_log_acionado_inst,
        author=author_id_acionamento,
        witness=f"action_endpoint:{settings.API_V1_STR}/actions/acionar_log_institucional",
        data=event_data_for_log,
        channel="fusion_litigio_panel", origin=f"AcionamentoInstitucional:{payload.acionamento_type}",
        meta={"references_original_log_id": payload.target_log_id}
    )

    # 5. Record Event
    persisted_event = await log_service.record_event(log_event_draft, background_tasks)
    return ActionResponseAPI(
        status="success",
        message=f"Acionamento institucional tipo '{payload.acionamento_type}' para Log '{payload.target_log_id}' registrado. Log do Acionamento: {persisted_event.id}",
        log_id=persisted_event.id,
        data={"target_log_id": payload.target_log_id, "acionamento_type": payload.acionamento_type}
    )