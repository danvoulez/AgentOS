# agentos_core/app/modules/office/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from pymongo import ASCENDING, DESCENDING, UpdateOne # Adicionar UpdateOne  
from pymongo.results import UpdateResult, DeleteResult # Adicionar resultados  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import SettingInDB, SettingCreateInternal, SettingUpdateInternal,   
                  AuditLogInDB, AuditLogCreateInternal # Usar nomes internos

# Importar get_database  
from app.core.database import get_database

# --- Repositório de Settings ---  
SETTINGS_COLLECTION = "settings"

# Repositório Customizado para Settings (usa 'key' string como _id)  
class SettingRepository:  
    collection_name = SETTINGS_COLLECTION  
    model = SettingInDB # Modelo Pydantic para validação de retorno

    def __init__(self, db: AsyncIOMotorDatabase):  
        if not isinstance(db, AsyncIOMotorDatabase):  
             raise TypeError("SettingRepository requires a valid AsyncIOMotorDatabase instance.")  
        self.db = db  
        self.collection: AsyncIOMotorCollection = db[self.collection_name]  
        logger.debug(f"SettingRepository initialized for collection: '{self.collection_name}'")

    async def create_indexes(self):  
        """Garante índice em _id (que é a 'key')."""  
        # O índice em _id é criado automaticamente pelo MongoDB.  
        logger.info(f"Índices verificados para a coleção: {self.collection_name} (usa _id como key)")  
        pass

    async def get_setting(self, key: str) -> Optional[SettingInDB]:  
        """Busca uma configuração pela chave (_id)."""  
        if not key or not isinstance(key, str):  
             logger.warning(f"Tentativa de buscar setting com chave inválida: {key}")  
             return None  
        try:  
            doc = await self.collection.find_one({"_id": key})  
            return self.model.model_validate(doc) if doc else None  
        except Exception as e:  
             # Usar handler do BaseRepository? Ou um local? Local por enquanto.  
             logger.exception(f"Erro de DB ao buscar setting '{key}': {e}")  
             raise RuntimeError(f"Database error fetching setting '{key}'") from e

    async def set_setting(self, setting_data: SettingCreateInternal | Dict) -> Optional[SettingInDB]:  
        """Cria ou atualiza completamente uma configuração (upsert)."""  
        if isinstance(setting_data, BaseModel):  
            data = setting_data.model_dump(exclude_unset=False, by_alias=False)  
        else:  
            data = setting_data.copy()

        key = data.get("key") # Obter a chave lógica  
        if not key or not isinstance(key, str):  
            raise ValueError("Setting key must be provided and be a string.")

        # Preparar dados para $set, usando a 'key' como '_id'  
        set_on_insert_data = {"_id": key} # Garantir _id na inserção  
        set_data = data.copy()  
        set_data.pop("key", None) # Remover 'key' do $set  
        set_data.setdefault("updated_at", datetime.utcnow()) # Garantir timestamp

        try:  
            result: UpdateResult = await self.collection.update_one(  
                {"_id": key}, # Filtro é a própria chave  
                {"$set": set_data, "$setOnInsert": set_on_insert_data},  
                upsert=True  
            )  
            # Buscar o documento após upsert para retornar dados consistentes  
            if result.upserted_id or result.modified_count > 0 or result.matched_count > 0:  
                 logger.info(f"Setting '{key}' foi {'criado' if result.upserted_id else 'atualizado'}.")  
                 return await self.get_setting(key) # Retorna o doc completo e validado  
            else:  
                 # Estado inesperado com upsert=True  
                 logger.error(f"Operação set_setting para chave '{key}' não resultou em upsert ou match.")  
                 return None  
        except Exception as e:  
             # Usar handler?  
             logger.exception(f"Erro de DB ao definir setting '{key}': {e}")  
             if isinstance(e, DuplicateKeyError): # Deveria ser pego pelo upsert, mas segurança extra  
                  raise ValueError(f"Setting key '{key}' already exists (concurrent modification?).") from e  
             raise RuntimeError(f"Database error setting setting '{key}'") from e

    async def update_setting_fields(self, key: str, update_data: SettingUpdateInternal | Dict) -> Optional[SettingInDB]:  
         """Atualiza campos específicos de uma configuração existente ($set)."""  
         if isinstance(update_data, BaseModel):  
              data_to_set = update_data.model_dump(exclude_unset=True, by_alias=False)  
         else:  
              data_to_set = update_data.copy()

         # Remover campos não atualizáveis (key/_id)  
         data_to_set.pop("key", None)  
         data_to_set.pop("_id", None)  
         data_to_set.pop("id", None)

         if not data_to_set:  
             logger.debug(f"Update chamado para setting '{key}' sem dados alteráveis.")  
             return await self.get_setting(key)

         data_to_set["updated_at"] = datetime.utcnow()

         try:  
             result: UpdateResult = await self.collection.update_one(  
                 {"_id": key},  
                 {"$set": data_to_set}  
             )  
             if result.matched_count == 0:  
                 logger.warning(f"Setting '{key}' não encontrado para atualização PATCH.")  
                 return None

             logger.debug(f"Setting '{key}' atualizado (PATCH). Modificados: {result.modified_count}")  
             return await self.get_setting(key) # Retorna doc atualizado  
         except Exception as e:  
             logger.exception(f"Erro de DB ao atualizar (PATCH) setting '{key}': {e}")  
             raise RuntimeError(f"Database error updating setting '{key}'") from e

    async def list_settings(self, skip: int = 0, limit: int = 0) -> List[SettingInDB]:  
        """Lista todas as configurações."""  
        try:  
            # Usar list_by do BaseRepository? Não, este repo não herda. Implementar aqui.  
            cursor = self.collection.find().sort("_id", ASCENDING).skip(skip) # Ordenar por chave  
            if limit > 0: cursor = cursor.limit(limit)  
            docs = await cursor.to_list(length=limit if limit > 0 else None)  
            return [self.model.model_validate(doc) for doc in docs]  
        except Exception as e:  
            logger.exception(f"Erro de DB ao listar settings: {e}")  
            raise RuntimeError("Database error listing settings") from e

    async def delete_setting(self, key: str) -> bool:  
        """Deleta uma configuração pela chave (_id)."""  
        if not key or not isinstance(key, str): return False  
        try:  
            result: DeleteResult = await self.collection.delete_one({"_id": key})  
            deleted = result.deleted_count > 0  
            if deleted: logger.info(f"Setting '{key}' deletado.")  
            else: logger.warning(f"Setting '{key}' não encontrado para deleção.")  
            return deleted  
        except Exception as e:  
            logger.exception(f"Erro de DB ao deletar setting '{key}': {e}")  
            raise RuntimeError(f"Database error deleting setting '{key}'") from e

# Função de dependência FastAPI  
async def get_setting_repository() -> SettingRepository:  
    """FastAPI dependency to get SettingRepository instance."""  
    db = get_database()  
    return SettingRepository(db)

# --- Repositório de Audit Logs (Herda de BaseRepository) ---  
AUDIT_LOGS_COLLECTION = "audit_logs"

class AuditLogRepository(BaseRepository[AuditLogInDB, AuditLogCreateInternal, BaseModel]): # Sem Update Schema  
    model = AuditLogInDB  
    collection_name = AUDIT_LOGS_COLLECTION

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de logs de auditoria."""  
        try:  
            await self.collection.create_index([("timestamp", DESCENDING)])  
            await self.collection.create_index("user_id", sparse=True)  
            await self.collection.create_index("user_email", sparse=True)  
            await self.collection.create_index("action")  
            await self.collection.create_index("entity_type", sparse=True)  
            await self.collection.create_index("entity_id", sparse=True)  
            await self.collection.create_index("status")  
            await self.collection.create_index("ip_address", sparse=True)  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    # create do BaseRepository é suficiente, pois AuditLogCreateInternal é Pydantic

    # Método de listagem com filtros específicos  
    async def list_logs_by_filter(  
        self,  
        start_date: Optional[datetime] = None,  
        end_date: Optional[datetime] = None,  
        user_id_str: Optional[str] = None, # Renomear para clareza  
        action: Optional[str] = None,  
        entity_type: Optional[str] = None,  
        entity_id: Optional[str] = None,  
        status: Optional[str] = None,  
        ip_address: Optional[str] = None, # Adicionar filtro IP  
        skip: int = 0,  
        limit: int = 100  
    ) -> List[AuditLogInDB]:  
        """Lista logs de auditoria com filtros."""  
        query: Dict[str, Any] = {}  
        if start_date or end_date:  
            query["timestamp"] = {}  
            if start_date: query["timestamp"]["$gte"] = start_date  
            if end_date: query["timestamp"]["$lte"] = end_date  
        if user_id_str:  
            obj_user_id = self._to_objectid(user_id_str)  
            if obj_user_id: query["user_id"] = obj_user_id  
        if action: query["action"] = action  
        if entity_type: query["entity_type"] = entity_type  
        if entity_id: query["entity_id"] = entity_id # ID é string no modelo  
        if status: query["status"] = status  
        if ip_address: query["ip_address"] = ip_address

        # Usar list_by do BaseRepository com a query montada  
        return await self.list_by(query=query, skip=skip, limit=limit, sort=[("timestamp", DESCENDING)])

# Função de dependência FastAPI  
async def get_audit_log_repository() -> AuditLogRepository:  
    """FastAPI dependency to get AuditLogRepository instance."""  
    db = get_database()  
    return AuditLogRepository(db)
