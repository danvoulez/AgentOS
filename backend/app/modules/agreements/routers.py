\# agentos_core/app/modules/tasks/routers.py

from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, Request \# Adicionar Request  
from typing import List, Optional  
from loguru import logger  
from datetime import date \# Para filtro de data

\# Dependências Auth/Roles  
from app.core.security import CurrentUser, UserInDB, require_role

\# Modelos API  
from app.models.tasks import Task as TaskAPI, TaskCreateAPI, TaskUpdateAPI

\# Modelos Internos/DB (para verificação de permissão)  
from .models import TaskInDB

\# Repositórios e Serviços  
from .repository import TaskRepository, get_task_repository  
from .services import TaskService, get_task_service  
from app.modules.people.repository import UserRepository, get_user_repository \# Para validar/enriquecer  
from app.modules.office.services_audit import AuditService, get_audit_service \# Para auditoria

tasks_router \= APIRouter()

\# Helper de Permissão  
def check_task_permission(task: TaskInDB, user: UserInDB, action: str \= \\"view\\"):  
    if not task or not user: return False  
    is_creator \= task.created_by \== user.id  
    is_assignee \= task.assigned_to and task.assigned_to \== user.id  
    is_admin \= \\"admin\\" in user.roles \# Ou manager?

    if action \== \\"view\\": return is_creator or is_assignee or is_admin  
    if action \== \\"update\\": return is_creator or is_assignee or is_admin \# Quem pode editar?  
    if action \== \\"delete\\": return is_creator or is_admin \# Quem pode deletar?  
    return False

\# \--- Endpoints \---

@tasks_router.post(  
    \\"/\\",  
    response_model=TaskAPI,  
    status_code=status.HTTP_201_CREATED,  
    summary=\\"Create a new task\\"  
    \# Qualquer usuário logado pode criar tarefa? Sim.  
)  
async def create_task_endpoint(  
    request: Request,  
    task_in: TaskCreateAPI, \# Recebe modelo API  
    task_service: TaskService \= Depends(get_task_service),  
    task_repo: TaskRepository \= Depends(get_task_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Criador  
):  
    \\"\\"\\"Creates a new task, optionally assigning it to a user.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.info(f\\"Endpoint: Criando nova tarefa '{task_in.title}'...\\")  
    try:  
        \# Service valida assignee, cria, audita, notifica (placeholder)  
        created_task_api \= await task_service.create_task(  
            task_in=task_in,  
            creator=current_user,  
            task_repo=task_repo,  
            user_repo=user_repo,  
            audit_service=audit_service  
        )  
        return created_task_api  
    except HTTPException as http_exc:  
        log.warning(f\\"Falha ao criar tarefa: {http_exc.detail}\\")  
        \# Auditoria feita no service se erro pego lá, senão logar aqui?  
        \# await audit_service.log_audit_event(action=\\"task_create_failed\\", status=\\"failure\\", ...)  
        raise http_exc  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao criar tarefa: {e}\\")  
        await audit_service.log_audit_event(action=\\"task_create_failed\\", status=\\"failure\\", ...)  
        raise HTTPException(status_code=500, detail=\\"Internal server error creating task.\\")

@tasks_router.get(  
    \\"/\\",  
    response_model=List\[TaskAPI\],  
    summary=\\"List tasks with filters\\"  
    \# Qualquer usuário logado pode listar, mas verá apenas as relevantes? Service filtra.  
)  
async def list_tasks_endpoint(  
    request: Request, \# Para auditoria opcional  
    \# Filtros  
    assignee_id: Optional\[str\] \= Query(None, description=\\"Filter by assigned user ID ('me' for current user)\\"),  
    created_by_id: Optional\[str\] \= Query(None, description=\\"Filter by creator user ID\\"),  
    status: Optional\[str\] \= Query(None, description=\\"Filter by status\\"),  
    priority: Optional\[str\] \= Query(None, description=\\"Filter by priority\\"),  
    due_before: Optional\[date\] \= Query(None, description=\\"Filter by due date before (YYYY-MM-DD)\\"),  
    due_after: Optional\[date\] \= Query(None, description=\\"Filter by due date after (YYYY-MM-DD)\\"),  
    tags: Optional\[List\[str\]\] \= Query(None, description=\\"Filter by tags (comma-separated in URL: ?tags=a\&tags=b)\\"),  
    \# Paginação  
    skip: int \= Query(0, ge=0),  
    limit: int \= Query(50, ge=1, le=200),  
    \# Dependências  
    task_service: TaskService \= Depends(get_task_service),  
    task_repo: TaskRepository \= Depends(get_task_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    audit_service: AuditService \= Depends(get_audit_service), \# Opcional para logar listagem  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Lists tasks based on various filter criteria, enriching with user details.\\"\\"\\"  
    log \= logger.bind(user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Listando tarefas...\\")

    assignee_filter_id \= None  
    if assignee_id:  
        assignee_filter_id \= str(current_user.id) if assignee_id.lower() \== \\"me\\" else assignee_id

    \# Validar status/priority (pode ser feito no service também)  
    if status and status not in TASK_STATUSES.__args__: raise HTTPException(400, \\"Invalid status value\\")  
    if priority and priority not in TASK_PRIORITIES.__args__: raise HTTPException(400, \\"Invalid priority value\\")

    tasks_api \= await task_service.list_tasks(  
        task_repo=task_repo, user_repo=user_repo,  
        assignee_id_str=assignee_filter_id, created_by_str=created_by_id,  
        status=status, priority=priority,  
        due_before_str=due_before.isoformat() if due_before else None, \# Passar como string  
        due_after_str=due_after.isoformat() if due_after else None, \# Passar como string  
        tags=tags, skip=skip, limit=limit  
    )  
    \# Logar listagem? (Opcional)  
    \# await audit_service.log_audit_event(action=\\"tasks_listed\\", ...)  
    return tasks_api

@tasks_router.get(  
    \\"/{task_id}\\",  
    response_model=TaskAPI,  
    summary=\\"Get a specific task by ID\\"  
    \# Permissão verificada no código  
)  
async def get_task_endpoint(  
    request: Request,  
    task_id: str \= Path(..., description=\\"ID da Tarefa (ObjectId)\\"),  
    task_service: TaskService \= Depends(get_task_service), \# Para buscar e enriquecer  
    task_repo: TaskRepository \= Depends(get_task_repository), \# Passado para o service  
    user_repo: UserRepository \= Depends(get_user_repository), \# Passado para o service  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user)  
):  
    \\"\\"\\"Retrieves details for a specific task, checking permissions.\\"\\"\\"  
    log \= logger.bind(task_id=task_id, user_id=str(current_user.id))  
    log.debug(\\"Endpoint: Buscando tarefa por ID...\\")

    \# Buscar via Repo primeiro para checar permissão no objeto DB  
    task_db \= await task_repo.get_by_id(task_id)  
    if not task_db: raise HTTPException(status_code=404, detail=\\"Task not found\\")

    \# Verificar permissão  
    if not check_task_permission(task_db, current_user, action=\\"view\\"):  
         await audit_service.log_audit_event(action=\\"task_view_denied\\", ...)  
         raise HTTPException(status_code=403, detail=\\"Not authorized to view this task\\")

    \# Enriquecer usando o service  
    task_api \= await task_service._enrich_task(task_db, user_repo)  
    return task_api

@tasks_router.patch(  
    \\"/{task_id}\\",  
    response_model=TaskAPI,  
    summary=\\"Update a task\\"  
    \# Permissão verificada no código  
)  
async def update_task_endpoint(  
    request: Request,  
    task_id: str \= Path(..., description=\\"ID da Tarefa a ser atualizada\\"),  
    task_update: TaskUpdateAPI, \# Recebe modelo API  
    task_service: TaskService \= Depends(get_task_service),  
    task_repo: TaskRepository \= Depends(get_task_repository),  
    user_repo: UserRepository \= Depends(get_user_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Quem está atualizando  
):  
    \\"\\"\\"Updates specific fields of an existing task.\\"\\"\\"  
    log \= logger.bind(task_id=task_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Atualizando tarefa...\\")

    \# Service busca, valida permissão (via check_task_permission), atualiza e audita  
    try:  
        \# Passar modelo API para o service, que converterá para interno  
        updated_task_api \= await task_service.update_task(  
            task_id_str=task_id,  
            task_update=task_update,  
            updater=current_user,  
            task_repo=task_repo,  
            user_repo=user_repo,  
            audit_service=audit_service  
        )  
        return updated_task_api  
    except HTTPException as http_exc: \# Capturar 403, 404, 400, 500 do service  
         log.warning(f\\"Falha ao atualizar tarefa: {http_exc.detail}\\")  
         \# Auditoria já logada no service  
         raise http_exc  
    except Exception as e:  
         log.exception(f\\"Erro inesperado ao atualizar tarefa {task_id}\\")  
         await audit_service.log_audit_event(action=\\"task_update_failed\\", status=\\"failure\\", ...)  
         raise HTTPException(status_code=500, detail=\\"Internal server error updating task.\\")

@tasks_router.delete(  
    \\"/{task_id}\\",  
    status_code=status.HTTP_204_NO_CONTENT,  
    dependencies=\[Depends(require_role(\[\\"admin\\"\]))\], \# \<\<\< Apenas Admin deleta? Ou criador? Ajustar.  
    summary=\\"Delete a task\\"  
)  
async def delete_task_endpoint(  
    request: Request,  
    task_id: str \= Path(..., description=\\"ID da Tarefa a ser deletada\\"),  
    task_service: TaskService \= Depends(get_task_service),  
    task_repo: TaskRepository \= Depends(get_task_repository),  
    audit_service: AuditService \= Depends(get_audit_service),  
    current_user: UserInDB \= Depends(get_current_active_user) \# Quem está deletando  
):  
    \\"\\"\\"(Admin Only) Deletes a task permanently.\\"\\"\\"  
    log \= logger.bind(task_id=task_id, user_id=str(current_user.id))  
    log.info(\\"Endpoint: Deletando tarefa...\\")

    \# Opcional: Verificar permissão de criador aqui se não usar require_role(\\"admin\\")  
    \# task_db \= await task_repo.get_by_id(task_id)  
    \# if not task_db: raise HTTPException(404)  
    \# if not check_task_permission(task_db, current_user, 'delete'): raise HTTPException(403)

    try:  
        deleted \= await task_service.delete_task(  
            task_id_str=task_id,  
            deleter=current_user,  
            task_repo=task_repo,  
            audit_service=audit_service  
        )  
        if not deleted:  
            \# Service já logou falha de auditoria se não encontrou  
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Task not found or delete failed\\")

        \# Retornar 204 automaticamente pelo FastAPI  
        return None  
    except HTTPException as http_exc:  
        raise http_exc \# Repassar erros já formatados pelo service (raro aqui)  
    except Exception as e:  
        log.exception(f\\"Erro inesperado ao deletar tarefa {task_id}\\")  
        await audit_service.log_audit_event(action=\\"task_delete_failed\\", status=\\"failure\\", entity_type=\\"Task\\", entity_id=task_id, request=request, current_user=current_user, error_message=f\\"Unexpected error: {e}\\")  
        raise HTTPException(status_code=500, detail=\\"Internal server error deleting task.\\")

\# Importar date para Query  
from datetime import date
