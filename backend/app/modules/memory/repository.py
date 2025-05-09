# agentos_core/app/modules/memory/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase  
from pymongo import ASCENDING, DESCENDING  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import MemoryRecordInDB, MemoryRecordCreateInternal # Usar nomes internos  
from app.core.config import settings # Para config de embedding/index

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "memories"

class MemoryRepository(BaseRepository[MemoryRecordInDB, MemoryRecordCreateInternal, BaseModel]): # Sem Update Schema  
    model = MemoryRecordInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices B-Tree. Índice vetorial DEVE ser criado no Atlas."""  
        try:  
            await self.collection.create_index("user_id")  
            await self.collection.create_index([("created_at", DESCENDING)])  
            await self.collection.create_index("tags", sparse=True)  
            await self.collection.create_index("source", sparse=True)  
            logger.info(f"Índices B-Tree criados/verificados para: {self.collection_name}")

            logger.warning(f"IMPORTANTE: Crie manualmente o índice Atlas Search vetorial "  
                           f"nomeado '{settings.MONGO_MEMORY_SEARCH_INDEX_NAME}' na coleção "  
                           f"'{self.collection_name}' para o campo 'embedding' "  
                           f"({settings.EMBEDDING_DIMENSIONS} dims, ex: cosine) "  
                           f"e inclua 'user_id' e 'tags' no índice para pré-filtragem.")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices B-Tree para {self.collection_name}: {e}")

    async def create_memory(self, record_data: MemoryRecordCreateInternal | Dict) -> MemoryRecordInDB:  
        """Cria um registro de memória com embedding."""  
        if isinstance(record_data, BaseModel):  
             create_data = record_data.model_dump(exclude_unset=False)  
        else:  
             create_data = record_data.copy()

        # Validar dimensão do embedding antes de salvar  
        embedding = create_data.get("embedding")  
        if not embedding or not isinstance(embedding, list) or len(embedding) != settings.EMBEDDING_DIMENSIONS:  
             err_msg = (f"Memory record missing or has incorrect embedding dimension "  
                        f"(Expected: {settings.EMBEDDING_DIMENSIONS}, Got: {len(embedding) if embedding else 'None'}).")  
             logger.error(err_msg)  
             raise ValueError(err_msg)

        # Garantir que user_id é ObjectId  
        if "user_id" in create_data:  
             obj_id = self._to_objectid(create_data["user_id"])  
             if not obj_id: raise ValueError("Invalid user_id format for memory record.")  
             create_data["user_id"] = obj_id

        # Chamar create do BaseRepository  
        return await super().create(create_data)

    async def vector_search(  
        self,  
        query_embedding: List[float],  
        user_id: ObjectId,  
        limit: int = 5,  
        min_similarity: float = 0.75,  
        tags_filter: Optional[List[str]] = None  
    ) -> List[Dict[str, Any]]: # Retornar dicts com score para o service validar/modelar  
        """Executa busca vetorial via Atlas Search $vectorSearch."""

        if len(query_embedding) != settings.EMBEDDING_DIMENSIONS:  
            raise ValueError(f"Query embedding dimension mismatch ({len(query_embedding)} vs {settings.EMBEDDING_DIMENSIONS})")

        search_index_name = settings.MONGO_MEMORY_SEARCH_INDEX_NAME

        # Construir estágio $vectorSearch  
        vector_search_stage = {  
            "index": search_index_name,  
            "path": "embedding",  
            "queryVector": query_embedding,  
            "numCandidates": max(limit * 15, 150), # Aumentar candidatos para melhor recall com filtros  
            "limit": limit,  
            # Filtro OBRIGATÓRIO por user_id!  
            "filter": {  
                "user_id": user_id # Filtrar ANTES da busca vetorial  
            }  
        }  
        # Adicionar filtro de tags se suportado pelo índice e fornecido  
        if tags_filter:  
             # Assumindo que 'tags' foi indexado como 'token' ou similar no Atlas Search Index  
             vector_search_stage["filter"]["tags"] = {"$in": tags_filter}  
             logger.debug(f"Vector search inclui filtro de tags: {tags_filter}")

        # Construir pipeline completo  
        pipeline = [  
            {"$vectorSearch": vector_search_stage},  
            { # Projetar campos + score  
              "$project": {  
                  "_id": 1, "user_id": 1, "text": 1, "source": 1, "tags": 1, "created_at": 1,  
                  "similarity_score": {"$meta": "vectorSearchScore"}  
                  # Não incluir "embedding" por padrão  
              }  
            },  
            { # Filtrar por score mínimo APÓS a busca  
              "$match": {  
                  "similarity_score": {"$gte": min_similarity}  
              }  
            },  
             { # Ordenar pelo score descendente (mais similar primeiro)  
                "$sort": {"similarity_score": -1}  
             }  
        ]

        log = logger.bind(user_id=str(user_id), limit=limit, min_score=min_similarity, index=search_index_name)  
        log.debug(f"Executando vector search. Pipeline: {pipeline}")

        try:  
            cursor = self.collection.aggregate(pipeline)  
            results = await cursor.to_list(length=limit)  
            log.info(f"Vector search encontrou {len(results)} memórias relevantes.")  
            return results # Retorna lista de dicionários do DB com score  
        except Exception as e:  
            log.exception(f"Erro durante vector search: {e}")  
            # Verificar se o erro indica que o índice não existe  
            if "index not found" in str(e) or "no such index" in str(e):  
                 log.error(f"ÍNDICE ATLAS SEARCH '{search_index_name}' NÃO ENCONTRADO OU NÃO ESTÁ PRONTO!")  
                 raise RuntimeError(f"Required Atlas Search index '{search_index_name}' not found or not ready.") from e  
            raise RuntimeError(f"Vector search failed: {e}") from e

# Função de dependência FastAPI  
async def get_memory_repository() -> MemoryRepository:  
    """FastAPI dependency to get MemoryRepository instance."""  
    db = get_database()  
    return MemoryRepository(db)
