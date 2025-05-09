# ./app/modules/tasks/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime, date # Adicionar date

from motor.motor_asyncio import AsyncIOMotorDatabase  
from pymongo import ASCENDING, DESCENDING  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel # Adicionar BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import TaskInDB, TaskCreateInternal, TaskUpdateInternal # Usar nomes internos

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "tasks"

class TaskRepository(BaseRepository[TaskInDB, TaskCreateInternal, TaskUpdateInternal]):  
    model = TaskInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de tarefas."""  
        try:  
            # Índices comuns para filtros e ordenação  
            await self.collection.create_index([("due_date", ASCENDING)], sparse=True)  
            await self.collection.create_index("status")  
            await self.collection.create_index("priority") # Considerar collation para sort? Ou mapear para número?  
            await self.collection.create_index("assigned_to", sparse=True)  
            await self.collection.create_index("created_by")  
            await self.collection.create_index("related_entity_id", sparse=True)  
            await self.collection.create_index("tags", sparse=True)  
            await self.collection.create_index([("created_at", DESCENDING)])  
            await self.collection.create_index([("updated_at", DESCENDING)])  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    # create do BaseRepository geralmente serve  
    async def create(self, data_in: TaskCreateInternal | Dict) -> TaskInDB:  
         if isinstance(data_in, BaseModel):  
             create_data = data_in.model_dump(exclude_unset=False)  
         else:  
             create_data = data_in.copy()  
         # Garantir que IDs são ObjectId  
         if "assigned_to" in create_data and create_data["assigned_to"]:  
              obj_id = self._to_objectid(create_data["assigned_to"])  
              if not obj_id: raise ValueError("Invalid assigned_to ID format during create")  
              create_data["assigned_to"] = obj_id  
         if "created_by" in create_data and create_data["created_by"]:  
              obj_id = self._to_objectid(create_data["created_by"])  
              if not obj_id: raise ValueError("Invalid created_by ID format during create")  
              create_data["created_by"] = obj_id  
         # Garantir que due_date (se string) é convertido para datetime (ou date?)  
         # O modelo Pydantic já deve ter validado/convertido, mas dupla checagem  
         if "due_date" in create_data and isinstance(create_data["due_date"], date) and not isinstance(create_data["due_date"], datetime):  
              # Converter date para datetime (meia-noite UTC) para consistência no Mongo? Ou manter date? Manter date é mais simples se o modelo suportar.  
              # Pydantic v2 lida melhor com date. Se usar date, ok. Se precisar de datetime:  
              # create_data["due_date"] = datetime.combine(create_data["due_date"], datetime.min.time(), tzinfo=timezone.utc)  
              pass # Assumindo que o modelo/driver lida com date

         return await super().create(create_data)

    # update do BaseRepository geralmente serve, mas atenção ao completed_at  
    async def update(self, id: str | ObjectId, data_in: TaskUpdateInternal | Dict) -> Optional[TaskInDB]:  
        if isinstance(data_in, BaseModel):  
            update_data = data_in.model_dump(exclude_unset=True)  
        else:  
            update_data = data_in.copy()

        # Garantir que IDs são ObjectId  
        if "assigned_to" in update_data and update_data["assigned_to"]:  
             obj_id = self._to_objectid(update_data["assigned_to"])  
             if not obj_id: raise ValueError("Invalid assigned_to ID format during update")  
             update_data["assigned_to"] = obj_id  
        elif "assigned_to" in update_data and update_data["assigned_to"] is None:  
            # Permitir desatribuição - precisa usar $unset ou $set: null? $set: null é mais simples  
             update_data["assigned_to"] = None

        # Tratar due_date  
        if "due_date" in update_data and isinstance(update_data["due_date"], date) and not isinstance(update_data["due_date"], datetime):  
              # update_data["due_date"] = datetime.combine(update_data["due_date"], datetime.min.time(), tzinfo=timezone.utc)  
              pass # Manter date se o modelo suportar  
        elif "due_date" in update_data and update_data["due_date"] is None:  
            # Remover data limite  
            update_data["due_date"] = None

        # Lógica do completed_at deve estar no SERVICE antes de chamar update  
        # O repo apenas aplica o $set que o service mandar.  
        # Remover completed_at do update_data aqui para garantir que só o service controle  
        update_data.pop("completed_at", None)

        return await super().update(id, update_data)

    # Métodos de listagem específicos  
    async def list_tasks_by_filter(  
        self,  
        status: Optional[str] = None,  
        priority: Optional[str] = None,  
        created_by_str: Optional[str] = None, # Renomeado para clareza  
        assigned_to_str: Optional[str] = None, # Renomeado para clareza  
        due_before: Optional[date] = None, # Receber date  
        due_after: Optional[date] = None,  # Receber date  
        tags: Optional[List[str]] = None,  
        skip: int = 0,  
        limit: int = 100  
        ) -> List[TaskInDB]:  
        """Lista tarefas com filtros variados."""  
        query = {}  
        if status: query["status"] = status  
        if priority: query["priority"] = priority

        creator_objid = self._to_objectid(created_by_str) if created_by_str else None  
        assignee_objid = self._to_objectid(assigned_to_str) if assigned_to_str else None  
        if creator_objid: query["created_by"] = creator_objid  
        if assignee_objid: query["assigned_to"] = assignee_objid

        if due_before or due_after:  
            query["due_date"] = {}  
            # Converter date para datetime para query Mongo se necessário  
            if due_after: query["due_date"]["$gte"] = datetime.combine(due_after, datetime.min.time())  
            if due_before: query["due_date"]["$lte"] = datetime.combine(due_before, datetime.max.time())

        if tags: query["tags"] = {"$in": tags}

        # Definir ordem de sort (ex: Prioridade > Data Vencimento > Data Criação)  
        # Mapear prioridade textual para valor numérico para sort correto  
        priority_map = {"urgent": 4, "high": 3, "medium": 2, "low": 1}  
        sort_order = [  
             # Não podemos ordenar diretamente por prioridade textual.  
             # Opções:  
             # 1. Adicionar campo numérico de prioridade no Doc e indexar.  
             # 2. Fazer sort na aplicação após buscar (ineficiente).  
             # 3. Usar agregação com $addFields e $cond (complexo).  
             # Por ora, ordenar por due_date e created_at.  
             ("due_date", ASCENDING), # Nulos primeiro ou último? MongoDB trata nulos como menores.  
             ("created_at", DESCENDING)  
        ]  
        return await self.list_by(query=query, skip=skip, limit=limit, sort=sort_order)

# Função de dependência FastAPI  
async def get_task_repository() -> TaskRepository:  
    """FastAPI dependency to get TaskRepository instance."""  
    db = get_database()  
    return TaskRepository(db)
