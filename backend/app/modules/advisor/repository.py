# agentos_core/app/modules/advisor/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from pymongo import ASCENDING, DESCENDING  
from pymongo.results import UpdateResult, DeleteResult # Adicionar resultados  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import AdvisorConversationInDB, AdvisorConversationCreateInternal, AdvisorMessageEntryInternal # Usar modelos internos/DB

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "advisor_conversations"

class AdvisorConversationRepository(BaseRepository[AdvisorConversationInDB, AdvisorConversationCreateInternal, BaseModel]): # Sem Update Schema padrão  
    model = AdvisorConversationInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de conversas."""  
        try:  
            # Índice principal para buscar conversas de um usuário  
            await self.collection.create_index("user_id")  
            # Índice para ordenar/buscar por data de atualização (mais recentes)  
            await self.collection.create_index([("updated_at", DESCENDING)])  
            await self.collection.create_index([("created_at", DESCENDING)])  
            # Opcional: Índice de texto no título para busca?  
            # await self.collection.create_index("title", collation={'locale': 'en', 'strength': 2})  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    async def create(self, data_in: AdvisorConversationCreateInternal | Dict) -> AdvisorConversationInDB:  
        """Cria uma nova conversa."""  
        if isinstance(data_in, BaseModel):  
            create_data = data_in.model_dump(exclude_unset=False)  
        else:  
            create_data = data_in.copy()

        # Garantir que user_id é ObjectId  
        if "user_id" in create_data:  
            obj_id = self._to_objectid(create_data["user_id"])  
            if not obj_id: raise ValueError("Invalid user_id format for conversation.")  
            create_data["user_id"] = obj_id  
        else:  
             raise ValueError("user_id is required to create a conversation.")

        # Inicializar array de mensagens se não vier (Pydantic default deve fazer isso)  
        create_data.setdefault("messages", [])  
        # Inicializar título se não vier  
        create_data.setdefault("title", "Nova Conversa")

        return await super().create(create_data)

    async def add_message_to_conversation(self, conversation_id: ObjectId, message: AdvisorMessageEntryInternal) -> bool:  
        """Adiciona uma mensagem ao array 'messages' e atualiza 'updated_at'."""  
        now = datetime.utcnow()  
        log = logger.bind(conversation_id=str(conversation_id), message_role=message.role)  
        log.debug("Adicionando mensagem à conversa...")  
        try:  
             # Usar model_dump para garantir formato correto para Mongo  
            message_dict = message.model_dump(mode='json') # Usar modo json para datas/etc

            result: UpdateResult = await self.collection.update_one(  
                {"_id": conversation_id},  
                {  
                    "$push": {"messages": message_dict},  
                    "$set": {"updated_at": now} # Atualizar timestamp da conversa  
                }  
            )  
            success = result.modified_count > 0  
            if success: log.info("Mensagem adicionada com sucesso.")  
            else: log.warning("Conversa não encontrada ou erro ao adicionar mensagem.")  
            return success  
        except Exception as e:  
            # Usar handler para logar e levantar erro apropriado  
            self._handle_db_exception(e, "add_message_to_conversation", conversation_id)  
            return False # Retornar False em caso de erro

    async def get_conversation_with_messages(self, conversation_id: ObjectId, user_id: ObjectId) -> Optional[AdvisorConversationInDB]:  
         """Busca uma conversa completa (com mensagens), verificando o dono."""  
         log = logger.bind(conversation_id=str(conversation_id), user_id=str(user_id))  
         log.debug("Buscando conversa completa...")  
         # Adicionar filtro por user_id na query  
         conversation = await self.get_by({"_id": conversation_id, "user_id": user_id})  
         if conversation: log.info("Conversa encontrada.")  
         else: log.info("Conversa não encontrada ou acesso negado.")  
         return conversation

    async def list_conversations_by_user(  
        self,  
        user_id: ObjectId,  
        skip: int = 0,  
        limit: int = 50  
        ) -> List[Dict[str, Any]]: # Retorna dicts para o ListItem validar  
        """Lista conversas de um usuário (apenas metadados)."""  
        log = logger.bind(user_id=str(user_id))  
        log.debug(f"Listando conversas (limit={limit}, skip={skip})...")  
        try:  
            # Usar list_by do Base? Não, precisamos de projeção específica.  
            cursor = self.collection.find(  
                {"user_id": user_id},  
                # Projeção para otimizar: buscar apenas campos necessários  
                {"_id": 1, "title": 1, "created_at": 1, "updated_at": 1}  
            ).sort("updated_at", DESCENDING).skip(skip).limit(limit) # Mais recentes primeiro

            conversations = await cursor.to_list(length=limit)  
            log.info(f"Encontradas {len(conversations)} conversas para listagem.")  
            return conversations  
        except Exception as e:  
             self._handle_db_exception(e, "list_conversations_by_user", query={"user_id": user_id})  
             return []

    async def update_conversation_title(self, conversation_id: ObjectId, user_id: ObjectId, new_title: str) -> bool:  
         """Atualiza o título de uma conversa (verificando o dono)."""  
         log = logger.bind(conversation_id=str(conversation_id), user_id=str(user_id))  
         if not new_title: return False # Título não pode ser vazio

         log.debug(f"Atualizando título para: '{new_title[:50]}...'")  
         try:  
             result: UpdateResult = await self.collection.update_one(  
                 {"_id": conversation_id, "user_id": user_id}, # Garantir que só o dono atualize  
                 {"$set": {"title": new_title, "updated_at": datetime.utcnow()}}  
             )  
             success = result.modified_count > 0  
             if success: log.info("Título da conversa atualizado.")  
             elif result.matched_count == 0: log.warning("Conversa não encontrada ou acesso negado para atualizar título.")  
             else: log.debug("Título da conversa não modificado (talvez já fosse o mesmo?).")  
             return success  
         except Exception as e:  
             self._handle_db_exception(e, "update_conversation_title", conversation_id)  
             return False

    async def delete_conversation(self, conversation_id: ObjectId, user_id: ObjectId) -> bool:  
        """Deleta uma conversa (verificando o dono)."""  
        log = logger.bind(conversation_id=str(conversation_id), user_id=str(user_id))  
        log.info("Deletando conversa...")  
        # Usar delete do BaseRepository, que já verifica o filtro  
        # Mas precisamos garantir que o filtro inclua user_id  
        # O BaseRepository.delete só aceita ID. Melhor implementar aqui.  
        try:  
            result: DeleteResult = await self.collection.delete_one({"_id": conversation_id, "user_id": user_id})  
            deleted = result.deleted_count > 0  
            if deleted: log.success("Conversa deletada com sucesso.")  
            else: log.warning("Conversa não encontrada ou acesso negado para deleção.")  
            return deleted  
        except Exception as e:  
             self._handle_db_exception(e, "delete_conversation", conversation_id)  
             return False

# Função de dependência FastAPI  
async def get_advisor_conversation_repository() -> AdvisorConversationRepository:  
    """FastAPI dependency to get AdvisorConversationRepository instance."""  
    db = get_database()  
    return AdvisorConversationRepository(db)
