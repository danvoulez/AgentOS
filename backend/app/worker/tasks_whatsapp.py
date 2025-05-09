# agentos_core/app/worker/tasks_whatsapp.py

from app.worker.celery_app import celery_app  
from loguru import logger  
from app.core.logging_config import trace_id_var  
import uuid  
import asyncio  
from datetime import datetime, timezone, timedelta # Adicionar timedelta  
from typing import List, Optional, Dict, Any

# Importar services e DB  
from app.services import whatsapp_service # Serviço que CHAMA a API Meta  
from app.db.mongo_client import get_database, AsyncIOMotorDatabase  
from app.websocket.connection_manager import manager as ws_manager  
from app.models.whatsapp import WhatsAppMessageAPI # Para broadcast  
# Importar dependências para AutoResponder  
from app.core.config import settings  
from app.modules.office.repository import SettingRepository, get_setting_repository # Settings  
from app.modules.people.repository import UserRepository, get_user_repository # User repo  
from app.modules.sales.repository import OrderRepository, get_order_repository # Order repo  
from app.modules.delivery.repository import DeliveryRepository, get_delivery_repository # Delivery repo  
from app.modules.people.models import UserInDB # Modelo User  
from app.modules.sales.models import Order # Modelo Order  
from app.modules.delivery.models import Delivery # Modelo Delivery  
# Importar GatewayService para chamar LLM no AutoResponder  
from app.modules.gateway.services import GatewayService, get_gateway_service

# Coleções  
WHATSAPP_CHATS_COLLECTION = "whatsapp_chats"  
WHATSAPP_MESSAGES_COLLECTION = "whatsapp_messages"

# Placeholder Vox Fallback  
async def trigger_vox_fallback(user_id: str, reason: str = "error", message_id: str | None = None, trace_id: str | None = None):  
     log = logger.bind(trace_id=trace_id, service="VoxFallback")  
     log.warning(f"[FALLBACK TRIGGERED] Reason: '{reason}' for User: '{user_id}', MsgID: {message_id}. (MOCK)")  
     await asyncio.sleep(0.1)

# Task Agente (Stub Fase 1)  
@celery_app.task(bind=True, name="whatsapp.process_agent_message", max_retries=2, default_retry_delay=45, acks_late=True)  
def process_agent_whatsapp_message(self, chat_id: str, message_id: str, trace_id: str | None = None):  
    """Task para processar msg WA no modo 'agent' (LÓGICA PENDENTE FASE 2)."""  
    current_trace_id = trace_id or f"task_{uuid.uuid4().hex[:12]}"; token = trace_id_var.set(current_trace_id)  
    log = logger.bind(trace_id=current_trace_id, task_name=self.name, job_id=self.request.id, chat_id=chat_id, incoming_msg_id=message_id)  
    log.info("Received agent processing task (LOGIC PENDING PHASE 2).")  
    # --- TODO: Implement Phase 2 Logic ---  
    # Buscar histórico, chamar Gateway/LLM, salvar resposta, enfileirar envio  
    log.warning("Agent processing logic not yet implemented.")  
    # ---  
    trace_id_var.reset(token)  
    return {"status": "skipped_phase2", "response_message_id": None}

# Task Envio de Mensagem (Implementada)  
@celery_app.task(bind=True, name="whatsapp.send_message", max_retries=4, default_retry_delay=45, acks_late=True, reject_on_worker_lost=True)  
def send_whatsapp_message(self, recipient_wa_id: str, message_text: str, internal_message_id: str, trace_id: str | None = None):  
    """Task Celery: Chama Meta API via service, atualiza DB, broadcast WS."""  
    current_trace_id = trace_id or f"task_{uuid.uuid4().hex[:12]}"; token = trace_id_var.set(current_trace_id)  
    log = logger.bind(trace_id=current_trace_id, task_name=self.name, job_id=self.request.id, recipient=recipient_wa_id, internal_msg_id=internal_message_id)  
    log.info("Executing task to send WhatsApp message via Meta API...")  
    db: AsyncIOMotorDatabase = get_database()  
    new_status = "failed_send"; wami: Optional[str] = None; success = False

    try:  
        # 1. Chamar o serviço de envio  
        # Usar asyncio.run para chamar a função async do service dentro da task sync  
        loop = asyncio.get_event_loop()  
        success, wami = loop.run_until_complete(  
            whatsapp_service.send_whatsapp_text_message(recipient_wa_id, message_text)  
        )  
        new_status = "sent" if success else "failed_send"  
        log.info(f"WhatsApp API send result: Success={success}, WAMI={wami}")

        # 2. Atualizar status no MongoDB  
        update_data = {"status": new_status, "status_timestamp": datetime.now(timezone.utc)}  
        if success and wami: update_data["official_wami"] = wami

        update_result = loop.run_until_complete(  
             db[WHATSAPP_MESSAGES_COLLECTION].update_one({"_id": internal_message_id}, {"$set": update_data})  
        )  
        if update_result.matched_count > 0:  
             log.info(f"Updated message {internal_message_id} status to '{new_status}' in DB.")  
             # 3. Broadcast de Status via WebSocket  
             async def broadcast_status():  
                  chat_id_for_ws = recipient_wa_id # Chat ID é o recipiente  
                  msg_to_broadcast = {  
                      "type": "whatsapp_message_status",  
                      "payload": {"id": internal_message_id, "chat_id": chat_id_for_ws, "status": new_status, "wami": wami, "timestamp": datetime.now(timezone.utc).isoformat()}  
                  }  
                  await ws_manager.broadcast(msg_to_broadcast)  
             loop.run_until_complete(broadcast_status()); log.debug("Status update broadcasted.")  
        else:  
             log.warning(f"Could not find message {internal_message_id} in DB to update status.")

        # 4. Lidar com Falha no Envio API  
        if not success:  
             raise RuntimeError(f"Meta API failed to send message (internal ID: {internal_message_id})")

        return {"status": "success", "wami": wami}

    # --- Tratamento de Erro e Retry ---  
    except Exception as e:  
        log.exception("Error executing send WhatsApp message task.")  
        # Tentar atualizar status para failed no DB  
        try: asyncio.run(db[WHATSAPP_MESSAGES_COLLECTION].update_one({"_id": internal_message_id, "status": {"$ne": "failed_send"}}, {"$set": {"status": "failed_send", "status_timestamp": datetime.now(timezone.utc)}}))  
        except Exception as db_upd_err: log.error(f"Failed to update message {internal_message_id} to 'failed_send': {db_upd_err}")  
        # Retry Celery  
        try:  
            retry_countdown = int(celery_app.conf.task_default_retry_delay * (2 ** self.request.retries))  
            log.warning(f"Retrying task in {retry_countdown}s (Attempt {self.request.retries + 1}/{self.max_retries}). Error: {e}")  
            self.retry(exc=e, countdown=retry_countdown)  
        except self.MaxRetriesExceededError:  
            log.error(f"Max retries exceeded for send WA message task ID {internal_message_id}.")  
            # asyncio.run(trigger_vox_fallback(recipient_wa_id, "send_message_failed_max_retries", internal_message_id, current_trace_id))  
            return {"status": "failed", "reason": "max_retries_exceeded", "error": str(e)}  
        except Exception as retry_err:  
             log.exception(f"Failed to initiate retry: {retry_err}"); raise e  
    finally:  
         trace_id_var.reset(token)

# --- Task AutoResponder (Implementada) ---  
@celery_app.task(bind=True, name="whatsapp.check_chat_timeout", max_retries=1, acks_late=True)  
def check_chat_timeout(self, chat_id: str, last_customer_message_id: str, scheduled_time_iso: str, trace_id: str | None = None):  
    """Verifica timeout, busca contexto, chama LLM e envia auto-resposta."""  
    current_trace_id = trace_id or f"task_{uuid.uuid4().hex[:12]}"; token = trace_id_var.set(current_trace_id)  
    log = logger.bind(trace_id=current_trace_id, task_name=self.name, job_id=self.request.id, chat_id=chat_id, check_msg_id=last_customer_message_id)  
    log.info(f"Running timeout check scheduled at {scheduled_time_iso}")  
    db: AsyncIOMotorDatabase = get_database()

    try:  
        # Executar lógica async principal  
        async def run_check():  
            # 1. Obter Configurações AutoResponder (com cache via service)  
            try:  
                # Obter instâncias de dependência dentro do run_until_complete se necessário  
                setting_repo_local = await get_setting_repository()  
                redis_client_local = get_redis_client() # Assume que connect já rodou no lifespan  
                office_service = get_office_service() # Service sem estado

                autoresponder_enabled = await office_service.get_setting("autoresponder_enabled", setting_repo_local, redis_client_local, default=False)  
                timeout_minutes = await office_service.get_setting("autoresponder_timeout_minutes", setting_repo_local, redis_client_local, default=5)  
                base_prompt_template = await office_service.get_setting("autoresponder_base_prompt", setting_repo_local, redis_client_local, default="")  
                fallback_message = await office_service.get_setting("autoresponder_fallback_message", setting_repo_local, redis_client_local, default="Recebemos sua mensagem, um atendente responderá em breve.")

                if not autoresponder_enabled or not isinstance(timeout_minutes, int) or timeout_minutes <= 0 or not base_prompt_template:  
                    log.info("AutoResponder disabled or misconfigured. Exiting check.")  
                    return  
            except Exception as config_err:  
                log.exception("Error fetching AutoResponder settings. Exiting check.")  
                return

            # 2. Verificar se última mensagem ainda é a do cliente  
            latest_message_doc = await db[WHATSAPP_MESSAGES_COLLECTION].find_one(  
                {"chat_id": chat_id}, sort=[("timestamp", DESCENDING)]  
            )  
            if not latest_message_doc or latest_message_doc["_id"] != last_customer_message_id:  
                status = "already_replied" if latest_message_doc else "no_messages_found"  
                log.info(f"Auto-response cancelled for chat {chat_id}. Reason: {status}")  
                await db[WHATSAPP_CHATS_COLLECTION].update_one({"_id": chat_id}, {"$unset": {"pending_timeout_task_id": ""}})  
                return

            # 3. Timeout Confirmado! Buscar Contexto.  
            log.info(f"Timeout confirmed for chat {chat_id}. Preparing contextual auto-response.")  
            # Buscar histórico recente  
            history_cursor = db[WHATSAPP_MESSAGES_COLLECTION].find(  
                {"chat_id": chat_id, "timestamp": {"$lt": latest_message_doc["timestamp"]}},  
                {"content": 1, "sender_id": 1}  
            ).sort("timestamp", DESCENDING).limit(5)  
            history_docs = list(reversed(await history_cursor.to_list(length=5)))  
            history_formatted = "n".join([f"- {msg.get('sender_id','?').split(':')[0]}: {msg.get('content', '')[:80]}" for msg in history_docs])

            # Buscar cliente  
            user_repo_local = await get_user_repository()  
            customer = await user_repo_local.get_by_id(chat_id) # Assumindo chat_id é user_id (ObjectId)  
            customer_name = customer.profile.first_name if customer and customer.profile else "Cliente"

            # Buscar último pedido/entrega  
            order_repo_local = await get_order_repository()  
            delivery_repo_local = await get_delivery_repository()  
            order_context = "Nenhum pedido recente encontrado."  
            # ... (Lógica para buscar order/delivery como antes) ...  
            # orders_list = await order_repo_local.list_by({"customer_id": customer.id, "status": {"$nin": ["cancelled", "failed"]}}, sort=[("created_at", DESCENDING)], limit=1) if customer else []  
            # if orders_list: ... (formatar order_context)

            # 4. Construir Prompt e chamar LLM  
            prompt_for_llm = base_prompt_template.format(  
                chat_id=chat_id, timeout=timeout_minutes, history=history_formatted,  
                last_messages=latest_message_doc.get("content", ""),  
                customer_name=customer_name, order_context=order_context # Adicionar contexto  
            )  
            messages_for_llm = [  
                {"role": "system", "content": "Você é um assistente prestativo da VoulezVous respondendo no WhatsApp porque o atendente demorou. Use o contexto para dar uma resposta curta e útil. NÃO se identifique como IA."},  
                {"role": "user", "content": prompt_for_llm}  
            ]

            response_text = fallback_message # Default  
            try:  
                llm_client = get_llm_client() # Obter cliente primário  
                llm_response = await llm_client.get_completion(messages=messages_for_llm, model=settings.OPENAI_CHAT_MODEL or "gpt-4-turbo-preview") # Usar modelo das settings?

                is_error_or_empty = llm_response.error or not (llm_response.choices and llm_response.choices[0].message.content)  
                if is_error_or_empty:  
                    log.error(f"LLM failed for auto-response chat {chat_id}: {llm_response.error.message if llm_response.error else 'Empty'}")  
                else:  
                    response_text = llm_response.choices[0].message.content.strip()  
                    log.info(f"LLM generated auto-response for chat {chat_id}.")  
            except Exception as llm_e:  
                log.exception(f"Error calling LLM for auto-response chat {chat_id}. Using fallback.")

            # 5. Enviar Resposta e Limpar Task ID  
            await _send_auto_response(log, chat_id, response_text)  
            await db[WHATSAPP_CHATS_COLLECTION].update_one({"_id": chat_id}, {"$unset": {"pending_timeout_task_id": ""}})

        # Executar a lógica async dentro da task sync  
        loop = asyncio.get_event_loop()  
        loop.run_until_complete(  
            _check_timeout_async_logic(db, log, chat_id, last_customer_message_id)  
        )

    except Exception as e:  
        log.exception("Unexpected error during check_chat_timeout task.")  
        # self.retry(exc=e) # Evitar retry automático aqui por enquanto  
    finally:  
        trace_id_var.reset(token)

async def _send_auto_response(log: logger, chat_id: str, message_text: str):  
    """Enfileira a task para enviar a mensagem e salva no DB."""  
    # ... (lógica de _send_auto_response como antes: salvar doc, enfileirar task, broadcast WS) ...  
    db: AsyncIOMotorDatabase = get_database()  
    response_id = f"auto_resp_{chat_id}_{uuid.uuid4().hex[:6]}"  
    recipient_wa_id_numeric = chat_id # Assume chat_id é o número

    agent_message_doc = { "_id": response_id, "chat_id": chat_id, "sender_id": "auto_responder", "recipient_id": chat_id, "content": message_text, "type": "text_auto_response", "timestamp": datetime.now(timezone.utc), "status": "pending_queue", "createdAt": datetime.now(timezone.utc) }  
    try:  
        await db[WHATSAPP_MESSAGES_COLLECTION].insert_one(agent_message_doc)  
        log.info(f"Auto-response {response_id} saved to DB.")  
        celery_app.send_task("app.worker.tasks_whatsapp.send_whatsapp_message", args=[recipient_wa_id_numeric, message_text, response_id], kwargs={"trace_id": trace_id_var.get()})  
        log.info(f"Task enqueued to send auto-response {response_id}.")  
        api_message = WhatsAppMessageAPI.model_validate(agent_message_doc)  
        await ws_manager.broadcast({"type": "new_whatsapp_message", "payload": api_message.model_dump(by_alias=True)})  
    except Exception as e:  
        log.exception(f"Error saving/enqueuing/broadcasting auto-response for chat {chat_id}")
