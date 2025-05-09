# agentos_core/app/modules/stock/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from pymongo import ASCENDING, DESCENDING, UpdateOne  
from pymongo.results import UpdateResult, DeleteResult, BulkWriteResult # Adicionar BulkWriteResult  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import StockItemInDB, StockItemCreateInternal, StockItemUpdateInternal # Usar modelos internos

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "stock_items"

class StockItemRepository(BaseRepository[StockItemInDB, StockItemCreateInternal, StockItemUpdateInternal]):  
    model = StockItemInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de itens de estoque."""  
        try:  
            await self.collection.create_index("rfid_tag_id", unique=True) # Chave natural  
            await self.collection.create_index("product_id")  
            await self.collection.create_index("status")  
            await self.collection.create_index("location", sparse=True)  
            await self.collection.create_index([("last_seen_at", DESCENDING)], sparse=True)  
            await self.collection.create_index([("created_at", DESCENDING)])  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    async def get_by_rfid_tag(self, rfid_tag_id: str) -> Optional[StockItemInDB]:  
        """Busca um item pela sua tag RFID (case-insensitive?)."""  
        if not rfid_tag_id: return None  
        # Padronizar busca para maiúsculas se tags forem salvas assim  
        return await self.get_by({"rfid_tag_id": rfid_tag_id.upper()})

    async def create(self, data_in: StockItemCreateInternal | Dict) -> StockItemInDB:  
        """Cria um item de estoque, padronizando tag RFID."""  
        if isinstance(data_in, BaseModel):  
            create_data = data_in.model_dump(exclude_unset=False)  
        else:  
            create_data = data_in.copy()

        # Padronizar tag para maiúsculas  
        if "rfid_tag_id" in create_data and isinstance(create_data["rfid_tag_id"], str):  
             create_data["rfid_tag_id"] = create_data["rfid_tag_id"].upper()  
        else:  
             raise ValueError("rfid_tag_id is required and must be a string.")

        # Garantir que product_id é ObjectId  
        if "product_id" in create_data:  
            obj_id = self._to_objectid(create_data["product_id"])  
            if not obj_id: raise ValueError("Invalid product_id format.")  
            create_data["product_id"] = obj_id

        return await super().create(create_data)

    async def bulk_create_or_update(self, items_data: List[Dict]) -> Tuple[int, int, List[str]]:  
        """Cria ou atualiza múltiplos itens em bulk via upsert."""  
        if not items_data: return 0, 0, []  
        log = logger.bind(operation="bulk_stock_upsert", count=len(items_data))  
        log.info("Iniciando operação bulk...")

        operations = []  
        now = datetime.utcnow()  
        errors = []  
        processed_tags = set() # Para detectar duplicatas na entrada

        for item_dict in items_data:  
            rfid_tag = item_dict.get("rfid_tag_id")  
            if not rfid_tag or not isinstance(rfid_tag, str):  
                 errors.append(f"Missing or invalid rfid_tag_id in item: {str(item_dict)[:100]}...")  
                 continue

            rfid_tag_upper = rfid_tag.upper() # Padronizar  
            if rfid_tag_upper in processed_tags:  
                 errors.append(f"Duplicate rfid_tag_id '{rfid_tag_upper}' found in input batch.")  
                 continue  
            processed_tags.add(rfid_tag_upper)

            # Preparar dados para $set e $setOnInsert  
            set_data = {}  
            on_insert_data = {}

            # Validar e preparar product_id  
            prod_id = item_dict.get("product_id")  
            obj_prod_id = self._to_objectid(prod_id) if prod_id else None  
            if not obj_prod_id:  
                 errors.append(f"Invalid or missing product_id for tag '{rfid_tag_upper}'")  
                 continue  
            # Definir product_id apenas na inserção? Ou permitir update? Permitir update por enquanto.  
            set_data["product_id"] = obj_prod_id

            # Status inicial (apenas na inserção)  
            initial_status = item_dict.get("initial_status", "provisioned")  
            on_insert_data["status"] = initial_status

            # Outros campos (location, metadata - definir no $set para permitir update)  
            if "initial_location" in item_dict: set_data["location"] = item_dict["initial_location"]  
            if "metadata" in item_dict: set_data["metadata"] = item_dict["metadata"]

            # Timestamps  
            set_data["updated_at"] = now  
            on_insert_data["created_at"] = now  
            on_insert_data["rfid_tag_id"] = rfid_tag_upper # Garantir que é salvo

            operation = UpdateOne(  
                {"rfid_tag_id": rfid_tag_upper}, # Filtro pelo RFID (case-insensitive implícito se collation usado)  
                {  
                    "$set": set_data,  
                    "$setOnInsert": on_insert_data  
                },  
                upsert=True  
            )  
            operations.append(operation)

        if not operations:  
             log.warning("Nenhuma operação válida para executar no bulk.")  
             return 0, 0, errors

        try:  
            log.debug(f"Executando {len(operations)} operações bulk...")  
            result: BulkWriteResult = await self.collection.bulk_write(operations, ordered=False)  
            # Analisar resultado  
            upserted = result.upserted_count  
            matched = result.matched_count  
            modified = result.modified_count # Contagem real de docs *modificados* (não inclui upserts que não mudaram nada)

            # Contar inserções reais (upserts que *não* existiam)  
            # O upserted_ids é uma lista dos _id dos docs inseridos via upsert  
            inserted = len(result.upserted_ids) if result.upserted_ids else 0

            log.success(f"Bulk stock items concluído. Inserted: {inserted}, Matched: {matched}, Modified: {modified}")  
            if result.write_errors:  
                for err in result.write_errors:  
                     # Logar erro detalhado  
                     err_msg = f"Bulk write error (Index: {err.get('index')}): Code {err.get('code')} - {err.get('errmsg')}"  
                     logger.error(err_msg)  
                     errors.append(err_msg)  
            return inserted, modified, errors  
        except Exception as e:  
             # Capturar erros gerais do bulk write (ex: conexão)  
             self._handle_db_exception(e, "bulk_create_or_update")  
             errors.append(f"General bulk write error: {e}")  
             return 0, 0, errors

    async def update_status_by_tags(self, rfid_tag_ids: List[str], new_status: str, location: Optional[str] = None) -> int:  
        """Atualiza o status e opcionalmente localização de múltiplos itens por RFID."""  
        if not rfid_tag_ids: return 0  
        log = logger.bind(new_status=new_status, location=location, count=len(rfid_tag_ids))  
        log.info("Atualizando status/localização de itens por RFID tags...")

        # Padronizar tags para maiúsculas  
        tags_upper = [tag.upper() for tag in rfid_tag_ids]

        update_payload: Dict[str, Any] = {"status": new_status, "updated_at": datetime.utcnow()}  
        if location is not None: # Permitir location vazia ""? Sim.  
            update_payload["location"] = location  
            update_payload["last_seen_at"] = datetime.utcnow()

        try:  
            result: UpdateResult = await self.collection.update_many(  
                {"rfid_tag_id": {"$in": tags_upper}},  
                {"$set": update_payload}  
            )  
            log.info(f"Resultado da atualização por tags: Matched={result.matched_count}, Modified={result.modified_count}")  
            return result.modified_count  
        except Exception as e:  
             self._handle_db_exception(e, "update_status_by_tags")  
             return 0 # Indicar falha

# Função de dependência FastAPI  
async def get_stock_item_repository() -> StockItemRepository:  
    """FastAPI dependency to get StockItemRepository instance."""  
    db = get_database()  
    return StockItemRepository(db)
