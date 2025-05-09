\# agentos_core/app/modules/tasks/services.py

from typing import Optional, List, Dict, Any, Literal \# Adicionar Literal  
from datetime import datetime, date \# Adicionar date  
from bson import ObjectId  
from fastapi import HTTPException, status  
from loguru import logger  
from pydantic import BaseModel

\# Repositórios e Modelos Internos/DB  
from .repository import TaskRepository  
from .models import TaskInDB, TaskCreateInternal, TaskUpdateInternal, TASK_STATUSES, TASK_PRIORITIES \# Usar nomes internos  
\# Modelos API (para tipo de retorno)  
from app.models.tasks import Task, TaskCreateAPI, TaskUpdateAPI

\# Repositório de Usuários (para buscar nomes e validar)  
from app.modules.people.repository import UserRepository  
from app.modules.people.models import UserInDB \# Para info do usuário

\# Serviços Core e de Auditoria  
from app.modules.office.services_audit import AuditService

\# Notificações (Placeholder)  
async def notify_assignee_of_task(task_title: str, assignee_id: ObjectId):  
    logger.info(f\\"Placeholder: Notificando usuário {assignee_id} sobre nova tarefa '{task_title}'\\")  
    await asyncio.sleep(0.1)

class TaskService:  
    \\"\\"\\"Lógica de negócio para Tarefas.\\"\\"\\"

    \# Helper para enriquecer (similar ao de Agreements)  
    async def _enrich_task(self, task_db: TaskInDB, user_repo: UserRepository) \-\> Task:  
        \\"\\"\\"Adiciona nomes do criador e responsável.\\"\\"\\"  
        task_api \= Task.model_validate(task_db)  
        user_ids_to_fetch \= {task_db.created_by}  
        if task_db.assigned_to:  
            user_ids_to_fetch.add(task_db.assigned_to)

        if not user_ids_to_fetch: return task_api \# Segurança

        users \= await user_repo.list_by({\\"_id\\": {\\"$in\\": list(user_ids_to_fetch)}})  
        user_map \= {str(u.id): u for u in users}

        creator \= user_map.get(str(task_db.created_by))  
        task_api.created_by_details \= {\\"id\\": str(task_db.created_by), \\"name\\": f\\"{creator.profile.first_name or ''} {creator.profile.last_name or ''}\\".strip() if creator else \\"Usuário Desconhecido\\"}

        if task_db.assigned_to:  
            assignee \= user_map.get(str(task_db.assigned_to))  
            task_api.assigned_to_details \= {\\"id\\": str(task_db.assigned_to), \\"name\\": f\\"{assignee.profile.first_name or ''} {assignee.profile.last_name or ''}\\".strip() if assignee else \\"Usuário Desconhecido\\"}

        return task_api

    async def create_task(  
        self,  
        task_in: TaskCreateAPI, \# Recebe modelo API  
        creator: UserInDB, \# Usuário logado  
        task_repo: TaskRepository,  
        user_repo: UserRepository, \# Para validar assignee  
        audit_service: AuditService,  
    ) \-\> Task: \# Retorna modelo API  
        \\"\\"\\"Cria uma nova tarefa, validando assignee e logando.\\"\\"\\"  
        log \= logger.bind(creator_id=str(creator.id), title=task_in.title)  
        log.info(\\"Service: Criando nova tarefa...\\")

        \# Preparar dados internos  
        task_internal_data \= TaskCreateInternal(  
            title=task_in.title,  
            description=task_in.description,  
            priority=task_in.priority,  
            due_date=datetime.strptime(task_in.due_date_str, '%Y-%m-%d').date() if task_in.due_date_str else None, \# Converter string para date  
            related_entity_type=task_in.related_entity_type,  
            related_entity_id=task_in.related_entity_id,  
            source_context=task_in.source_context,  
            tags=task_in.tags or \[\],  
            created_by=creator.id \# ID do criador  
            \# assigned_to será validado e adicionado abaixo  
        )

        \# Validar assignee se fornecido  
        assignee_id_obj: Optional\[ObjectId\] \= None  
        if task_in.assigned_to_id:  
             assignee_id_obj \= task_repo._to_objectid(task_in.assigned_to_id)  
             if not assignee_id_obj: raise HTTPException(400, \\"Invalid assigned_to_id format\\")  
             assignee \= await user_repo.get_by_id(assignee_id_obj)  
             if not assignee or not assignee.is_active:  
                  raise HTTPException(404, f\\"Assigned user {task_in.assigned_to_id} not found or inactive.\\")  
             task_internal_data.assigned_to \= assignee_id_obj \# Adiciona ObjectId validado

        \# Criar no repositório  
        try:  
            \# Repo.create espera Dict, converter modelo interno  
            created_db \= await task_repo.create(task_internal_data.model_dump())  
            log.success(f\\"Tarefa ID {created_db.id} criada.\\")

            \# Logar auditoria  
            await audit_service.log_audit_event(  
                 action=\\"task_created\\", status=\\"success\\", entity_type=\\"Task\\",  
                 entity_id=created_db.id, audit_repo=None,  
                 details=created_db.model_dump(mode='json'), \# Logar dados completos  
                 current_user=creator  
            )

            \# Notificar assignee (assíncrono)  
            if assignee_id_obj:  
                asyncio.create_task(notify_assignee_of_task(created_db.title, assignee_id_obj))

            \# Enriquecer e retornar modelo API  
            return await self._enrich_task(created_db, user_repo)

        except (ValueError, RuntimeError) as e:  
             logger.exception(f\\"Falha ao criar tarefa no DB: {e}\\")  
             \# Auditoria de falha pode ser feita no router que captura a exceção final  
             raise HTTPException(status_code=500, detail=f\\"Could not create task: {e}\\")

    async def update_task(  
        self,  
        task_id_str: str,  
        task_update: TaskUpdateAPI, \# Modelo API  
        updater: UserInDB, \# Usuário logado  
        task_repo: TaskRepository,  
        user_repo: UserRepository,  
        audit_service: AuditService,  
    ) \-\> Task: \# Retorna modelo API  
        \\"\\"\\"Atualiza uma tarefa existente, validando e logando.\\"\\"\\"  
        log \= logger.bind(task_id=task_id_str, user_id=str(updater.id))  
        log.info(\\"Service: Atualizando tarefa...\\")

        task_id \= task_repo._to_objectid(task_id_str)  
        if not task_id: raise HTTPException(400, \\"Invalid task ID format\\")

        \# Buscar tarefa antiga para log e validações  
        old_task \= await task_repo.get_by_id(task_id)  
        if not old_task: raise HTTPException(404, \\"Task not found\\")

        \# Verificar permissão de update (service ou router?) \- Router é melhor para consistência  
        \# if not check_task_permission(old_task, updater, 'update'): raise HTTPException(403, ...)

        \# Preparar dados internos para update  
        update_internal \= TaskUpdateInternal(  
             \*\*(task_update.model_dump(exclude_unset=True)) \# Passa apenas campos fornecidos  
        )  
        \# Validar e converter assignee_id se presente  
        if update_internal.assigned_to_id is not None: \# Permite passar null para desatribuir  
             assignee_id_obj \= task_repo._to_objectid(update_internal.assigned_to_id)  
             if not assignee_id_obj: raise HTTPException(400, \\"Invalid assigned_to_id format\\")  
             assignee \= await user_repo.get_by_id(assignee_id_obj)  
             if not assignee or not assignee.is_active: raise HTTPException(404, f\\"New assigned user not found or inactive.\\")  
             update_internal.assigned_to \= assignee_id_obj \# Usa ObjectId  
        \# Converter due_date_str para date  
        if update_internal.due_date_str is not None:  
            try: update_internal.due_date \= datetime.strptime(update_internal.due_date_str, '%Y-%m-%d').date()  
            except ValueError: raise HTTPException(400, \\"Invalid due_date_str format.\\")  
        elif task_update.model_dump(exclude_unset=True).get('due_date_str') is None and 'due_date_str' in task_update.model_dump(exclude_unset=True):  
             update_internal.due_date \= None \# Permitir remover data

        update_data_dict \= update_internal.model_dump(exclude_unset=True, exclude={'assigned_to_id', 'due_date_str'}) \# Excluir campos string

        \# Lidar com completed_at baseado no status  
        new_status \= update_data_dict.get(\\"status\\")  
        if new_status and new_status \!= old_task.status:  
            if new_status \== \\"completed\\": update_data_dict\[\\"completed_at\\"\] \= datetime.utcnow()  
            else: update_data_dict\[\\"completed_at\\"\] \= None \# Limpar se reabrir

        \# Chamar repo update  
        try:  
            updated_db \= await task_repo.update(task_id, update_data_dict)  
            if not updated_db:  
                 raise HTTPException(status_code=404, detail=\\"Task not found or update failed.\\") \# 404 se repo retornou None

            task_api \= await self._enrich_task(updated_db, user_repo)  
            log.success(f\\"Tarefa ID {task_id_str} atualizada.\\")

            \# Logar auditoria  
            await audit_service.log_audit_event(  
                 action=\\"task_updated\\", status=\\"success\\", entity_type=\\"Task\\",  
                 entity_id=task_api.id, audit_repo=None,  
                 details={\\"update_payload\\": task_update.model_dump(exclude_unset=True)}, \# Logar o que foi enviado  
                 current_user=updater  
            )  
            \# Notificar se assignee mudou?  
            \# if \\"assigned_to\\" in update_data_dict and old_task.assigned_to \!= update_data_dict\[\\"assigned_to\\"\]: ...

            return task_api  
        except (ValueError, RuntimeError) as e:  
            logger.exception(f\\"Falha ao atualizar tarefa {task_id}: {e}\\")  
            \# Auditoria de falha feita no router  
            raise HTTPException(status_code=500, detail=f\\"Could not update task: {e}\\")

    async def get_task(self, task_id_str: str, task_repo: TaskRepository, user_repo: UserRepository) \-\> Optional\[Task\]:  
         \\"\\"\\"Busca uma tarefa e enriquece com nomes.\\"\\"\\"  
         log \= logger.bind(task_id=task_id_str)  
         log.debug(\\"Service: Buscando tarefa por ID...\\")  
         task_db \= await task_repo.get_by_id(task_id_str)  
         if not task_db:  
             log.info(\\"Tarefa não encontrada.\\")  
             return None  
         return await self._enrich_task(task_db, user_repo)

    async def list_tasks(  
        self,  
        task_repo: TaskRepository,  
        user_repo: UserRepository,  
        \# Filtros  
        assignee_id_str: Optional\[str\] \= None,  
        created_by_str: Optional\[str\] \= None,  
        status: Optional\[str\] \= None,  
        priority: Optional\[str\] \= None,  
        due_before_str: Optional\[str\] \= None, \# Receber como string  
        due_after_str: Optional\[str\] \= None,  \# Receber como string  
        tags: Optional\[List\[str\]\] \= None,  
        skip: int \= 0,  
        limit: int \= 100  
    ) \-\> List\[Task\]:  
        \\"\\"\\"Lista tarefas com filtros e enriquece com nomes.\\"\\"\\"  
        log \= logger.bind(service=\\"TaskService\\")  
        log.debug(\\"Service: Listando tarefas com filtros...\\")

        \# Converter filtros de data string para date  
        due_before \= datetime.strptime(due_before_str, '%Y-%m-%d').date() if due_before_str else None  
        due_after \= datetime.strptime(due_after_str, '%Y-%m-%d').date() if due_after_str else None

        \# Chamar repo com IDs string (repo converte para ObjectId)  
        tasks_db \= await task_repo.list_tasks_by_filter(  
            status=status, priority=priority, assigned_to_str=assignee_id_str,  
            created_by_str=created_by_str, due_before=due_before, due_after=due_after,  
            tags=tags, skip=skip, limit=limit  
        )  
        enriched_tasks \= \[await self._enrich_task(t, user_repo) for t in tasks_db\]  
        log.info(f\\"Retornando {len(enriched_tasks)} tarefas.\\")  
        return enriched_tasks

    async def delete_task(  
        self,  
        task_id_str: str,  
        task_repo: TaskRepository,  
        \# audit_service: AuditService, \# Log feito no Router  
        \# current_user: UserInDB  
    ) \-\> bool:  
         \\"\\"\\"Deleta uma tarefa.\\"\\"\\"  
         log \= logger.bind(task_id=task_id_str)  
         log.info(\\"Service: Deletando tarefa...\\")  
         deleted \= await task_repo.delete(task_id_str) \# Repo lida com conversão e validação de ID  
         if deleted: log.success(\\"Tarefa deletada com sucesso.\\")  
         else: log.warning(\\"Tarefa não encontrada ou falha ao deletar.\\")  
         return deleted

\# Função de dependência  
async def get_task_service() \-\> TaskService:  
    \\"\\"\\"FastAPI dependency for TaskService.\\"\\"\\"  
    return TaskService()

\# Importar asyncio para notificação  
import asyncio
