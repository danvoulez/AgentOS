# agentos_core/app/modules/people/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from motor.motor_asyncio import AsyncIOMotorDatabase  
from pymongo import ASCENDING, DESCENDING  
from pymongo.errors import DuplicateKeyError  
from loguru import logger  
from bson import ObjectId

# Importar Base e modelos internos/DB do próprio módulo  
from app.core.repository import BaseRepository  
from .models import UserInDB, UserProfile, UserCreateInternal, UserUpdateInternal # Usar modelos internos/DB

# Importar get_database para função de dependência  
from app.core.database import get_database

# Nome da coleção no MongoDB  
COLLECTION_NAME = "users"

class UserRepository(BaseRepository[UserInDB, UserCreateInternal, UserUpdateInternal]):  
    """Repositório para operações CRUD de Usuários no MongoDB."""  
    model = UserInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices necessários para a coleção de usuários."""  
        try:  
            # Índice único no email (convertido para minúsculas)  
            await self.collection.create_index("email", unique=True)  
            # Índice para buscar por roles  
            await self.collection.create_index("roles")  
            # Índice para buscar por status ativo  
            await self.collection.create_index("is_active")  
            # Índice para tags RFID (se usado)  
            await self.collection.create_index("rfid_tags", sparse=True) # Sparse pois pode não existir  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    async def get_by_email(self, email: str) -> Optional[UserInDB]:  
        """Busca um usuário pelo email (case-insensitive)."""  
        if not email: return None  
        logger.debug(f"Buscando usuário por email: {email}")  
        # Armazenar e buscar email sempre em minúsculas para garantir unicidade case-insensitive  
        user_doc = await self.get_by({"email": email.lower()})  
        if user_doc:  
             logger.info(f"Usuário encontrado por email: {email} (ID: {user_doc.id})")  
        else:  
             logger.debug(f"Usuário não encontrado por email: {email}")  
        return user_doc

    async def create(self, data_in: UserCreateInternal | Dict) -> UserInDB:  
        """Cria um novo usuário, garantindo email em minúsculas."""  
        if isinstance(data_in, BaseModel):  
            create_data = data_in.model_dump(exclude_unset=False)  
        else:  
            create_data = data_in.copy()

        if "email" in create_data and isinstance(create_data["email"], str):  
             create_data["email"] = create_data["email"].lower()  
        else:  
             # Email é obrigatório para UserInDB/UserCreateInternal, Pydantic deve ter validado  
             logger.error("Tentativa de criar usuário sem email ou com tipo inválido.")  
             raise ValueError("Email is required to create a user.")

        # Chamar create do BaseRepository que lida com timestamps e DuplicateKeyError  
        return await super().create(create_data)

    async def update(self, id: str | ObjectId, data_in: UserUpdateInternal | Dict) -> Optional[UserInDB]:  
        """Atualiza um usuário, garantindo email em minúsculas se alterado."""  
        if isinstance(data_in, BaseModel):  
            update_data = data_in.model_dump(exclude_unset=True)  
        else:  
            update_data = data_in.copy()

        # Converter email para minúsculas se estiver sendo atualizado  
        if "email" in update_data and isinstance(update_data["email"], str):  
            update_data["email"] = update_data["email"].lower()  
            # Verificar duplicação ANTES de chamar super().update  
            obj_id = self._to_objectid(id)  
            if obj_id: # Só verificar se o ID é válido  
                existing_user = await self.get_by_email(update_data["email"])  
                if existing_user and existing_user.id != obj_id:  
                     logger.warning(f"Falha no update: Email '{update_data['email']}' já está em uso por outro usuário (ID: {existing_user.id}).")  
                     raise ValueError(f"Email '{update_data['email']}' is already registered.")  
            else:  
                 # Não deveria chegar aqui se ID for inválido, mas por segurança  
                 logger.error(f"Tentativa de update com ID inválido: {id}")  
                 return None

        # Chamar update do BaseRepository que lida com $set, timestamps e erros  
        return await super().update(id, update_data)

    async def add_rfid_tag(self, user_id: ObjectId, tag_id: str) -> bool:  
        """Adiciona uma tag RFID ao array do usuário (evita duplicatas)."""  
        result = await self.collection.update_one(  
            {"_id": user_id},  
            {"$addToSet": {"rfid_tags": tag_id.upper()}} # Usar $addToSet para evitar duplicatas e padronizar  
        )  
        return result.modified_count > 0

    async def remove_rfid_tag(self, user_id: ObjectId, tag_id: str) -> bool:  
        """Remove uma tag RFID do array do usuário."""  
        result = await self.collection.update_one(  
            {"_id": user_id},  
            {"$pull": {"rfid_tags": tag_id.upper()}} # Usar $pull para remover  
        )  
        return result.modified_count > 0

# Função de dependência FastAPI  
async def get_user_repository() -> UserRepository:  
    """FastAPI dependency to get UserRepository instance."""  
    db = get_database()  
    return UserRepository(db)

# Importar BaseModel de Pydantic se usado em data_in  
from pydantic import BaseModel
