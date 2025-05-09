\# agentos_core/app/modules/delivery/routers.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request  
from typing import List, Optional  
from loguru import logger

\# Dependências de Auth e Roles  
from app.core.security import CurrentUser, UserInDB, require_role \# Importar require_role  
from app.modules.people.repository import UserRepository, get_user_repository \# Para enriquecer

\# Modelos API e Payloads  
from app.models.delivery import ( \# Importar modelos API  
    Delivery as DeliveryAPI,  
    AssignDriverPayloadAPI,  
    UpdateStatusPayloadAPI,  
    AddTrackingEventPayloadAPI  
)  
\# Modelos Internos/DB (para type hints e service)  
from .models import DeliveryInDB, AddTrackingEventInternal \# Importar modelo interno do evento

\# Repositórios e Serviços  
from .repository import DeliveryRepository, get_delivery_repository  
from .services import DeliveryService, get_delivery_service  
from app.modules.sales.repository import OrderRepository, get_order_repository  
from app.core.counters import CounterService, get_counter_service  
from app.modules.office.services_audit import AuditService, get_audit_service

delivery_router \= APIRouter()

\# Helper de Permissão (redefinido aqui para clareza, pode ser movido para utils)  
def check_delivery_permission(delivery: DeliveryInDB | DeliveryAPI, user: UserInDB, action: str \= \\"view\\"):  
    if not delivery or not user: return False  
    is_owner \= delivery.customer_id \== user.id  
    is_driver \= delivery.assigned_driver_id and delivery.assigned_driver_id \== user.id  
    is_staff \= any(role in user.roles for role in \[\\"admin\\", \\"sales_rep\\", \\"support\\", \\"stock_manager\\"\])  
    if action \== \\"view\\": return is_owner or is_driver or is_staff  
    if action in \[\\"update_status\\", \\"add_tracking\\"\]: return is_driver or is_staff  
    if action \== \\"assign_driver\\": return is_staff \# Apenas Staff atribui  
    return False

\# \--- Endpoints \---

@delivery_router.post(  
    \\"/from_order/{order_id}\\",  
    response_model=DeliveryAPI, \# Retorna modelo API  
    status_code=status.HTTP_201_CREATED,  
    \# Definir roles que podem criar/disparar entregas  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"sales_rep\\", \\"system\\"\]))\],  
    summary=\\"Create a delivery record from an existing order\\",  
    tags=\[\\"Deliveries\\"\]  
)  
async def create_delivery(  
    request: Request, \# Para auditoria  
    order_id: str \= Path(..., description=\\"ID do pedido para criar a entrega\\"),  
    delivery_service: DeliveryService \= Depends(get_delivery_service),  
    delivery_repo: DeliveryRepository \= Depends(get_delivery_repository),  
    order_repo: OrderRepository \= Depends(get_order_repository),  
    counter_service: CounterService \= Depends(get_counter_service),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Quem disparou  
):  
    \\"\\"\\"(Staff/System) Creates a delivery entry based on a valid order ID.\\"\\"\\"  
    log \= logger.bind(order_id=order_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Criando entrega a partir do pedido...\\")  
    try:  
        \# Service lida com a lógica e validações  
        created_delivery_db \= await delivery_service.create_delivery_from_order(  
            order_id_str=order_id,  
            delivery_repo=delivery_repo,  
            order_repo=order_repo,  
            counter_service=counter_service  
        )  
        \# Logar auditoria de sucesso  
        await audit_service.log_audit_event(  
            action=\\"delivery_created\\", status=\\"success\\", entity_type=\\"Delivery\\",  
            entity_id=created_delivery_db.id, request=request, current_user=current_user,  
            details={\\"delivery_ref\\": created_delivery_db.delivery_ref, \\"order_id\\": order_id}  
        )  
        \# Enriquecer e retornar modelo API  
        user_repo \= await get_user_repository() \# Obter repo para enriquecer  
        \# Criar função de enriquecimento no service? Ou fazer aqui? Fazer aqui por enquanto.  
        delivery_api \= DeliveryAPI.model_validate(created_delivery_db)  
        \# Adicionar nome do motorista se já houver (improvável na criação)  
        return delivery_api

    except HTTPException as http_exc: \# Capturar erros 4xx do service  
        log.warning(f\\"Falha ao criar entrega: {http_exc.detail} (Status: {http_exc.status_code})\\")  
        await audit_service.log_audit_event(  
            action=\\"delivery_create_failed\\", status=\\"failure\\", entity_type=\\"Delivery\\",  
            request=request, current_user=current_user, error_message=http_exc.detail,  
            details={\\"order_id\\": order_id}  
        )  
        raise http_exc  
    except Exception as e: \# Capturar erros 5xx inesperados  
        log.exception(f\\"Erro inesperado ao criar entrega para pedido {order_id}: {e}\\")  
        await audit_service.log_audit_event(  
            action=\\"delivery_create_failed\\", status=\\"failure\\", entity_type=\\"Delivery\\",  
            request=request, current_user=current_user, error_message=str(e), details={\\"order_id\\": order_id}  
        )  
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=\\"Internal server error creating delivery.\\")

@delivery_router.get(  
    \\"/{delivery_id}\\",  
    response_model=DeliveryAPI,  
    summary=\\"Get delivery details by internal ID\\",  
    tags=\[\\"Deliveries\\"\]  
    \# Sem require_role aqui, a verificação é feita no código  
)  
async def get_delivery(  
    request: Request,  
    delivery_id: str \= Path(..., description=\\"ID interno da Entrega (ObjectId)\\"),  
    delivery_service: DeliveryService \= Depends(get_delivery_service), \# Para enriquecer  
    delivery_repo: DeliveryRepository \= Depends(get_delivery_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Para enriquecer  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user),  
):  
    \\"\\"\\"Retrieves details for a specific delivery by its internal MongoDB ID.\\"\\"\\"  
    log \= logger.bind(delivery_id=delivery_id, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando entrega por ID...\\")

    \# Usar service para buscar e enriquecer  
    delivery_api \= await delivery_service.get_delivery(delivery_id, delivery_repo, user_repo)

    if not delivery_api:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Delivery not found\\")

    \# Verificar permissão  
    if not check_delivery_permission(delivery_api, current_user, action=\\"view\\"):  
        log.warning(\\"Acesso negado para ver entrega.\\")  
        await audit_service.log_audit_event(  
            action=\\"delivery_view_denied\\", status=\\"failure\\", entity_type=\\"Delivery\\", entity_id=delivery_id,  
            request=request, current_user=current_user, error_message=\\"Permission denied\\"  
        )  
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=\\"Not authorized to view this delivery\\")

    \# Logar acesso (opcional)  
    \# await audit_service.log_audit_event(action=\\"delivery_viewed\\", ...)  
    return delivery_api

@delivery_router.get(  
    \\"/ref/{delivery_ref}\\",  
    response_model=DeliveryAPI,  
    summary=\\"Get delivery details by reference code\\",  
    tags=\[\\"Deliveries\\"\]  
)  
async def get_delivery_by_reference(  
    request: Request,  
    delivery_ref: str \= Path(..., description=\\"Referência da Entrega (ex: DLV-2025-00123)\\"),  
    delivery_service: DeliveryService \= Depends(get_delivery_service),  
    delivery_repo: DeliveryRepository \= Depends(get_delivery_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user),  
):  
    \\"\\"\\"Retrieves delivery details by its reference code.\\"\\"\\"  
    log \= logger.bind(delivery_ref=delivery_ref, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando entrega por referência...\\")

    delivery_db \= await delivery_repo.get_by_ref(delivery_ref)  
    if not delivery_db: raise HTTPException(status_code=404, detail=\\"Delivery not found\\")

    \# Enriquecer e checar permissão  
    delivery_api \= await delivery_service._enrich_delivery(delivery_db, user_repo) \# Usar helper interno se existir ou fazer aqui  
    if not check_delivery_permission(delivery_api, current_user, action=\\"view\\"):  
        await audit_service.log_audit_event(action=\\"delivery_view_denied\\", ...)  
        raise HTTPException(status_code=403, detail=\\"Not authorized to view this delivery\\")

    return delivery_api

@delivery_router.patch(  
    \\"/{delivery_id}/assign\\",  
    response_model=DeliveryAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"sales_rep\\", \\"support\\"\]))\], \# Staff apenas  
    summary=\\"Assign a driver to a delivery\\",  
    tags=\[\\"Deliveries\\"\]  
)  
async def assign_delivery_driver(  
    request: Request,  
    delivery_id: str \= Path(..., description=\\"ID da Entrega a ser atribuída\\"),  
    payload: AssignDriverPayloadAPI, \# Recebe modelo API  
    delivery_service: DeliveryService \= Depends(get_delivery_service),  
    delivery_repo: DeliveryRepository \= Depends(get_delivery_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Necessário para validar e enriquecer  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Quem está atribuindo  
):  
    \\"\\"\\"(Staff Only) Assigns a valid delivery driver to a pending delivery.\\"\\"\\"  
    log \= logger.bind(delivery_id=delivery_id, user_id=str(current_user.id))  
    log.info(f\\"Endpoint: Atribuindo motorista {payload.driver_id}...\\")  
    try:  
        \# Service lida com busca, validações (permissão base já feita), update e auditoria interna  
        updated_delivery_db \= await delivery_service.assign_driver(  
            delivery_id_str=delivery_id,  
            driver_id_str=payload.driver_id,  
            delivery_repo=delivery_repo,  
            user_repo=user_repo,  
            audit_service=audit_service,  
            current_user=current_user  
        )  
        \# Enriquecer para resposta API  
        return await delivery_service._enrich_delivery(updated_delivery_db, user_repo)  
    except HTTPException as http_exc:  
        \# Service já deve ter logado auditoria de falha  
        raise http_exc  
    except Exception as e:  
        log.exception(\\"Erro inesperado ao atribuir motorista.\\")  
        await audit_service.log_audit_event(action=\\"delivery_assign_failed\\", status=\\"failure\\", entity_id=delivery_id, request=request, current_user=current_user, error_message=f\\"Unexpected error: {e}\\")  
        raise HTTPException(status_code=500, detail=\\"Internal server error assigning driver.\\")

@delivery_router.patch(  
    \\"/{delivery_id}/status\\",  
    response_model=DeliveryAPI,  
    \# Permissão verificada dentro do endpoint (motorista ou staff)  
    summary=\\"Update the status of a delivery\\",  
    tags=\[\\"Deliveries\\"\]  
)  
async def update_delivery_status_endpoint(  
    request: Request,  
    delivery_id: str \= Path(..., description=\\"ID da Entrega a ter status atualizado\\"),  
    payload: UpdateStatusPayloadAPI, \# Modelo API  
    delivery_service: DeliveryService \= Depends(get_delivery_service),  
    delivery_repo: DeliveryRepository \= Depends(get_delivery_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Para enriquecer e checar permissão  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Updates the main status of the delivery and adds a tracking event.\\"\\"\\"  
    log \= logger.bind(delivery_id=delivery_id, user_id=str(current_user.id), new_status=payload.status)  
    log.info(\\"Endpoint: Atualizando status da entrega...\\")

    \# Buscar ANTES para verificar permissão  
    delivery_db_check \= await delivery_repo.get_by_id(delivery_id)  
    if not delivery_db_check: raise HTTPException(status_code=404, detail=\\"Delivery not found\\")  
    delivery_api_check \= DeliveryAPI.model_validate(delivery_db_check) \# Para helper

    if not check_delivery_permission(delivery_api_check, current_user, action=\\"update_status\\"):  
        await audit_service.log_audit_event(action=\\"delivery_status_update_denied\\", ...)  
        raise HTTPException(status_code=403, detail=\\"Not authorized to update this delivery's status\\")

    try:  
        \# Service lida com validação de transição, update e adição de evento tracking  
        updated_delivery_db \= await delivery_service.update_delivery_status(  
            delivery_id_str=delivery_id,  
            new_status=payload.status,  
            delivery_repo=delivery_repo,  
            notes=payload.notes,  
            location=payload.location_note  
            \# Passar audit_service/user se o log for feito no service? Não, fazemos aqui.  
        )  
        \# Logar auditoria de SUCESSO aqui  
        await audit_service.log_audit_event(  
            action=\\"delivery_status_updated\\", status=\\"success\\", entity_type=\\"Delivery\\", entity_id=delivery_id,  
            request=request, current_user=current_user,  
            details={\\"delivery_ref\\": updated_delivery_db.delivery_ref, \\"old_status\\": delivery_api_check.current_status, \\"new_status\\": payload.status, \\"location\\": payload.location_note}  
        )  
        \# Enriquecer para resposta API  
        return await delivery_service._enrich_delivery(updated_delivery_db, user_repo)  
    except HTTPException as http_exc:  
        \# Service pode levantar 400 para transição inválida ou 404/500 para outros erros  
        await audit_service.log_audit_event(action=\\"delivery_status_update_failed\\", status=\\"failure\\", entity_id=delivery_id, request=request, current_user=current_user, error_message=http_exc.detail, details={\\"target_status\\": payload.status})  
        raise http_exc  
    except Exception as e:  
        log.exception(\\"Erro inesperado ao atualizar status da entrega.\\")  
        await audit_service.log_audit_event(action=\\"delivery_status_update_failed\\", status=\\"failure\\", entity_id=delivery_id, request=request, current_user=current_user, error_message=str(e), details={\\"target_status\\": payload.status})  
        raise HTTPException(status_code=500, detail=\\"Internal server error updating delivery status.\\")

@delivery_router.post(  
    \\"/{delivery_id}/tracking\\",  
    response_model=DeliveryAPI,  
    \# Permissão verificada dentro (motorista ou staff)  
    summary=\\"Add a manual tracking event to a delivery\\",  
    tags=\[\\"Deliveries\\"\]  
)  
async def add_tracking_event_endpoint(  
    request: Request,  
    delivery_id: str \= Path(..., description=\\"ID da Entrega para adicionar evento\\"),  
    event_data: AddTrackingEventPayloadAPI, \# Modelo API  
    delivery_service: DeliveryService \= Depends(get_delivery_service),  
    delivery_repo: DeliveryRepository \= Depends(get_delivery_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Para enriquecer  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Adds a manual tracking event to the delivery's history.\\"\\"\\"  
    log \= logger.bind(delivery_id=delivery_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Adicionando evento de tracking manual...\\")

    \# Buscar ANTES para verificar permissão  
    delivery_db_check \= await delivery_repo.get_by_id(delivery_id)  
    if not delivery_db_check: raise HTTPException(status_code=404, detail=\\"Delivery not found\\")  
    delivery_api_check \= DeliveryAPI.model_validate(delivery_db_check)

    if not check_delivery_permission(delivery_api_check, current_user, action=\\"add_tracking\\"):  
        await audit_service.log_audit_event(action=\\"delivery_tracking_add_denied\\", ...)  
        raise HTTPException(status_code=403, detail=\\"Not authorized to add tracking to this delivery\\")

    try:  
        \# Converter payload API para modelo interno se necessário no service  
        event_internal \= AddTrackingEventInternal(\*\*event_data.model_dump())  
        updated_delivery_db \= await delivery_service.add_manual_tracking_event(  
            delivery_id_str=delivery_id,  
            event_data=event_internal,  
            delivery_repo=delivery_repo  
        )  
        \# Logar auditoria de sucesso  
        await audit_service.log_audit_event(  
            action=\\"delivery_tracking_event_added\\", status=\\"success\\", entity_type=\\"Delivery\\", entity_id=delivery_id,  
            request=request, current_user=current_user,  
            details={\\"delivery_ref\\": updated_delivery_db.delivery_ref, \\"event_status\\": event_data.status, \\"location\\": event_data.location_note}  
        )  
        \# Enriquecer para resposta API  
        return await delivery_service._enrich_delivery(updated_delivery_db, user_repo)  
    except HTTPException as http_exc:  
        await audit_service.log_audit_event(action=\\"delivery_tracking_add_failed\\", status=\\"failure\\", ...)  
        raise http_exc  
    except Exception as e:  
        log.exception(\\"Erro inesperado ao adicionar evento de tracking.\\")  
        await audit_service.log_audit_event(action=\\"delivery_tracking_add_failed\\", status=\\"failure\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error adding tracking event.\\")

\# Adicionar listagem de Entregas (GET /) \- similar a list_deliveries no exemplo anterior  
\# ...

\# Importar timedelta para exemplo de data estimada  
from datetime import timedelta
