# agentos_core/app/api/endpoints/command.py

from fastapi import APIRouter, Depends, HTTPException, status, Request # Adicionar Request  
from typing import Annotated  
from loguru import logger  
import uuid

# Segurança, Modelos API, Celery, Auditoria, User  
from app.core.security import CurrentUser # Injeta UserInDB  
from app.modules.people.models import UserInDB # Para type hint  
from app.models.command import CommandRequest, CommandResponse  
from app.worker.celery_app import celery_app  
from app.modules.office.services_audit import AuditService, get_audit_service  
from app.core.logging_config import trace_id_var  
from celery.result import AsyncResult

router = APIRouter()

@router.post(  
    "", # Rota relativa ao prefixo /command  
    response_model=CommandResponse,  
    status_code=status.HTTP_202_ACCEPTED, # Indica processamento assíncrono  
    tags=["Agent Commands"],  
    summary="Submit a command for asynchronous agent processing"  
)  
async def execute_command(  
    request: Request, # Para auditoria  
    command_in: CommandRequest,  
    audit_service: Annotated[AuditService, Depends(get_audit_service)],  
    current_user: CurrentUser # Requer autenticação JWT  
):  
    """  
    Accepts a command (e.g., natural language prompt), enqueues it for  
    asynchronous processing by a Celery worker, and returns the Job ID.  
    """  
    trace_id = trace_id_var.get() or f"cmd_{uuid.uuid4().hex[:12]}"  
    log = logger.bind(trace_id=trace_id, user_id=str(current_user.id), api_endpoint="/command POST")  
    log.info(f"Received agent command request: '{command_in.prompt[:100]}...'")  
    log.debug(f"Command payload: {command_in.model_dump()}")

    # Validação básica  
    if len(command_in.prompt) > 10000: # Limite maior para prompts  
        log.warning("Command prompt exceeds length limit (10000 chars).")  
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Command prompt too long.")

    # Enfileirar a task Celery  
    try:  
        task = celery_app.send_task(  
            "agent.process_command", # Nome da task (registrado em tasks_agent.py)  
            args=[command_in.prompt],  
            kwargs={  
                "user_id": str(current_user.id), # Passar ID como string  
                "context": command_in.context,  
                "trace_id": trace_id  
            },  
            # queue='agent_commands' # Roteamento opcional  
        )  
        log.success(f"Command enqueued successfully. Celery Task ID: {task.id}")

        # Logar auditoria (tentativa de execução)  
        await audit_service.log_audit_event(  
            action="agent_command_submitted", status="success", entity_type="AgentCommand",  
            entity_id=task.id, request=request, current_user=current_user,  
            details={"prompt": command_in.prompt[:200]+"...", "context": command_in.context}  
        )

        # Retornar resposta indicando aceite  
        return CommandResponse(  
            status="accepted",  
            message="Command received and queued for processing.",  
            job_id=task.id  
        )

    except Exception as e:  
        log.exception(f"Failed to enqueue agent command task: {e}")  
        # Logar falha na auditoria  
        await audit_service.log_audit_event(  
            action="agent_command_submit_failed", status="failure", entity_type="AgentCommand",  
            request=request, current_user=current_user, error_message=str(e),  
            details={"prompt": command_in.prompt[:200]+"...", "context": command_in.context}  
        )  
        raise HTTPException(  
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  
            detail="Failed to queue command. Check queue service."  
        )

# Opcional: Endpoint de Status da Task (como antes)  
@router.get("/{job_id}/status", response_model=CommandResponse, tags=["Agent Commands"], summary="Check command task status")  
async def get_command_status(  
    job_id: str,  
    current_user: CurrentUser # Proteger endpoint? Ou permitir checar status publicamente? Proteger por padrão.  
):  
    """Checks the status and result (if ready) of a background command task."""  
    log = logger.bind(trace_id=trace_id_var.get(), user_id=str(current_user.id), job_id=job_id)  
    log.info("Checking command task status.")  
    try:  
        task_result = AsyncResult(job_id, app=celery_app)  
        status_info = task_result.status  
        result_data = task_result.result if task_result.ready() else None

        log.debug(f"Celery task status: {status_info}, Result available: {task_result.ready()}")

        response_message = f"Command status: {status_info}"  
        response_details = None  
        final_status = status_info.lower() # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED

        if task_result.successful():  
            final_status = "completed"  
            response_message = "Command completed successfully."  
            if isinstance(result_data, dict):  
                 response_message = result_data.get("message", response_message)  
                 response_details = result_data.get("details")  
            elif result_data is not None:  
                 response_message = str(result_data)  
        elif task_result.failed():  
            final_status = "failed"  
            log.warning(f"Command task {job_id} failed. Result/Traceback: {result_data}")  
            error_detail = str(result_data) or "Worker task failed execution."  
            response_message = f"Command execution failed: {error_detail}"  
            # Opcional: mascarar detalhes de traceback para o cliente  
            # response_details = {"error_type": type(result_data).__name__} if result_data else None  
        # Tratar outros status Celery  
        elif status_info == 'STARTED': final_status = "executing"; response_message = "Command processing..."  
        elif status_info == 'PENDING': final_status = "queued"; response_message = "Command queued..."  
        elif status_info == 'RETRY': final_status = "retrying"; response_message = "Command failed, retrying..."

        return CommandResponse(status=final_status, message=response_message, details=response_details, job_id=job_id)  
    except Exception as e:  
        log.exception(f"Error checking Celery task status for job_id {job_id}: {e}")  
        raise HTTPException(status_code=500, detail="Failed to retrieve command status.")
