# agentos_core/app/api/endpoints/whatsapp.py

from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query, Path, Header  
from pydantic import ValidationError  
from typing import List, Optional, Dict, Any, Annotated  
from loguru import logger  
import hmac  
import hashlib  
import asyncio  
from datetime import datetime, timezone, date # Adicionar date  
import uuid  
from bson import ObjectId # Para validar IDs recebidos

# Core & Utils  
from app.core.config import settings  
from app.core.logging_config import trace_id_var  
from app.core.security import CurrentUser, UserInDB # Importar UserInDB para tipo do usuário logado

# Services & DB  
from app.websocket.connection_manager import manager as ws_manager  
from app.worker.celery_app import celery_app  
from app.db.mongo_client import get_database, AsyncIOMotorDatabase

# Models  
from app.models.whatsapp import (  
    WhatsAppWebhookPayload, SendMessagePayloadAPI, SendMessageResponseAPI,  
    ChatModePayloadAPI, ChatModeResponseAPI, WhatsAppChatAPI, WhatsAppMessageAPI  
)  
# Importar modelo interno para validação/formatação  
from app.modules.whatsapp.models import WhatsAppMessageInternal, WhatsAppChatInternal # <<< Assumindo que criamos modelos internos

router = APIRouter()

# --- Constantes ---  
WHATSAPP_CHATS_COLLECTION = "whatsapp_chats"  
WHATSAPP_MESSAGES_COLLECTION = "whatsapp_messages"

# --- Dependência de Verificação de Assinatura Meta ---  
async def verify_meta_signature(request: Request, x_hub_signature_256: Annotated[str | None, Header(alias="X-Hub-Signature-256")] = None):  
    """Dependency to verify the X-Hub-Signature-256 header from Meta webhooks."""  
    # (Lógica de verificação como antes - mantida)  
    log = logger.bind(trace_id=trace_id_var.get(), service="WebhookAuth")  
    if not settings.META_APP_SECRET: log.critical("FATAL: META_APP_SECRET missing."); raise HTTPException(500, "Webhook validation misconfigured")  
    if not x_hub_signature_256: log.warning("Webhook missing signature header."); raise HTTPException(400, "Missing signature header")  
    if not x_hub_signature_256.startswith("sha256="): log.warning(f"Invalid signature format."); raise HTTPException(400, "Invalid signature format")  
    expected_hash = x_hub_signature_256.split("=")[1]  
    if not hasattr(request.state, 'raw_body'): request.state.raw_body = await request.body()  
    body = request.state.raw_body  
    hashed = hmac.new(settings.META_APP_SECRET.encode('utf-8'), body, hashlib.sha256).hexdigest()  
    if not hmac.compare_digest(hashed, expected_hash): log.error("Webhook signature failed!"); raise HTTPException(403, "Invalid signature")  
    log.debug("Webhook signature verified.")  
    return True

# --- Helpers de Processamento de Webhook (Refinados) ---  
async def process_incoming_message(message_data: Dict, value_data: Dict, db: AsyncIOMotorDatabase, log: logger):  
    """Processes a single incoming message: Store, Update Chat, Broadcast WS, Schedule Timeout."""  
    # Extrair dados básicos  
    message_type = message_data.get('type')  
    sender_id_wa = message_data.get('from') # User's WA ID (number)  
    message_id_wami = message_data.get('id') # WAMI  
    timestamp_unix = int(message_data.get('timestamp', 0))  
    timestamp_dt = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc) if timestamp_unix else datetime.now(timezone.utc)  
    your_phone_id = value_data.get('metadata', {}).get('phone_number_id')  
    chat_id = sender_id_wa # Usar WA ID do remetente como ID do chat para 1-on-1

    if not sender_id_wa or not message_id_wami:  
        log.error("Webhook message missing critical IDs (sender/WAMI). Skipping.")  
        return

    log = log.bind(chat_id=chat_id, wami=message_id_wami, msg_type=message_type) # Bind IDs ao log  
    log.info(f"Processing incoming WhatsApp message...")

    # Extrair conteúdo e metadados  
    content = f"[{message_type.upper()} Received - Check Metadata]" # Placeholder  
    media_info = None  
    contact_name = value_data.get('contacts', [{}])[0].get('profile', {}).get('name', 'Unknown Contact')  
    is_unsupported_type = False

    if message_type == 'text':  
        content = message_data.get('text', {}).get('body', '')  
    elif message_type in ['image', 'audio', 'video', 'document', 'sticker']:  
        media_info = message_data.get(message_type, {})  
        content = media_info.get('caption', f"[{message_type.upper()} Media]")  
        log.info(f"Received media. Type: {message_type}, MediaID: {media_info.get('id')}")  
    elif message_type == 'location':  
         loc = message_data.get('location', {})  
         content = f"Location: {loc.get('latitude')}, {loc.get('longitude')}"  
         media_info = loc  
    elif message_type == 'contacts':  
         contacts = message_data.get('contacts', [])  
         content = f"[Contact(s) Received: {len(contacts)}]"  
         media_info = contacts  
    elif message_type == 'reaction':  
         reaction = message_data.get('reaction', {})  
         content = f"[Reacted {reaction.get('emoji', '?')} to msg {reaction.get('message_id')}]"  
         media_info = reaction  
    else:  
         log.warning(f"Unhandled message type: {message_type}")  
         is_unsupported_type = True

    # Preparar documento MongoDB (usando modelo interno se definido)  
    message_doc_data = {  
        "_id": message_id_wami, "chat_id": chat_id, "sender_id": sender_id_wa,  
        "recipient_id": your_phone_id, "content": content or "", "type": message_type or "unknown",  
        "timestamp": timestamp_dt, "status": "received",  
        "metadata": {"contact_name": contact_name, "media_info": media_info},  
        "createdAt": datetime.now(timezone.utc), "status_timestamp": None,  
        "official_wami": message_id_wami, # WAMI é o ID oficial aqui  
        "processing_status": None, "internal_flags": []  
    }  
    # Validar com modelo interno (opcional, mas recomendado)  
    # try:  
    #     message_internal = WhatsAppMessageInternal.model_validate(message_doc_data)  
    #     message_doc_to_save = message_internal.model_dump(by_alias=True)  
    # except ValidationError as e:  
    #     log.error(f"Failed to validate incoming message doc: {e}")  
    #     return # Não salvar se inválido?  
    message_doc_to_save = message_doc_data # Salvar dict diretamente por enquanto

    try:  
        # --- Store Message ---  
        await db[WHATSAPP_MESSAGES_COLLECTION].update_one(  
            {"_id": message_id_wami}, {"$set": message_doc_to_save}, upsert=True  
        )  
        log.debug(f"Message upserted in DB.")

        # --- Update Chat ---  
        increment_unread = 1 if message_type not in ['reaction', 'status'] and not is_unsupported_type else 0  
        # Opcional: Não incrementar se a janela de chat estiver aberta no frontend? Requer mais lógica.  
        chat_update_result = await db[WHATSAPP_CHATS_COLLECTION].update_one(  
            {"_id": chat_id},  
            {"$set": { "contact_id": sender_id_wa, "last_message_ts": timestamp_dt, "contact_name": contact_name, "status": "open", "last_interaction_at": datetime.now(timezone.utc) },  
             "$inc": {"unread_count": increment_unread},  
             "$setOnInsert": { "_id": chat_id, "mode": "human", "created_at": datetime.now(timezone.utc)} },  
            upsert=True  
        )  
        log.debug(f"Chat upserted. Matched: {chat_update_result.matched_count}, Mod: {chat_update_result.modified_count}")

        # --- Broadcast via WebSocket ---  
        try:  
             api_message = WhatsAppMessageAPI.model_validate(message_doc_to_save)  
             await ws_manager.broadcast({"type": "new_whatsapp_message", "payload": api_message.model_dump(by_alias=True, exclude_none=True)})  
             log.debug("WS broadcast sent.")  
        except (ValidationError, Exception) as ws_err:  
             log.error(f"Failed to validate/broadcast incoming message via WS: {ws_err}")

        # --- AutoResponder Scheduling/Revocation ---  
        is_customer_message = message_doc_to_save["sender_id"] == chat_id  
        if is_customer_message:  
            chat_doc = await db[WHATSAPP_CHATS_COLLECTION].find_one({"_id": chat_id}, {"mode": 1, "pending_timeout_task_id": 1})  
            current_mode = chat_doc.get("mode", "human") if chat_doc else "human"  
            pending_task_id = chat_doc.get("pending_timeout_task_id") if chat_doc else None

            # Revogar task anterior SE HOUVER (independentemente do modo atual)  
            if pending_task_id:  
                 try:  
                     celery_app.control.revoke(pending_task_id)  
                     log.info(f"Revoked previous timeout task {pending_task_id} for chat {chat_id}")  
                     # Limpar do DB ou deixar a task que vai rodar limpar? Deixar limpar.  
                 except Exception as revoke_err:  
                      log.error(f"Failed to revoke timeout task {pending_task_id}: {revoke_err}")

            # Agendar NOVA task APENAS se modo for 'human' e AutoResponder ativo  
            if current_mode == "human":  
                 # Buscar settings (idealmente usar cache)  
                 enabled = await get_setting_value("autoresponder_enabled", db, default=False)  
                 timeout_min = await get_setting_value("autoresponder_timeout_minutes", db, default=5)  
                 if enabled and isinstance(timeout_min, int) and timeout_min > 0:  
                      eta = datetime.now(timezone.utc) + timedelta(minutes=timeout_min)  
                      try:  
                           task = celery_app.send_task(  
                               "whatsapp.check_chat_timeout", # Nome da task  
                               args=[chat_id, message_id_wami], # Passar chat e ID desta msg  
                               kwargs={"scheduled_time_iso": eta.isoformat(), "trace_id": trace_id_var.get()},  
                               eta=eta # Agendar  
                           )  
                           # Salvar ID da task no chat  
                           await db[WHATSAPP_CHATS_COLLECTION].update_one({"_id": chat_id}, {"$set": {"pending_timeout_task_id": task.id}})  
                           log.info(f"AutoResponder task {task.id} scheduled for chat {chat_id} at {eta.isoformat()}")  
                      except Exception as sched_err:  
                           log.exception(f"Failed to schedule timeout task for chat {chat_id}: {sched_err}")  
            else:  
                 # Se modo agente, garantir que não há task pendente no DB  
                 if pending_task_id:  
                      await db[WHATSAPP_CHATS_COLLECTION].update_one({"_id": chat_id}, {"$unset": {"pending_timeout_task_id": ""}})

    except Exception as e:  
        log.exception(f"Core error processing incoming message {message_id_wami}: {e}")

async def process_status_update(status_update: Dict, db: AsyncIOMotorDatabase, log: logger):  
    """Processes a message status update: Update DB, Broadcast WS."""  
    # (Lógica como antes)  
    message_id_wami = status_update.get('id'); status_val = status_update.get('status');  
    timestamp_unix = int(status_update.get('timestamp', 0)); timestamp_dt = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc) if timestamp_unix else datetime.now(timezone.utc);  
    chat_id = status_update.get('recipient_id') # WA ID do usuário  
    if not message_id_wami or not status_val or not chat_id: log.warning(f"Incomplete status update: {status_update}"); return  
    log.info(f"Processing status update for WAMI:{message_id_wami}: '{status_val}'")  
    try:  
        update_result = await db[WHATSAPP_MESSAGES_COLLECTION].update_one(  
            {"_id": message_id_wami},  
            {"$set": {"status": status_val, "status_timestamp": timestamp_dt}}  
        )  
        if update_result.matched_count > 0:  
            log.debug(f"Msg {message_id_wami} status updated to '{status_val}'.")  
            await ws_manager.broadcast({  
                "type": "whatsapp_message_status",  
                "payload": {"id": message_id_wami, "chat_id": chat_id, "status": status_val, "timestamp": timestamp_dt.isoformat()}  
            })  
        else: log.warning(f"Status update for unknown WAMI: {message_id_wami}")  
        if status_val == 'failed': log.error(f"Message {message_id_wami} failed: {status_update.get('errors')}")  
    except Exception as e: log.exception(f"Error processing status update for {message_id_wami}: {e}")

# Helper para buscar setting (usado por process_incoming_message)  
async def get_setting_value(key: str, db: AsyncIOMotorDatabase, default: Any = None) -> Any:  
     try:  
        setting_doc = await db["settings"].find_one({"_id": key})  
        return setting_doc.get("value", default) if setting_doc else default  
     except Exception as e:  
         logger.error(f"Failed to fetch setting '{key}': {e}")  
         return default

# --- API Endpoints ---

@router.get("/webhook", ...) # OK como antes  
async def verify_whatsapp_webhook(...): ...

@router.post("/webhook", ...) # OK como antes (chama helpers)  
async def handle_whatsapp_webhook_endpoint(...): ...

@router.post("/send", ...)  
async def send_whatsapp_message_endpoint(  
    payload: SendMessagePayloadAPI, # Usar modelo API  
    request: Request, # Para auditoria e IP  
    audit_service: Annotated[AuditService, Depends(get_audit_service)],  
    current_user: CurrentUser # UserInDB  
):  
    """Endpoint para humanos enviarem mensagens via API."""  
    trace_id = trace_id_var.get(); log = logger.bind(trace_id=trace_id, user=current_user.email, recipient=payload.recipient_wa_id)  
    log.info("Request from human user to send WhatsApp message.")

    if not settings.META_ACCESS_TOKEN: raise HTTPException(503, "WhatsApp sending not configured.")

    internal_message_id = f"out_{current_user.email}_{uuid.uuid4().hex[:8]}"  
    chat_id = payload.recipient_wa_id # Usar número como chat ID

    try:  
        db = get_database()  
        # Salvar mensagem no DB  
        message_doc = {  
            "_id": internal_message_id, "chat_id": chat_id, "sender_id": f"employee:{current_user.email}", # Identificar sender  
            "recipient_id": payload.recipient_wa_id, "content": payload.content, "type": "text",  
            "timestamp": datetime.now(timezone.utc), "status": "pending_queue", "createdAt": datetime.now(timezone.utc)  
        }  
        await db[WHATSAPP_MESSAGES_COLLECTION].insert_one(message_doc)  
        log.debug(f"Outgoing human message {internal_message_id} stored.")

        # --- Revogar AutoResponder Task ---  
        chat_doc = await db[WHATSAPP_CHATS_COLLECTION].find_one({"_id": chat_id}, {"pending_timeout_task_id": 1})  
        pending_task_id = chat_doc.get("pending_timeout_task_id") if chat_doc else None  
        if pending_task_id:  
            try:  
                celery_app.control.revoke(pending_task_id)  
                log.info(f"Revoked pending AutoResponder task {pending_task_id} for chat {chat_id}")  
                await db[WHATSAPP_CHATS_COLLECTION].update_one({"_id": chat_id}, {"$unset": {"pending_timeout_task_id": ""}})  
            except Exception as revoke_err:  
                 log.error(f"Failed to revoke timeout task {pending_task_id}: {revoke_err}")  
        # --- Fim Revogação ---

        # Enfileirar task de envio  
        celery_app.send_task("whatsapp.send_message", args=[payload.recipient_wa_id, payload.content, internal_message_id], kwargs={"trace_id": trace_id})  
        log.info(f"Task enqueued to send message {internal_message_id}.")

        # Broadcast via WS (como antes)  
        # ... (broadcast api_message) ...

        # Logar auditoria  
        await audit_service.log_audit_event(  
            action="whatsapp_message_sent_by_human", status="success", entity_type="WhatsAppMessage",  
            entity_id=internal_message_id, request=request, current_user=current_user,  
            details={"recipient": payload.recipient_wa_id, "content_preview": payload.content[:50]+"..."}  
        )

        return SendMessageResponseAPI(status="queued", internal_message_id=internal_message_id)  
    except Exception as e:  
        log.exception("Error processing send message request.")  
        await audit_service.log_audit_event(action="whatsapp_message_send_failed", status="failure", ...) # Logar falha  
        raise HTTPException(status_code=500, detail="Failed to queue message for sending.")

@router.get("/chats", ...) # OK como antes (usar WhatsAppChatAPI)  
async def list_whatsapp_chats_endpoint(...): ...

@router.get("/chats/{chat_id}/messages", ...) # OK como antes (usar WhatsAppMessageAPI)  
async def get_whatsapp_chat_messages_endpoint(...): ...

@router.post("/chats/{chat_id}/mode", ...) # OK como antes (usar ChatModePayloadAPI, ChatModeResponseAPI)  
async def set_chat_mode_endpoint(...): ...

# Adicionar imports necessários no topo  
import asyncio  
from datetime import datetime, timezone, timedelta  
from bson import ObjectId  
from app.modules.office.services_audit import AuditService, get_audit_service  
from app.modules.people.models import UserInDB # Para current_user
