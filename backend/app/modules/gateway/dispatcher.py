# agentos_core/app/modules/gateway/dispatcher.py

from typing import Dict, Any, Optional, Callable, Awaitable
from loguru import logger
from pydantic import ValidationError, BaseModel
from fastapi import HTTPException

# Importar Services de todos os módulos relevantes
from app.modules.sales.services import get_sales_service
from app.modules.delivery.services import get_delivery_service
from app.modules.people.services import get_people_service
from app.modules.tasks.services import get_task_service
# Repositório de usuário para buscar o objeto UserInDB
from app.modules.people.repository import get_user_repository
from app.modules.people.models import UserInDB

# Importar modelos Pydantic API para validação de entidades/parâmetros
from app.models.sales import OrderCreateAPI
from app.models.tasks import TaskCreateAPI

ValidatedPayloadType = BaseModel | Dict[str, Any]
ServiceFunctionType = Callable[[ValidatedPayloadType, UserInDB], Awaitable[Dict[str, Any]]]

INTENT_ACTION_MAP: Dict[str, ServiceFunctionType] = {
    "create_order": get_sales_service().create_order_from_payload,
    "get_order_status": get_sales_service().get_order_status_by_ref,
    "create_task": get_task_service().create_task_from_payload,
}

async def dispatch_intent(intent: str, entities: Dict[str, Any], user: UserInDB) -> Dict[str, Any]:
    log = logger.bind(intent=intent, user_id=str(user.id), entities=entities)
    log.info("Dispatching intent...")

    service_func = INTENT_ACTION_MAP.get(intent)
    if not service_func:
        log.error(f"Intenção não mapeada para nenhuma ação: '{intent}'")
        return {
            "status": "error",
            "message": f"Desculpe, não entendi ou não posso realizar a ação: '{intent}'.",
            "data": None
        }

    validated_payload: ValidatedPayloadType = entities
    try:
        if intent == "create_order":
            validated_payload = OrderCreateAPI.model_validate(entities)
        elif intent == "create_task":
            validated_payload = TaskCreateAPI.model_validate(entities)
    except ValidationError as e:
        log.warning(f"Falha na validação Pydantic: {e.errors()}")
        return {
            "status": "error",
            "message": f"Dados inválidos para '{intent}'.",
            "data": {"validation_errors": e.errors()}
        }

    try:
        result_data = await service_func(payload=validated_payload, current_user=user)
        return {
            "status": "success",
            "message": f"Ação '{intent}' executada com sucesso.",
            "data": result_data
        }
    except HTTPException as http_exc:
        log.warning(f"HTTPException: Status={http_exc.status_code}, Detail='{http_exc.detail}'")
        return {
            "status": "error",
            "message": http_exc.detail,
            "data": {"status_code": http_exc.status_code}
        }
    except Exception as e:
        log.exception(f"Erro inesperado ao executar a função de serviço: {e}")
        return {
            "status": "error",
            "message": f"Erro interno ao processar '{intent}'.",
            "data": None
        }
