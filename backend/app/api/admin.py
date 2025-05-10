import logging
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Any, Dict, List, Optional, Type

from app.config import settings
from app.utils.auth import require_role, TokenData, get_token_data_from_header
from app.utils.opa_validator import validate_via_opa
from app.services.log_service import LogService, get_log_service
from app.core.database import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models import (
    LogEvent, ActionResponseAPI,
    RegistrarVendaData, RelatoQuebraData, UpdateOrderStatusData, EntradaEstoqueData,
    DespachoCreatedData, DespachoResolvedData, WhatsAppMensagemRecebidaData, ValidarPrelogData
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin Tools"], dependencies=[Depends(require_role(["admin", "developer"]))])

_LOG_EVENT_DATA_MODELS: Dict[str, Type[BaseModel]] = {
    "registrar_venda": RegistrarVendaData,
    "relato_quebra": RelatoQuebraData,
    "update_order_status": UpdateOrderStatusData,
    "entrada_estoque": EntradaEstoqueData,
    "despacho_created": DespachoCreatedData,
    "despacho_resolved": DespachoResolvedData,
    "whatsapp_mensagem_recebida": WhatsAppMensagemRecebidaData,
    "approve_prelog": ValidarPrelogData,
    "reject_prelog": ValidarPrelogData,
}


class LogEventEditorPayload(BaseModel):
    id: Optional[str] = Field(None, description="Optional: ID for the event. If not provided, backend generates one.")
    timestamp: Optional[datetime] = Field(None, description="Optional: UTC Timestamp. If not provided, backend uses current time.")
    type: str = Field(..., description="LogEvent type (e.g., 'registrar_venda', 'despacho_created').")
    author: str = Field(..., description="Author of the event (e.g., 'user:admin_id', 'system:manual_override').")
    witness: str = Field(..., description="Witness of the event (e.g., 'admin:ui', 'system:force_log').")
    channel: Optional[str] = Field("admin_ui", description="Channel where the event originated.")
    origin: Optional[str] = Field("LogEventEditor", description="Specific origin within the channel.")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event-specific data payload. Must match *Data model for 'type'.")
    consequence: Optional[Dict[str, Any]] = Field(None, description="Consequence data.")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata (e.g., trace_id, conversation_id).")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        if v and v > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError("Timestamp cannot be significantly in the future.")
        return v

class LogEventValidationResponse(BaseModel):
    is_valid: bool
    message: str
    validated_log_event: Optional[LogEvent] = None
    validation_errors: Optional[List[str]] = None
    suggested_corrections: Optional[Dict[str, Any]] = None

@router.get("/log-event-schema", summary="Get JSON Schema for LogEvent and *Data models for dynamic form rendering.")
async def get_log_event_schema():
    all_schemas = {
        "LogEvent": LogEvent.model_json_schema(),
        "LogEventDataModels": {
            intent_type: model.model_json_schema() for intent_type, model in _LOG_EVENT_DATA_MODELS.items()
        }
    }
    return all_schemas

@router.post("/validate_log_event_proposal", response_model=LogEventValidationResponse, summary="Validate a LogEvent proposal without persisting it.")
async def validate_log_event_proposal(
    payload: LogEventEditorPayload,
    token_data: TokenData = Depends(get_token_data_from_header),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    validation_errors = []
    is_valid = True
    validated_log_event: Optional[LogEvent] = None

    try:
        draft_id = payload.id or f"evt_draft_{uuid.uuid4().hex[:12]}"
        draft_timestamp = payload.timestamp or datetime.now(timezone.utc)
        log_event_draft = LogEvent(
            id=draft_id, timestamp=draft_timestamp,
            type=payload.type, author=payload.author, witness=payload.witness,
            channel=payload.channel, origin=payload.origin,
            data=payload.data, consequence=payload.consequence, meta=payload.meta
        )
        validated_log_event = log_event_draft
    except ValidationError as e:
        is_valid = False
        validation_errors.append(f"Basic LogEvent schema validation failed: {e.errors()}")
        return LogEventValidationResponse(is_valid=is_valid, message="Basic schema validation failed.", validation_errors=validation_errors)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal validation error: {e}")

    specific_data_model = _LOG_EVENT_DATA_MODELS.get(log_event_draft.type)
    if specific_data_model:
        try:
            validated_data_payload = specific_data_model(**log_event_draft.data)
            log_event_draft.data = validated_data_payload.model_dump(exclude_none=True)
        except ValidationError as e:
            is_valid = False
            validation_errors.append(f"LogEvent.data validation against {specific_data_model.__name__} failed: {e.errors()}")

    try:
        await validate_via_opa(
            path=["admin", "log_event_proposal"],
            method="PROPOSE",
            token_data=token_data,
            request_body=log_event_draft.model_dump()
        )
    except HTTPException as e:
        is_valid = False
        validation_errors.append(f"OPA policy denied proposal: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal OPA validation error: {e}")

    if not is_valid:
        return LogEventValidationResponse(
            is_valid=False,
            message="LogEvent proposal validation failed.",
            validation_errors=validation_errors,
            validated_log_event=validated_log_event
        )
    else:
        return LogEventValidationResponse(
            is_valid=True,
            message="LogEvent proposal is valid.",
            validated_log_event=validated_log_event
        )

@router.post("/force_log_event", response_model=ActionResponseAPI, summary="Persist a LogEvent directly, bypassing normal entry points (Admin only).")
async def force_log_event(
    payload: LogEventEditorPayload,
    background_tasks: BackgroundTasks,
    token_data: TokenData = Depends(get_token_data_from_header),
    log_service: LogService = Depends(get_log_service)
):
    validation_response = await validate_log_event_proposal(payload, token_data, get_database())
    if not validation_response.is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"LogEvent proposal is not valid: {validation_response.validation_errors}")

    log_event_to_persist = validation_response.validated_log_event

    try:
        await validate_via_opa(
            path=["admin", "force_log_event"],
            method="FORCE",
            token_data=token_data,
            request_body=log_event_to_persist.model_dump()
        )
    except HTTPException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to force this log event: {e.detail}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal OPA authorization error: {e}")

    try:
        persisted_event = await log_service.record_event(log_event_to_persist, background_tasks)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Core system error forcing log: {e}")

    return ActionResponseAPI(
        status="success",
        message=f"LogEvent '{persisted_event.id}' of type '{persisted_event.type}' forced successfully.",
        log_id=persisted_event.id,
        data={"forced_log_event_id": persisted_event.id, "log_event_type": persisted_event.type}
    )