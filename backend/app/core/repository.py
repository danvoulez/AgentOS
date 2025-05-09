# agentos_core/app/core/repository.py

from typing import TypeVar, Type, Optional, List, Any, Dict, Tuple, cast # Adicionar cast  
from abc import ABC, abstractmethod  
from datetime import datetime  
from decimal import Decimal # Adicionar Decimal

from pydantic import BaseModel  
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from bson import ObjectId  
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult  
from pymongo.errors import DuplicateKeyError  
from loguru import logger

# Importar get_database da implementação final  
from app.core.database import get_database

# Tipos genéricos  
ModelType = TypeVar("ModelType", bound=BaseModel) # Modelo Pydantic que representa o doc DB (ex: UserInDB)  
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel) # Schema para criar (ex: UserCreate)  
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel) # Schema para atualizar (ex: UserUpdate)

class BaseRepository(ABC):  
    """Classe base abstrata para repositórios MongoDB com Motor e Pydantic."""

    model: Type[ModelType]  
    collection_name: str

    def __init__(self, db: AsyncIOMotorDatabase):  
        if not hasattr(self, 'collection_name') or not self.collection_name:  
             raise AttributeError("Repository subclass must define a 'collection_name'")  
        if not hasattr(self, 'model') or not issubclass(self.model, BaseModel):  
             raise AttributeError("Repository subclass must define a Pydantic 'model'")  
        if not isinstance(db, AsyncIOMotorDatabase):  
             raise TypeError("BaseRepository requires a valid AsyncIOMotorDatabase instance.")

        self.db = db  
        self.collection: AsyncIOMotorCollection = db[self.collection_name]  
        logger.debug(f"BaseRepository initialized for collection: '{self.collection_name}'")

    @staticmethod  
    def _to_objectid(id_str: Any) -> Optional[ObjectId]:  
        """Converte input para ObjectId de forma segura, retornando None se inválido."""  
        if isinstance(id_str, ObjectId):  
            return id_str  
        if isinstance(id_str, str) and ObjectId.is_valid(id_str):  
            try:  
                return ObjectId(id_str)  
            except Exception: # Capturar erros inesperados da conversão  
                 logger.warning(f"Falha ao converter string '{id_str}' válida para ObjectId.")  
                 return None  
        # Logar aviso para tipos inesperados ou inválidos  
        # logger.warning(f"Input inválido para conversão ObjectId: '{id_str}' (Tipo: {type(id_str)})")  
        return None

    @staticmethod  
    def _handle_db_exception(e: Exception, operation: str, doc_id: Any = None, query: Optional[Dict] = None):  
        """Loga e levanta exceções de banco de dados padronizadas."""  
        context = f"op='{operation}' coll='{getattr(e.__traceback__.tb_frame.f_locals.get('self', None), 'collection_name', 'unknown')}'" # Tentar pegar collection do self  
        if doc_id: context += f" id='{doc_id}'"  
        if query: context += f" query='{str(query)[:100]}...'" # Limitar tamanho da query no log

        log_msg = f"DB Error during {context}: {e}"

        if isinstance(e, DuplicateKeyError):  
            dup_key_info = e.details.get('keyValue', {}) if e.details else {}  
            logger.error(f"{log_msg} - Duplicate Key: {dup_key_info}")  
            # Levantar erro específico para chave duplicada  
            raise ValueError(f"Duplicate key error: Field(s) {list(dup_key_info.keys())} must be unique.") from e  
        else:  
            # Logar com traceback para erros inesperados  
            logger.exception(log_msg)  
            raise RuntimeError(f"Database error during operation: {operation}") from e

    def _prepare_data_for_db(self, data: Dict) -> Dict:  
        """Prepara dados para inserção/atualização (ex: converter Decimal). Subclasses podem sobrescrever."""  
        prepared_data = {}  
        for key, value in data.items():  
             # Exemplo: Converter Decimal para String (ajuste conforme necessidade do seu DB/driver)  
            if isinstance(value, Decimal):  
                 prepared_data[key] = str(value)  
            # Adicionar outras conversões se necessário (ex: Datetime para formato específico?)  
            else:  
                 prepared_data[key] = value  
        return prepared_data

    async def get_by_id(self, id: str | ObjectId) -> Optional[ModelType]:  
        """Busca um documento pelo seu _id."""  
        obj_id = self._to_objectid(id)  
        if not obj_id: return None  
        try:  
            document = await self.collection.find_one({"_id": obj_id})  
            return self.model.model_validate(document) if document else None  
        except Exception as e:  
            self._handle_db_exception(e, "get_by_id", obj_id)  
            return None # Erro de DB, retornar None

    async def get_by(self, query: Dict[str, Any]) -> Optional[ModelType]:  
        """Busca o PRIMEIRO documento que corresponde a um critério."""  
        try:  
            document = await self.collection.find_one(query)  
            return self.model.model_validate(document) if document else None  
        except Exception as e:  
            self._handle_db_exception(e, "get_by", query=query)  
            return None

    async def list_by(  
        self,  
        query: Dict[str, Any] = {},  
        skip: int = 0,  
        limit: int = 100, # Default limit  
        sort: Optional[List[Tuple[str, int]]] = None  
    ) -> List[ModelType]:  
        """Lista documentos com base em critérios, paginação e ordenação."""  
        try:  
            cursor = self.collection.find(query)  
            if sort:  
                cursor = cursor.sort(sort)  
            # Aplicar skip e limit (garantir não negativos)  
            cursor = cursor.skip(max(0, skip)).limit(max(0, limit) if limit > 0 else 0) # limit=0 significa sem limite para pymongo  
            documents = await cursor.to_list(length=limit if limit > 0 else None) # length=None para buscar todos se limit=0  
            # Validar cada documento (pode ser lento para listas grandes)  
            # Considerar retornar dicts e validar no service/router se performance for crítica  
            return [self.model.model_validate(doc) for doc in documents]  
        except Exception as e:  
             self._handle_db_exception(e, "list_by", query=query)  
             return [] # Retornar lista vazia em caso de erro

    async def create(self, data_in: CreateSchemaType | Dict) -> ModelType:  
        """Cria um novo documento."""  
        if isinstance(data_in, BaseModel):  
            create_data_dict = data_in.model_dump(exclude_unset=False, by_alias=False)  
        else:  
            create_data_dict = data_in.copy()

        # Preparar dados (ex: converter Decimal)  
        create_data_prepared = self._prepare_data_for_db(create_data_dict)

        # Adicionar timestamps  
        now = datetime.utcnow()  
        create_data_prepared.setdefault("created_at", now)  
        create_data_prepared.setdefault("updated_at", now)

        # Remover _id/id  
        create_data_prepared.pop("_id", None)  
        create_data_prepared.pop("id", None)

        try:  
            result: InsertOneResult = await self.collection.insert_one(create_data_prepared)  
            inserted_id = result.inserted_id  
            # Buscar o documento recém-criado para retornar o objeto Pydantic validado  
            created_document = await self.get_by_id(inserted_id)  
            if created_document is None:  
                 # Log crítico  
                 logger.critical(f"CRITICAL: Failed to retrieve document immediately after insertion! ID: {inserted_id}, Collection: {self.collection_name}")  
                 raise RuntimeError("Failed to retrieve document after creation.")  
            return created_document  
        except Exception as e:  
             # _handle_db_exception já loga e levanta erro (ValueError para DupKey, RuntimeError para outros)  
             self._handle_db_exception(e, "create")  
             # Garantir que a função não retorne se _handle_db_exception levantar erro  
             raise # Re-raise a exceção que _handle_db_exception levantou

    async def update(self, id: str | ObjectId, data_in: UpdateSchemaType | Dict) -> Optional[ModelType]:  
        """Atualiza um documento existente usando $set."""  
        obj_id = self._to_objectid(id)  
        if not obj_id: return None

        if isinstance(data_in, BaseModel):  
            update_data_dict = data_in.model_dump(exclude_unset=True, by_alias=False) # Apenas campos definidos  
        else:  
            update_data_dict = data_in.copy()

        # Preparar dados (ex: converter Decimal)  
        update_data_prepared = self._prepare_data_for_db(update_data_dict)

        # Remover campos protegidos/imutáveis  
        immutable_fields = ["_id", "id", "created_at"] # Adicionar outros se necessário  
        for field in immutable_fields:  
            update_data_prepared.pop(field, None)

        if not update_data_prepared:  
            logger.debug(f"Update called for ID {id} with no updatable data.")  
            return await self.get_by_id(obj_id)

        # Adicionar timestamp de atualização  
        update_data_prepared["updated_at"] = datetime.utcnow()

        try:  
            result: UpdateResult = await self.collection.update_one(  
                {"_id": obj_id},  
                {"$set": update_data_prepared}  
            )  
            if result.matched_count == 0:  
                logger.warning(f"Document not found for update: ID {id}, Collection: {self.collection_name}")  
                return None

            logger.debug(f"Document updated: ID {id}, Matched: {result.matched_count}, Modified: {result.modified_count}")  
            # Retorna o documento completo e atualizado  
            return await self.get_by_id(obj_id)

        except Exception as e:  
             self._handle_db_exception(e, "update", obj_id)  
             return None

    async def delete(self, id: str | ObjectId) -> bool:  
        """Deleta um documento pelo ID."""  
        obj_id = self._to_objectid(id)  
        if not obj_id: return False  
        try:  
            result: DeleteResult = await self.collection.delete_one({"_id": obj_id})  
            deleted = result.deleted_count > 0  
            if deleted: logger.info(f"Document deleted: ID {id}, Collection: {self.collection_name}")  
            else: logger.warning(f"Document not found for deletion: ID {id}, Collection: {self.collection_name}")  
            return deleted  
        except Exception as e:  
             self._handle_db_exception(e, "delete", obj_id)  
             return False

    async def count(self, query: Dict[str, Any] = {}) -> int:  
        """Conta documentos que correspondem a um critério."""  
        logger.debug(f"Counting documents in {self.collection_name} with query: {query}")  
        try:  
            count = await self.collection.count_documents(query)  
            logger.debug(f"Count result: {count}")  
            return count  
        except Exception as e:  
            self._handle_db_exception(e, "count", query=query)  
            return -1 # Indicar erro

    # Não incluir create_indexes aqui, chamar externamente  
    # @abstractmethod  
    # async def create_indexes(self): ...

    # Método para deleção lógica (requer campo 'is_active' no modelo)  
    async def set_active_status(self, id: str | ObjectId, is_active: bool) -> Optional[ModelType]:  
        """Define o status ativo/inativo (requer campo 'is_active')."""  
        # Assume que UpdateSchemaType pode lidar com {"is_active": bool} ou passamos dict  
        logger.info(f"Setting active status to {is_active} for ID {id} in {self.collection_name}")  
        return await self.update(id, {"is_active": is_active})
