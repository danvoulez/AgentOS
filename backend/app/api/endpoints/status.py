# agentos_core/app/api/endpoints/status.py

from fastapi import APIRouter, Depends, HTTPException, status as http_status # Renomear status  
from loguru import logger  
import uuid  
from redis.asyncio import Redis  
import asyncio # Para gather

# Modelos e Dependências Core  
from app.models.api_common import StatusResponse  
from app.core.logging_config import trace_id_var  
from app.core.database import get_database, get_redis_client # Funções de dependência  
from app.worker.celery_app import celery_app # Para checar conexão Celery

router = APIRouter()

@router.get(  
    "", # Rota relativa ao prefixo /status  
    response_model=StatusResponse,  
    tags=["Status"],  
    summary="Application Health and Component Status Check"  
)  
async def get_application_status(  
    # Tornar público ou requerer auth? Público é comum para health checks.  
    # current_user: Optional[CurrentUser] = None # Exemplo se quisesse proteger  
    db: AsyncIOMotorDatabase = Depends(get_database), # Injetar DB  
    redis: Redis = Depends(get_redis_client) # Injetar Redis  
):  
    """  
    Performs health checks on critical components (Database, Cache/Broker)  
    and returns the overall application status.  
    """  
    trace_id = trace_id_var.get() or f"status_{uuid.uuid4().hex[:8]}"  
    log = logger.bind(trace_id=trace_id, api_endpoint="/status GET")  
    log.info("Performing application status check...")

    component_statuses = {}  
    overall_ok = True

    # --- Check MongoDB ---  
    try:  
        await db.command('ping')  
        component_statuses["database_mongodb"] = "ok"  
        log.debug("MongoDB ping successful.")  
    except Exception as e:  
        log.error(f"MongoDB connection check failed: {e}", exc_info=False)  
        component_statuses["database_mongodb"] = "error"  
        overall_ok = False

    # --- Check Redis (Cache/Broker) ---  
    try:  
        await redis.ping()  
        component_statuses["cache_broker_redis"] = "ok"  
        log.debug("Redis ping successful.")  
    except Exception as e:  
        log.error(f"Redis connection check failed: {e}", exc_info=False)  
        component_statuses["cache_broker_redis"] = "error"  
        overall_ok = False

    # --- Check Celery Worker Availability (Opcional - mais complexo) ---  
    # try:  
    #     # Ping workers - pode ser lento e não 100% confiável  
    #     stats = celery_app.control.inspect().ping()  
    #     if stats and any(workers for workers in stats.values()):  
    #         component_statuses["celery_workers"] = "ok" # Pelo menos um respondeu  
    #         log.debug(f"Celery worker ping response: {stats}")  
    #     else:  
    #         component_statuses["celery_workers"] = "unavailable"  
    #         log.warning("No Celery workers responded to ping.")  
    #         # Não marcar overall como error por isso? Ou sim? Depende da criticidade.  
    #         # overall_ok = False  
    # except Exception as e:  
    #     log.error(f"Celery worker check failed: {e}", exc_info=False)  
    #     component_statuses["celery_workers"] = "error"  
    #     # overall_ok = False  
    component_statuses["celery_workers"] = "check_not_implemented" # Marcar como não checado

    # --- Construir Resposta ---  
    final_status = "ok" if overall_ok else "error"  
    status_message = f"Overall: {final_status.upper()} | Components: {component_statuses}"  
    log.info(f"Status check completed: {status_message}")

    # Retornar 503 se componentes críticos falharem  
    if not overall_ok:  
         # Usar status 503 para indicar que o serviço não está saudável  
         # Alguns load balancers usam isso para remover a instância.  
         raise HTTPException(status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE, detail=status_message)

    return StatusResponse(status=final_status, message="All critical components operational.")

# Importar AsyncIOMotorDatabase para type hint  
from motor.motor_asyncio import AsyncIOMotorDatabase
