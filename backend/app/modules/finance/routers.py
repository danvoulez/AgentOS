\# agentos_core/app/modules/office/routers.py

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Path, Body  
from typing import List, Optional, Any  
from datetime import datetime  
from loguru import logger

\# Dependências Auth/Roles  
from app.core.security import CurrentUser, UserInDB, require_role

\# Modelos API  
from app.models.office import SettingAPI, SettingCreateAPI, SettingUpdateAPI, AuditLogAPI

\# Repositórios e Serviços  
from .repository import SettingRepository, AuditLogRepository, get_setting_repository, get_audit_log_repository  
from .services import OfficeService, get_office_service  
from .services_audit import AuditService, get_audit_service

\# Redis (para obter cliente para Service)  
from app.core.database import get_redis_client, Redis

office_router \= APIRouter()

\# \--- Endpoints de Settings \---

@office_router.get(  
    \\"/settings\\",  
    response_model=List\[SettingAPI\], \# Retorna lista do modelo API  
    dependencies=\[Depends(require_role(\[\\"admin\\"\]))\], \# Apenas Admin lista todas?  
    summary=\\"List all system settings\\",  
    tags=\[\\"Office & Admin \- Settings\\"\]  
)  
async def list_settings_endpoint(  
    request: Request, \# Para auditoria opcional  
    office_service: OfficeService \= Depends(get_office_service),  
    setting_repo: SettingRepository \= Depends(get_setting_repository),  
    audit_service: AuditService \= Depends(get_audit_service), \# Para log opcional  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para log  
):  
    \\"\\"\\"(Admin Only) Lists all system settings (sensitive values are masked).\\"\\"\\"  
    logger.debug(\\"Endpoint: Listando todas as configurações.\\")  
    settings_list \= await office_service.list_settings(setting_repo)  
    \# await audit_service.log_audit_event(action=\\"settings_listed\\", ...) \# Opcional  
    return settings_list

@office_router.get(  
    \\"/settings/{key}\\",  
    response_model=SettingAPI, \# Retorna modelo API  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"support\\"\]))\], \# Quem pode ver uma setting específica?  
    summary=\\"Get a specific system setting by key\\",  
    tags=\[\\"Office & Admin \- Settings\\"\]  
)  
async def get_setting_endpoint(  
    request: Request, \# Para auditoria opcional  
    key: str \= Path(..., description=\\"A chave única da configuração.\\"),  
    office_service: OfficeService \= Depends(get_office_service), \# Usa para buscar com cache  
    setting_repo: SettingRepository \= Depends(get_setting_repository),  
    redis_client: Optional\[Redis\] \= Depends(get_redis_client), \# Cache é opcional  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria  
):  
    \\"\\"\\"Retrieves a specific system setting by its key (sensitive value is masked).\\"\\"\\"  
    logger.debug(f\\"Endpoint: Buscando configuração por chave: {key}\\")  
    \# Service busca no cache/DB e lida com 'não encontrado' internamente? Não, repo busca.  
    setting_db \= await setting_repo.get_setting(key)  
    if not setting_db:  
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f\\"Setting '{key}' not found\\")

    setting_api \= SettingAPI.model_validate(setting_db)  
    \# Ofuscar valor aqui ANTES de retornar  
    if setting_api.is_sensitive:  
         setting_api.value \= \\"\*\*\*\*\*\\"

    \# await audit_service.log_audit_event(action=\\"setting_viewed\\", ...) \# Opcional  
    return setting_api

@office_router.put(  
    \\"/settings/{key}\\",  
    response_model=SettingAPI, \# Retorna modelo API  
    dependencies=\[Depends(require_role(\[\\"admin\\"\]))\], \# Apenas Admin cria/substitui  
    summary=\\"Create or replace a system setting\\",  
    tags=\[\\"Office & Admin \- Settings\\"\]  
)  
async def set_setting_endpoint(  
    request: Request, \# Para auditoria  
    key: str \= Path(..., description=\\"A chave única da configuração.\\"),  
    setting_in: SettingCreateAPI \= Body(...), \# Recebe modelo API  
    office_service: OfficeService \= Depends(get_office_service),  
    setting_repo: SettingRepository \= Depends(get_setting_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    redis_client: Optional\[Redis\] \= Depends(get_redis_client), \# Para cache  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria  
):  
    \\"\\"\\"(Admin Only) Creates a new setting or completely replaces an existing one.\\"\\"\\"  
    log \= logger.bind(setting_key=key, user_id=str(current_user.id))  
    if key \!= setting_in.key:  
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=\\"Key in URL must match key in payload.\\")

    log.info(\\"Endpoint: Criando ou substituindo configuração...\\")  
    try:  
        \# Passar modelo interno para o service? Ou service converte? Service converte.  
        \# O service lida com upsert, cache e auditoria  
        updated_setting \= await office_service.set_setting(  
            setting_data=setting_in, \# Passar modelo API  
            setting_repo=setting_repo,  
            audit_service=audit_service,  
            audit_repo=await get_audit_log_repository(), \# Passar repo de audit  
            current_user=current_user,  
            redis_client=redis_client,  
            request=request  
        )  
        \# Service já ofuscou e logou auditoria  
        return updated_setting  
    except HTTPException as http_exc:  
        raise http_exc \# Repassar erros 4xx/5xx do service  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao definir configuração '{key}'\\")  
        \# Logar auditoria de falha genérica  
        await audit_service.log_audit_event(action=\\"setting_set_failed\\", status=\\"failure\\", entity_id=key, error_message=f\\"Unexpected: {e}\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error setting configuration.\\")

@office_router.patch(  
    \\"/settings/{key}\\",  
    response_model=SettingAPI, \# Retorna modelo API  
    dependencies=\[Depends(require_role(\[\\"admin\\"\]))\], \# Apenas Admin atualiza  
    summary=\\"Update specific fields of a system setting\\",  
    tags=\[\\"Office & Admin \- Settings\\"\]  
)  
async def update_setting_fields_endpoint(  
    request: Request,  
    key: str \= Path(..., description=\\"A chave da configuração a ser atualizada.\\"),  
    setting_update: SettingUpdateAPI \= Body(...), \# Recebe modelo API  
    office_service: OfficeService \= Depends(get_office_service),  
    setting_repo: SettingRepository \= Depends(get_setting_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    redis_client: Optional\[Redis\] \= Depends(get_redis_client),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"(Admin Only) Updates specific fields (e.g., value, description) of an existing setting.\\"\\"\\"  
    log \= logger.bind(setting_key=key, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Atualizando campos da configuração...\\")  
    try:  
        \# Service lida com busca, update, cache e auditoria  
        updated_setting \= await office_service.update_setting_fields(  
            key=key,  
            setting_update=setting_update, \# Passar modelo API  
            setting_repo=setting_repo,  
            audit_service=audit_service,  
            audit_repo=await get_audit_log_repository(),  
            current_user=current_user,  
            redis_client=redis_client,  
            request=request  
        )  
         \# Service já ofuscou e logou auditoria  
        return updated_setting  
    except HTTPException as http_exc: \# Captura 404 Not Found do service  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao atualizar configuração '{key}'\\")  
        await audit_service.log_audit_event(action=\\"setting_update_failed\\", status=\\"failure\\", entity_id=key, error_message=f\\"Unexpected: {e}\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error updating configuration.\\")

@office_router.delete(  
    \\"/settings/{key}\\",  
    status_code=status.HTTP_204_NO_CONTENT,  
    dependencies=\[Depends(require_role(\[\\"admin\\"\]))\], \# Apenas Admin deleta  
    summary=\\"Delete a system setting\\",  
    tags=\[\\"Office & Admin \- Settings\\"\]  
)  
async def delete_setting_endpoint(  
    request: Request,  
    key: str \= Path(..., description=\\"A chave da configuração a ser deletada.\\"),  
    office_service: OfficeService \= Depends(get_office_service),  
    setting_repo: SettingRepository \= Depends(get_setting_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    redis_client: Optional\[Redis\] \= Depends(get_redis_client),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"(Admin Only) Deletes a system setting by its key.\\"\\"\\"  
    log \= logger.bind(setting_key=key, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Deletando configuração...\\")  
    try:  
        deleted \= await office_service.delete_setting(  
            key=key,  
            setting_repo=setting_repo,  
            audit_service=audit_service,  
            audit_repo=await get_audit_log_repository(),  
            current_user=current_user,  
            redis_client=redis_client,  
            request=request  
        )  
        if not deleted:  
            \# Service já logou falha na auditoria  
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f\\"Setting '{key}' not found or delete failed\\")  
        \# Retornar 204 automaticamente pelo FastAPI  
        return None  
    except HTTPException as http_exc:  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao deletar configuração '{key}'\\")  
        await audit_service.log_audit_event(action=\\"setting_delete_failed\\", status=\\"failure\\", entity_id=key, error_message=f\\"Unexpected: {e}\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error deleting configuration.\\")

\# \--- Endpoints de Audit Logs \---

@office_router.get(  
    \\"/audit-logs\\",  
    response_model=List\[AuditLogAPI\], \# Retorna modelo API  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"auditor\\"\]))\], \# Definir role 'auditor'?  
    summary=\\"List audit log entries\\",  
    tags=\[\\"Office & Admin \- Audit\\"\]  
)  
async def list_audit_logs_endpoint(  
    request: Request, \# Para auditoria da própria listagem (opcional)  
    \# Filtros  
    start_date: Optional\[datetime\] \= Query(None, description=\\"Filter by start date/time (ISO format)\\"),  
    end_date: Optional\[datetime\] \= Query(None, description=\\"Filter by end date/time (ISO format)\\"),  
    user_id: Optional\[str\] \= Query(None, description=\\"Filter by user ID (ObjectId string)\\"),  
    action: Optional\[str\] \= Query(None, description=\\"Filter by action name (e.g., 'order_created')\\"),  
    entity_type: Optional\[str\] \= Query(None, description=\\"Filter by entity type (e.g., 'Order')\\"),  
    entity_id: Optional\[str\] \= Query(None, description=\\"Filter by specific entity ID\\"),  
    status: Optional\[str\] \= Query(None, description=\\"Filter by status ('success' or 'failure')\\"),  
    ip_address: Optional\[str\] \= Query(None, description=\\"Filter by IP address\\"),  
    \# Paginação  
    skip: int \= Query(0, ge=0),  
    limit: int \= Query(100, ge=1, le=1000),  
    \# Dependências  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Para auditoria da listagem  
):  
    \\"\\"\\"(Admin/Auditor Only) Retrieves audit log entries with filtering and pagination.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Listando logs de auditoria...\\")  
    try:  
        \# Service busca os logs (repo já validado internamente)  
        logs \= await audit_service.list_audit_logs(  
            \# Passar filtros para o service  
            start_date=start_date, end_date=end_date, user_id_str=user_id, action=action,  
            entity_type=entity_type, entity_id=entity_id, status=status, ip_address=ip_address,  
            skip=skip, limit=limit  
        )  
        \# Logar a ação de visualização (cuidado com volume)  
        \# await audit_service.log_audit_event(action=\\"audit_logs_viewed\\", status=\\"success\\", request=request, current_user=current_user, details={\\"filter_count\\": len(logs), \\"limit\\": limit, \\"skip\\": skip})  
        return logs \# Service já retorna lista de modelos API  
    except Exception as e:  
        log.exception(\\"Erro inesperado ao listar logs de auditoria.\\")  
        raise HTTPException(status_code=500, detail=\\"Internal server error listing audit logs.\\")
