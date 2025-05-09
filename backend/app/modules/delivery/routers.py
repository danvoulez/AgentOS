\# agentos_core/app/modules/agreements/routers.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request, Body \# Adicionar Request, Body  
from typing import List, Optional  
from loguru import logger

\# Dependências Auth/Roles  
from app.core.security import CurrentUser, UserInDB, require_role \# Usar UserInDB

\# Modelos API  
from app.models.agreements import Agreement as AgreementAPI, AgreementCreateAPI, AgreementUpdateAPI, ConversationListItem \# Ajustar nome ConversationListItem? Não pertence aqui. Usar um modelo específico de lista.  
from app.models.api_common import DetailResponse \# Para erros

\# Modelos Internos/DB (para verificação de permissão)  
from .models import AgreementInDB

\# Repositórios e Serviços  
from .repository import AgreementRepository, get_agreement_repository  
from .services import AgreementService, get_agreement_service  
from app.modules.people.repository import UserRepository, get_user_repository \# Para validar/enriquecer  
from app.core.counters import CounterService, get_counter_service \# Para criar  
from app.modules.office.services_audit import AuditService, get_audit_service \# Para auditoria

agreement_router \= APIRouter()

\# Helper de Permissão (interno ao router ou movido para service/utils)  
def check_agreement_permission(agreement: AgreementInDB, user: UserInDB, action: str \= \\"view\\") \-\> bool:  
    if not agreement or not user: return False  
    is_creator \= agreement.created_by \== user.id  
    \# Verificar se o ID do usuário está na lista de ObjectIds de testemunhas  
    is_witness \= user.id in agreement.witness_ids  
    is_admin \= \\"admin\\" in user.roles

    if action \== \\"view\\":  
        return is_creator or is_witness or is_admin  
    elif action \== \\"accept\\":  
        \# Apenas testemunha listada E acordo pendente E testemunha ainda não aceitou  
        if not is_witness or agreement.status \!= \\"pending\\": return False  
        witness_status_entry \= next((ws for ws in agreement.witness_status if ws.witness_id \== user.id), None)  
        return witness_status_entry is not None and not witness_status_entry.accepted  
    elif action \== \\"conclude\\" or action \== \\"dispute\\":  
        \# Apenas criador ou admin, e acordo precisa estar pendente ou aceito?  
        return (is_creator or is_admin) and agreement.status in \[\\"pending\\", \\"accepted\\"\]  
    return False

\# \--- Endpoints \---

@agreement_router.post(  
    \\"/\\",  
    response_model=AgreementAPI, \# Retorna modelo API enriquecido  
    status_code=status.HTTP_201_CREATED,  
    summary=\\"Create a new agreement\\",  
    tags=\[\\"Agreements\\"\]  
    \# Sem require_role aqui? Qualquer usuário logado pode criar? Sim.  
)  
async def create_agreement_endpoint(  
    request: Request, \# Para auditoria  
    agreement_in: AgreementCreateAPI, \# Recebe modelo API  
    agreement_service: AgreementService \= Depends(get_agreement_service),  
    agreement_repo: AgreementRepository \= Depends(get_agreement_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    counter_service: CounterService \= Depends(get_counter_service),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Criador  
):  
    \\"\\"\\"Creates a new agreement, requiring at least one valid witness.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.info(\\"Endpoint: Criando novo acordo...\\")  
    try:  
        \# Service lida com validação de testemunhas, criação, auditoria, notificação (placeholder)  
        created_agreement_api \= await agreement_service.create_agreement(  
            agreement_in=agreement_in,  
            creator=current_user,  
            agreement_repo=agreement_repo,  
            user_repo=user_repo,  
            counter_service=counter_service,  
            audit_service=audit_service,  
        )  
        return created_agreement_api  
    except HTTPException as http_exc: \# Capturar erros 4xx (ex: testemunha inválida)  
        log.warning(f\\"Falha ao criar acordo: {http_exc.detail} (Status: {http_exc.status_code})\\")  
        \# Auditoria de falha já deve ter sido logada no service se o erro foi pego lá  
        \# Se o erro for levantado aqui (ex: permissão futura), logar aqui.  
        raise http_exc  
    except Exception as e: \# Capturar erros 5xx inesperados  
        log.exception(f\\"Erro inesperado ao criar acordo: {e}\\")  
        \# Logar auditoria de falha genérica?  
        await audit_service.log_audit_event(  
            action=\\"agreement_create_failed\\", status=\\"failure\\", entity_type=\\"Agreement\\",  
            request=request, current_user=current_user, error_message=f\\"Unexpected error: {e}\\",  
            details=agreement_in.model_dump()  
        )  
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=\\"Internal server error creating agreement.\\")

@agreement_router.get(  
    \\"/\\",  
    response_model=List\[AgreementAPI\], \# Retorna lista de modelos API enriquecidos  
    summary=\\"List agreements for the current user\\",  
    tags=\[\\"Agreements\\"\]  
    \# Qualquer usuário logado pode listar os seus  
)  
async def list_my_agreements_endpoint(  
    request: Request, \# Para auditoria (opcional em listagem)  
    status: Optional\[str\] \= Query(None, description=f\\"Filter by status (e.g., {list(AGREEMENT_STATUSES.__args__)})\\"),  
    tags: Optional\[List\[str\]\] \= Query(None, description=\\"Filter by tags\\"),  
    skip: int \= Query(0, ge=0),  
    limit: int \= Query(50, ge=1, le=200),  
    agreement_service: AgreementService \= Depends(get_agreement_service),  
    agreement_repo: AgreementRepository \= Depends(get_agreement_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Para enriquecer  
    audit_service: AuditService \= Depends(get_audit_service), \# Para auditoria (opcional)  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Lists agreements where the current user is either the creator or a witness.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Listando acordos do usuário...\\")  
    \# Validar status se fornecido  
    if status and status not in AGREEMENT_STATUSES.__args__:  
        raise HTTPException(status_code=400, detail=\\"Invalid status filter value.\\")

    \# Service lida com a busca e enriquecimento  
    agreements \= await agreement_service.list_agreements_for_user(  
        user=current_user,  
        agreement_repo=agreement_repo,  
        user_repo=user_repo,  
        status=status,  
        tags=tags,  
        skip=skip,  
        limit=limit  
    )  
    \# Logar auditoria de listagem (opcional, pode ser ruidoso)  
    \# await audit_service.log_audit_event(action=\\"agreements_listed\\", status=\\"success\\", ..., details={\\"filter_status\\": status, \\"count\\": len(agreements)})  
    return agreements

@agreement_router.get(  
    \\"/{agreement_id}\\",  
    response_model=AgreementAPI,  
    summary=\\"Get a specific agreement by ID\\",  
    tags=\[\\"Agreements\\"\]  
    \# Permissão verificada no service/endpoint  
)  
async def get_agreement_endpoint(  
    request: Request, \# Para auditoria  
    agreement_id: str \= Path(..., description=\\"ID do Acordo (ObjectId)\\"),  
    agreement_service: AgreementService \= Depends(get_agreement_service), \# Para buscar/enriquecer/checar permissão  
    agreement_repo: AgreementRepository \= Depends(get_agreement_repository), \# Passado para o service  
    user_repo: UserRepository \= Depends(get_user_repository), \# Passado para o service  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Retrieves a specific agreement by its ID, checking user authorization.\\"\\"\\"  
    log \= logger.bind(agreement_id=agreement_id, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando acordo por ID...\\")  
    try:  
        \# Service busca, valida permissão e enriquece  
        agreement_api \= await agreement_service.get_agreement(  
            agreement_id_str=agreement_id,  
            requester=current_user,  
            agreement_repo=agreement_repo,  
            user_repo=user_repo  
        )  
        \# Logar visualização (opcional)  
        \# await audit_service.log_audit_event(action=\\"agreement_viewed\\", ...)  
        return agreement_api  
    except HTTPException as http_exc: \# Captura 404, 403 do service  
        log.warning(f\\"Falha ao buscar acordo: {http_exc.detail} (Status: {http_exc.status_code})\\")  
        \# Logar falha de auditoria se for 403  
        if http_exc.status_code \== 403:  
             await audit_service.log_audit_event(  
                 action=\\"agreement_view_denied\\", status=\\"failure\\", entity_type=\\"Agreement\\", entity_id=agreement_id,  
                 request=request, current_user=current_user, error_message=http_exc.detail  
             )  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao buscar acordo {agreement_id}: {e}\\")  
        await audit_service.log_audit_event(action=\\"agreement_view_failed\\", status=\\"failure\\", entity_id=agreement_id, error_message=str(e), ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error retrieving agreement.\\")

@agreement_router.patch(  
    \\"/{agreement_id}/accept\\",  
    response_model=AgreementAPI,  
    summary=\\"Accept an agreement as a witness\\",  
    tags=\[\\"Agreements\\"\]  
    \# Requer apenas usuário logado, service valida se é testemunha correta  
)  
async def accept_agreement_endpoint(  
    request: Request,  
    agreement_id: str \= Path(..., description=\\"ID do Acordo a ser aceito\\"),  
    agreement_service: AgreementService \= Depends(get_agreement_service),  
    agreement_repo: AgreementRepository \= Depends(get_agreement_repository),  
    user_repo: UserRepository \= Depends(get_user_repository), \# Para enriquecer  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# A testemunha logada  
):  
    \\"\\"\\"Allows a listed witness to accept a pending agreement.\\"\\"\\"  
    log \= logger.bind(agreement_id=agreement_id, witness_id=str(current_user.id))  
    log.info(\\"Endpoint: Aceitando acordo como testemunha...\\")  
    try:  
        \# Service lida com validação, atualização e auditoria  
        accepted_agreement_api \= await agreement_service.accept_agreement(  
            agreement_id_str=agreement_id,  
            witness=current_user,  
            agreement_repo=agreement_repo,  
            user_repo=user_repo, \# Passar para enriquecer retorno  
            audit_service=audit_service  
        )  
        return accepted_agreement_api  
    except HTTPException as http_exc: \# Captura 400, 403, 404, 500 do service  
        log.warning(f\\"Falha ao aceitar acordo: {http_exc.detail} (Status: {http_exc.status_code})\\")  
        \# Auditoria de falha já logada no service  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao aceitar acordo {agreement_id}: {e}\\")  
        \# Logar auditoria de falha genérica?  
        await audit_service.log_audit_event(action=\\"agreement_accept_failed\\", status=\\"failure\\", entity_id=agreement_id, error_message=f\\"Unexpected: {e}\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error accepting agreement.\\")

@agreement_router.patch(  
    \\"/{agreement_id}/conclude\\",  
    response_model=AgreementAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\", \\"creator\\"\]))\], \# \<\<\< Definir quem pode: admin ou criador? Ajustar roles.  
    summary=\\"Mark an agreement as concluded\\",  
    tags=\[\\"Agreements\\"\]  
)  
async def conclude_agreement_endpoint(  
    request: Request,  
    agreement_id: str \= Path(..., description=\\"ID do Acordo a ser concluído\\"),  
    payload: AgreementUpdateAPI \= Body({}, description=\\"Opcional: Adicionar notas de resolução.\\"), \# Usar modelo API, mas só notas são relevantes  
    agreement_service: AgreementService \= Depends(get_agreement_service),  
    agreement_repo: AgreementRepository \= Depends(get_agreement_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"(Admin/Creator Only) Marks an agreement as successfully concluded.\\"\\"\\"  
    log \= logger.bind(agreement_id=agreement_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Concluindo acordo...\\")  
    try:  
        \# Service valida permissão (creator/admin) e status antes de atualizar e logar auditoria  
        concluded_agreement_api \= await agreement_service.conclude_or_dispute_agreement(  
            agreement_id_str=agreement_id,  
            action_user=current_user,  
            new_status=\\"concluded\\",  
            notes=payload.resolution_notes,  
            agreement_repo=agreement_repo,  
            user_repo=user_repo,  
            audit_service=audit_service  
        )  
        return concluded_agreement_api  
    except HTTPException as http_exc:  
        log.warning(f\\"Falha ao concluir acordo: {http_exc.detail} (Status: {http_exc.status_code})\\")  
        \# Auditoria já logada no service  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao concluir acordo {agreement_id}: {e}\\")  
        await audit_service.log_audit_event(action=\\"agreement_conclude_failed\\", status=\\"failure\\", entity_id=agreement_id, error_message=f\\"Unexpected: {e}\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error concluding agreement.\\")

@agreement_router.patch(  
    \\"/{agreement_id}/dispute\\",  
    response_model=AgreementAPI,  
    dependencies=\[Depends(require_role(\[\\"admin\\"\]))\], \# \<\<\< Apenas Admin pode marcar como disputado?  
    summary=\\"Mark an agreement as disputed\\",  
    tags=\[\\"Agreements\\"\]  
)  
async def dispute_agreement_endpoint(  
    request: Request,  
    agreement_id: str \= Path(..., description=\\"ID do Acordo a ser disputado\\"),  
    payload: AgreementUpdateAPI \= Body(..., description=\\"Notas explicando a disputa são recomendadas.\\"),  
    agreement_service: AgreementService \= Depends(get_agreement_service),  
    agreement_repo: AgreementRepository \= Depends(get_agreement_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"(Admin Only) Marks an agreement as disputed, requiring further action.\\"\\"\\"  
    log \= logger.bind(agreement_id=agreement_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Marcando acordo como disputado...\\")  
    try:  
        \# Service valida permissão (admin) e status antes de atualizar e logar auditoria  
        disputed_agreement_api \= await agreement_service.conclude_or_dispute_agreement(  
            agreement_id_str=agreement_id,  
            action_user=current_user,  
            new_status=\\"disputed\\",  
            notes=payload.resolution_notes, \# Passar notas  
            agreement_repo=agreement_repo,  
            user_repo=user_repo,  
            audit_service=audit_service  
        )  
        return disputed_agreement_api  
    except HTTPException as http_exc:  
        log.warning(f\\"Falha ao disputar acordo: {http_exc.detail} (Status: {http_exc.status_code})\\")  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao disputar acordo {agreement_id}: {e}\\")  
        await audit_service.log_audit_event(action=\\"agreement_dispute_failed\\", status=\\"failure\\", entity_id=agreement_id, error_message=f\\"Unexpected: {e}\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error disputing agreement.\\")

\# Importar Literal para status  
from typing import Literal  
\# Importar asyncio para notificações (se implementadas no service)  
import asyncio
