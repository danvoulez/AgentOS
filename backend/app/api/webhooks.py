import logging
import hashlib
import hmac
import json
import uuid

from fastapi import APIRouter, Depends, Request, HTTPException, status, BackgroundTasks, Query
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.config import settings
from app.services.log_service import LogService, get_log_service
from app.models import LogEvent, WhatsAppMensagemRecebidaData

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    request: Request,
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    log = logger.bind(trace_id=logger.extra.get("trace_id"))
    log.info(f"GET /webhooks/whatsapp verification request received. Mode: {hub_mode}, Token: {hub_verify_token}")
    EXPECTED_VERIFY_TOKEN = getattr(settings, "WHATSAPP_VERIFY_TOKEN", "your_webhook_verify_token_here")
    if hub_mode == "subscribe" and hub_verify_token == EXPECTED_VERIFY_TOKEN:
        log.success("WhatsApp webhook verification successful.")
        return int(hub_challenge)
    else:
        log.error("WhatsApp webhook verification failed. Mode or token mismatch.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Webhook verification failed.")

async def verify_whatsapp_signature(request: Request, app_secret: str) -> bool:
    signature_header = request.headers.get("X-Hub-Signature-256")
    if not signature_header:
        logger.warning("Missing X-Hub-Signature-256 header from WhatsApp webhook.")
        return False
    try:
        hash_method, received_hash = signature_header.split("=", 1)
        if hash_method != "sha256":
            logger.warning(f"Unsupported hash method in signature: {hash_method}")
            return False
    except ValueError:
        logger.warning(f"Malformed X-Hub-Signature-256 header: {signature_header}")
        return False
    raw_body = await request.body()
    expected_hash = hmac.new(
        app_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    if hmac.compare_digest(expected_hash, received_hash):
        logger.debug("WhatsApp webhook signature verified successfully.")
        return True
    else:
        logger.error(f"WhatsApp webhook signature mismatch. Expected: {expected_hash}, Received: {received_hash}")
        return False

@router.post("/whatsapp", status_code=status.HTTP_200_OK)
async def receive_whatsapp_message_webhook(
    request: Request,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    log_service: LogService = Depends(get_log_service)
):
    trace_id = logger.extra.get("trace_id", f"wh_{uuid.uuid4().hex[:12]}")
    log = logger.bind(trace_id=trace_id, webhook_source="whatsapp")
    log.info(f"POST /webhooks/whatsapp received payload.")
    log.debug(f"Full WhatsApp Payload: {json.dumps(payload, indent=2)[:1000]}...")

    APP_SECRET = getattr(settings, "WHATSAPP_APP_SECRET", "your_whatsapp_app_secret_here")
    if APP_SECRET == "your_whatsapp_app_secret_here":
        log.critical("CRITICAL SECURITY WARNING: Using default WHATSAPP_APP_SECRET. Webhook is insecure!")
    if not await verify_whatsapp_signature(request, APP_SECRET):
         log.error("Invalid WhatsApp webhook signature. Request rejected.")
         pass

    message_text = None
    sender_wa_id = None
    message_timestamp_from_provider_unix = None

    try:
        if payload.get("object") == "whatsapp_business_account":
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    if "messages" in value:
                        for message_obj in value.get("messages", []):
                            if message_obj.get("type") == "text" and "text" in message_obj:
                                message_text = message_obj["text"]["body"]
                                sender_wa_id = message_obj.get("from")
                                message_timestamp_from_provider_unix = int(message_obj.get("timestamp", 0))
                                break
                        if message_text: break
                if message_text: break
    except Exception as e:
        log.error(f"Error parsing WhatsApp payload structure: {e}", exc_info=True)
        return {"status": "error_parsing_payload"}

    if not message_text or not sender_wa_id:
        log.info("No processable user text message found in WhatsApp payload. Ignoring.")
        return {"status": "no_actionable_message"}

    log.info(f"Extracted WA message from {sender_wa_id}: '{message_text[:100]}...'")
    prelog_event_id = f"evt_prelog_wa_{uuid.uuid4().hex}"
    message_ts_iso = None
    if message_timestamp_from_provider_unix:
        message_ts_iso = datetime.fromtimestamp(message_timestamp_from_provider_unix, tz=timezone.utc).isoformat()

    prelog_event_data_payload = WhatsAppMensagemRecebidaData(
        prelog_id=prelog_event_id,
        sender_wa_id=sender_wa_id,
        message_text=message_text,
        message_timestamp_from_provider=message_ts_iso,
        initial_llm_interpretation=None
    )

    log_event_draft = LogEvent(
        id=prelog_event_id,
        type="whatsapp_mensagem_recebida",
        author=f"whatsapp_user:{sender_wa_id}",
        witness="whatsapp_provider:meta",
        channel="whatsapp",
        origin="webhook_message",
        data=prelog_event_data_payload.model_dump(),
        meta={"trace_id": trace_id}
    )

    async def process_and_log_prelog():
        try:
            await log_service.record_event(log_event_draft, BackgroundTasks(), [])
            log.success(f"WhatsApp pre-log event '{prelog_event_id}' successfully recorded.")
        except Exception as e:
            log.critical(f"Failed to record WhatsApp pre-log event '{prelog_event_id}': {e}", exc_info=True)

    background_tasks.add_task(process_and_log_prelog)
    log.info(f"Task added to background for processing WA message into pre-log: {prelog_event_id}")

    return {"status": "message_received_for_processing"}