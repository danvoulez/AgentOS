# agentos_core/app/worker/tasks_agent.py

from app.worker.celery_app import celery_app  
from loguru import logger  
from app.core.logging_config import trace_id_var  
import uuid  
import asyncio  
from typing import Dict, Any, Optional

# Tentar importar engine - pode causar erro circular se engine importar worker  
ENGINE_AVAILABLE = False  
agent_process_prompt = None  
try:  
    from app.modules.gateway.services import GatewayService, get_gateway_service # Chamar Gateway pode ser melhor  
    ENGINE_AVAILABLE = True  
    logger.info("GatewayService importado com sucesso para tasks_agent.")  
except ImportError as e:  
     logger.error(f"Could not import GatewayService, agent tasks may fail: {e}")  
     # Definir função dummy se falhar  
     async def agent_process_prompt_dummy(prompt: str, **kwargs) -> Dict[str, Any]:  
         logger.error("GatewayService não disponível.")  
         return {"status": "error", "message": "Agent engine (GatewayService) unavailable due to import error."}  
     agent_process_prompt = agent_process_prompt_dummy # Usar dummy

@celery_app.task(bind=True, name="agent.process_command", max_retries=2, default_retry_delay=30, acks_late=True)  
def process_agent_command_task(self, prompt: str, user_id: str | None = None, context: dict | None = None, trace_id: str | None = None):  
    """  
    Task Celery para processar comando genérico do agente (atualmente stub/placeholder).  
    Deveria chamar a lógica principal de processamento de prompt/intenção.  
    """  
    current_trace_id = trace_id or f"task_{uuid.uuid4().hex[:12]}"  
    token = trace_id_var.set(current_trace_id)  
    log = logger.bind(trace_id=current_trace_id, task_name=self.name, job_id=self.request.id, user_id=user_id or "N/A")

    log.info(f"Received agent command task for processing. Prompt starts: '{prompt[:80]}...'")  
    log.debug(f"Context received: {context}")

    if not ENGINE_AVAILABLE or agent_process_prompt is None:  
         log.error("Agent engine (GatewayService) is not available. Task cannot proceed.")  
         return {"status": "error", "message": "Agent engine unavailable."}

    try:  
        # --- Lógica Real (Placeholder) ---  
        # Idealmente, esta task chamaria o GatewayService ou uma lógica similar  
        # para interpretar o prompt e executar a ação/ferramenta apropriada.  
        # Como o Gateway já faz isso via API HTTP, chamar o Gateway aqui pode ser redundante  
        # ou usado para operações muito longas que não cabem em um request HTTP.

        # Exemplo simulado:  
        log.warning("Agent command processing logic is currently a placeholder.")  
        async def run_mock_processing():  
             await asyncio.sleep(2) # Simular trabalho  
             # Simular uma chamada ao Gateway ou engine interno  
             # result = await agent_process_prompt(prompt, user_id=user_id, context=context)  
             return {"success": True, "message": f"Command processed (Mock): {prompt[:50]}..."}

        result = asyncio.run(run_mock_processing())  
        # --- Fim Lógica Real ---

        log.info(f"Agent command processing completed. Result Success: {result.get('success', False)}")  
        log.debug(f"Full Result: {result}")

        # TODO: Notificar via WebSocket/PubSub?  
        return result

    except Exception as e:  
        log.exception("Error encountered while processing agent command.")  
        try:  
            retry_countdown = int(celery_app.conf.task_default_retry_delay * (2 ** self.request.retries))  
            log.warning(f"Retrying task in {retry_countdown} seconds (Attempt {self.request.retries + 1}/{self.max_retries}). Error: {e}")  
            self.retry(exc=e, countdown=retry_countdown)  
        except self.MaxRetriesExceededError:  
            log.error("Max retries exceeded for agent command task.")  
            return {"status": "failed", "message": "Task failed after max retries.", "error": str(e)}  
        except Exception as retry_err:  
             log.exception(f"Failed to initiate retry: {retry_err}")  
             raise e  
    finally:  
        trace_id_var.reset(token)

# --- Task Periódica Exemplo ---  
# @celery_app.task(name="agent.cleanup_logs")  
# def cleanup_logs_task(): ... (implementar se necessário)
