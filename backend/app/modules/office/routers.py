\# agentos_core/app/modules/stock/routers.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request, BackgroundTasks, Body  
from typing import List, Optional, Dict, Any  
from loguru import logger

\# Dependências Auth/Roles  
from app.core.security import CurrentUser, UserInDB, require_role

\# Modelos API  
from app.models.stock import ( \# Usar sufixo API  
    StockItem as StockItemAPI,  
    StockItemCreateAPI,  
    BulkStockItemCreateAPI, BulkStockItemResponseAPI,  
    StockItemUpdateAPI,  
    RFIDEventAPI  
)  
\# Modelos Internos/DB (para passar ao service)  
from .models import RFIDEvent as RFIDEventInternal

\# Repositórios e Serviços  
from .repository import StockItemRepository, get_stock_item_repository  
from .services import StockService, get_stock_service  
from app.modules.sales.repository import ProductRepository, get_product_repository \# Para enriquecer  
from app.modules.office.services_audit import AuditService, get_audit_service \# Para auditoria

stock_router \= APIRouter()

\# \--- Endpoints \---

@stock_router.post(  
    \\"/items/bulk\\",  
    response_model=BulkStockItemResponseAPI, \# Retorna resultado do bulk  
    status_code=status.HTTP_201_CREATED, \# Ou 207 se houver erros parciais  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"stock_manager\\"\]))\],  
    summary=\\"Register multiple stock items with RFID tags\\",  
    tags=\[\\"Stock & RFID\\"\]  
)  
async def register_stock_items_bulk(  
    request: Request,  
    payload: BulkStockItemCreateAPI, \# Receber a lista no payload  
    stock_service: StockService \= Depends(get_stock_service),  
    stock_repo: StockItemRepository \= Depends(get_stock_item_repository),  
    product_repo: ProductRepository \= Depends(get_product_repository), \# Para validação opcional no service  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"(Admin/Stock Manager Only) Registers or updates multiple stock items based on RFID tag ID.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    if not payload.items:  
        raise HTTPException(status_code=400, detail=\\"Request body 'items' cannot be empty.\\")  
    log.info(f\\"Endpoint: Registrando {len(payload.items)} itens de estoque em bulk...\\")

    try:  
        \# O serviço lida com a lógica de bulk write e auditoria  
        \# Passar a lista de modelos API para o service  
        result \= await stock_service.register_stock_items(  
            items_in=payload.items, \# Passar a lista de StockItemCreateAPI  
            stock_repo=stock_repo,  
            product_repo=product_repo,  
            audit_service=audit_service,  
            current_user=current_user  
        )  
        \# Service já logou auditoria  
        \# Decidir status code baseado nos erros? Ou sempre 201/207?  
        \# Manter 201 por simplicidade e reportar erros no corpo.  
        return result  
    except HTTPException as http_exc: \# Capturar erros de validação pré-bulk do service  
        raise http_exc  
    except Exception as e:  
        log.exception(\\"Erro inesperado durante registro bulk de estoque.\\")  
        await audit_service.log_audit_event(action=\\"stock_items_bulk_failed\\", status=\\"failure\\", request=request, current_user=current_user, error_message=f\\"Unexpected error: {e}\\", details={\\"item_count\\": len(payload.items)})  
        raise HTTPException(status_code=500, detail=\\"Internal server error during bulk registration.\\")

@stock_router.get(  
    \\"/items\\",  
    response_model=List\[StockItemAPI\],  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"stock_manager\\", \\"sales_rep\\", \\"support\\"\]))\], \# Ampliar quem pode ver?  
    summary=\\"List stock items with filters\\",  
    tags=\[\\"Stock & RFID\\"\]  
)  
async def list_stock_items_endpoint(  
    request: Request, \# Para auditoria opcional  
    status: Optional\[str\] \= Query(None, description=\\"Filter by status\\"),  
    product_id: Optional\[str\] \= Query(None, description=\\"Filter by product ID (ObjectId string)\\"),  
    location: Optional\[str\] \= Query(None, description=\\"Filter by location\\"),  
    rfid_tag_id: Optional\[str\] \= Query(None, description=\\"Filter by specific RFID tag\\"), \# Adicionar filtro por tag  
    skip: int \= Query(0, ge=0),  
    limit: int \= Query(100, ge=1, le=1000),  
    stock_service: StockService \= Depends(get_stock_service),  
    stock_repo: StockItemRepository \= Depends(get_stock_item_repository),  
    product_repo: ProductRepository \= Depends(get_product_repository), \# Para enriquecer  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria  
):  
    \\"\\"\\"Lists individual stock items with optional filters, enriched with product details.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Listando itens de estoque...\\")  
    \# Adicionar validação de status se usar Literal no modelo interno  
    \# if status and status not in STOCK_ITEM_STATUS.__args__: ...

    \# Passar rfid_tag_id para o service/repo  
    items \= await stock_service.list_stock_items(  
        stock_repo=stock_repo, product_repo=product_repo,  
        status=status, product_id_str=product_id, location=location,  
        rfid_tag_id_str=rfid_tag_id, \# \<\<\< Passar filtro de tag  
        skip=skip, limit=limit  
    )  
    \# Logar listagem (opcional)  
    \# await audit_service.log_audit_event(action=\\"stock_items_listed\\", ...)  
    return items

@stock_router.get(  
    \\"/items/{item_id}\\",  
    response_model=StockItemAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"stock_manager\\", \\"sales_rep\\", \\"support\\"\]))\],  
    summary=\\"Get a specific stock item by its internal ID\\",  
    tags=\[\\"Stock & RFID\\"\]  
)  
async def get_stock_item_endpoint(  
    request: Request, \# Auditoria opcional  
    item_id: str \= Path(..., description=\\"ID interno do Item de Estoque (ObjectId)\\"),  
    stock_service: StockService \= Depends(get_stock_service),  
    stock_repo: StockItemRepository \= Depends(get_stock_item_repository),  
    product_repo: ProductRepository \= Depends(get_product_repository),  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Retrieves details for a single stock item by its MongoDB ID.\\"\\"\\"  
    log \= logger.bind(item_id=item_id, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando item de estoque por ID interno...\\")  
    item \= await stock_service.get_stock_item(item_id, stock_repo, product_repo)  
    if not item:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Stock item not found\\")  
    \# Logar view?  
    \# await audit_service.log_audit_event(action=\\"stock_item_viewed\\", ...)  
    return item

@stock_router.get(  
    \\"/tags/{rfid_tag_id}\\",  
    response_model=StockItemAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"stock_manager\\", \\"sales_rep\\", \\"support\\"\]))\],  
    summary=\\"Get a specific stock item by its RFID tag ID\\",  
    tags=\[\\"Stock & RFID\\"\]  
)  
async def get_stock_item_by_rfid_endpoint(  
    request: Request,  
    rfid_tag_id: str \= Path(..., description=\\"ID da etiqueta RFID UHF\\"),  
    stock_repo: StockItemRepository \= Depends(get_stock_item_repository),  
    product_repo: ProductRepository \= Depends(get_product_repository), \# Para enriquecer  
    stock_service: StockService \= Depends(get_stock_service), \# Para enriquecer  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Retrieves details for a single stock item by its unique RFID tag ID.\\"\\"\\"  
    log \= logger.bind(rfid_tag=rfid_tag_id, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando item de estoque por tag RFID...\\")  
    \# Buscar direto do repo e enriquecer aqui ou no service? Service é melhor.  
    \# item_db \= await stock_repo.get_by_rfid_tag(rfid_tag_id)  
    \# if not item_db: raise HTTPException(404, \\"Stock item with this RFID tag not found\\")  
    \# item_api \= await stock_service._enrich_item(item_db, product_repo) \# Criar helper no service  
    \# Usando get_stock_item que busca por ID normal. Precisamos buscar por RFID e enriquecer.  
    item_db \= await stock_repo.get_by_rfid_tag(rfid_tag_id)  
    if not item_db: raise HTTPException(404, \\"Stock item with this RFID tag not found\\")  
    item_api \= await stock_service._enrich_item(item_db, product_repo) \# Criar _enrich_item no service  
    \# await audit_service.log_audit_event(action=\\"stock_item_viewed_by_rfid\\", ...)  
    return item_api

@stock_router.post(  
    \\"/events\\",  
    response_model=AcceptedResponse, \# Usar modelo comum  
    status_code=status.HTTP_202_ACCEPTED,  
    \# dependencies=\[Depends(require_role(\[\\"system\\", \\"rfid_reader\\"\]))\], \# Segurança via API Key ou Role? API Key é mais comum.  
    \# Adicionar dependência de API Key (criar em core/security?)  
    \# dependencies=\[Depends(verify_reader_api_key)\], \# Exemplo  
    summary=\\"Receive RFID read/event data from edge software\\",  
    tags=\[\\"Stock & RFID\\"\]  
)  
async def receive_rfid_event(  
    event: RFIDEventAPI, \# Receber modelo API  
    background_tasks: BackgroundTasks,  
    stock_service: StockService \= Depends(get_stock_service),  
    stock_repo: StockItemRepository \= Depends(get_stock_item_repository),  
    audit_service: AuditService \= Depends(get_audit_service)  
    \# Segurança: Como autenticar o leitor/edge software? API Key no header?  
    \# api_key: str \= Header(None, alias=\\"X-RFID-Reader-Key\\") \# Exemplo  
):  
    \\"\\"\\"  
    (Authenticated Reader Only) Receives events from RFID readers.  
    Processes the event asynchronously.  
    \\"\\"\\"  
    log \= logger.bind(event_type=event.event_type, tag_id=event.tag_id, reader_id=event.reader_id)  
    log.info(\\"Endpoint: Recebido evento RFID.\\")  
    \# TODO: Implementar autenticação do leitor/edge software aqui ou via Depends()

    \# Converter API model para Internal model se houver diferenças  
    event_internal \= RFIDEventInternal(\*\*event.model_dump())

    \# Adicionar tarefa ao background  
    background_tasks.add_task(  
        stock_service.process_rfid_event, \# Chamar a função do service  
        event=event_internal,  
        stock_repo=stock_repo,  
        audit_service=audit_service  
        \# Passar outras dependências que process_rfid_event possa precisar  
    )  
    return AcceptedResponse(message=\\"Event received and queued for processing.\\")

@stock_router.patch(  
    \\"/items/{item_id}\\",  
    response_model=StockItemAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"stock_manager\\"\]))\],  
    summary=\\"Manually update a stock item's status or location\\",  
    tags=\[\\"Stock & RFID\\"\]  
)  
async def update_stock_item_endpoint(  
    request: Request,  
    item_id: str \= Path(..., description=\\"ID Interno do Item (ObjectId string)\\"),  
    update_data: StockItemUpdateAPI, \# Modelo API  
    stock_repo: StockItemRepository \= Depends(get_stock_item_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user),  
    product_repo: ProductRepository \= Depends(get_product_repository), \# Para enriquecer  
    stock_service: StockService \= Depends(get_stock_service) \# Para enriquecer  
):  
    \\"\\"\\"(Admin/Stock Mgr Only) Manually updates status/location/metadata of a stock item.\\"\\"\\"  
    log \= logger.bind(item_id=item_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Atualizando item de estoque manualmente...\\")

    \# Validar status se fornecido  
    if update_data.status and update_data.status not in STOCK_ITEM_STATUS.__args__:  
         raise HTTPException(400, \\"Invalid status value\\")

    \# Buscar item antigo para log de auditoria  
    old_item_db \= await stock_repo.get_by_id(item_id)  
    if not old_item_db: raise HTTPException(status_code=404, detail=\\"Stock item not found\\")

    try:  
        \# Usar repo.update diretamente (service não tem lógica extra para PATCH manual)  
        updated_item_db \= await stock_repo.update(item_id, update_data.model_dump(exclude_unset=True))  
        if not updated_item_db: \# Não deveria acontecer se old_item_db foi encontrado  
             raise HTTPException(status_code=500, detail=\\"Failed to update stock item after finding it.\\")

        \# Logar auditoria  
        await audit_service.log_audit_event(  
            action=\\"stock_item_manually_updated\\", status=\\"success\\", entity_type=\\"StockItem\\", entity_id=item_id,  
            request=request, current_user=current_user,  
            details={\\"old_status\\": old_item_db.status, \\"old_location\\": old_item_db.location, \\"update_payload\\": update_data.model_dump(exclude_unset=True)}  
        )

        \# Enriquecer e retornar  
        return await stock_service._enrich_item(updated_item_db, product_repo) \# Usar helper

    except (ValueError, RuntimeError) as e:  
        log.error(f\\"Erro ao atualizar item de estoque {item_id}: {e}\\")  
        await audit_service.log_audit_event(action=\\"stock_item_manual_update_failed\\", status=\\"failure\\", ...)  
        raise HTTPException(status_code=500, detail=str(e))  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao atualizar item de estoque {item_id}\\")  
        await audit_service.log_audit_event(action=\\"stock_item_manual_update_failed\\", status=\\"failure\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Unexpected error updating stock item.\\")
