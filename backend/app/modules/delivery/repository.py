# agentos_core/app/modules/delivery/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from pymongo import ASCENDING, DESCENDING, UpdateOne # Importar UpdateOne  
from pymongo.results import UpdateResult # Importar UpdateResult  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel

from app.core.repository import BaseRepository  
# Importar modelos internos/DB  
from .models import DeliveryInDB, DeliveryCreateInternal, DeliveryUpdateInternal, TrackingEvent # Usar modelos internos

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "deliveries"

class DeliveryRepository(BaseRepository[DeliveryInDB, DeliveryCreateInternal, DeliveryUpdateInternal]):  
    model = DeliveryInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de entregas."""  
        try:  
            # Garantir unicidade e busca rápida por referências  
            await self.collection.create_index("delivery_ref", unique=True)  
            await self.collection.create_index("order_id", unique=True) # Assumindo 1 entrega por pedido

            # Índices para filtros comuns  
            await self.collection.create_index("customer_id")  
            await self.collection.create_index("current_status")  
            await self.collection.create_index("assigned_driver_id", sparse=True) # Pode ser nulo  
            await self.collection.create_index([("created_at", DESCENDING)])  
            await self.collection.create_index([("estimated_delivery_date", ASCENDING)], sparse=True)  
            # Índice no histórico de tracking? Pode ser útil, mas complexo.  
            # await self.collection.create_index("tracking_history.timestamp")

            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    async def get_by_ref(self, delivery_ref: str) -> Optional[DeliveryInDB]:  
        """Busca entrega pela referência."""  
        return await self.get_by({"delivery_ref": delivery_ref})

    async def get_by_order_id(self, order_id: str | ObjectId) -> Optional[DeliveryInDB]:  
        """Busca entrega pelo ID do pedido."""  
        obj_order_id = self._to_objectid(order_id)  
        if not obj_order_id: return None  
        return await self.get_by({"order_id": obj_order_id})

    async def list_by_driver(  
        self,  
        driver_id: ObjectId,  
        status_in: Optional[List[str]] = None, # Adicionar filtro de status  
        skip: int = 0,  
        limit: int = 100  
        ) -> List[DeliveryInDB]:  
        """Lista entregas atribuídas a um motorista, opcionalmente por status."""  
        query: Dict[str, Any] = {"assigned_driver_id": driver_id}  
        if status_in:  
            query["current_status"] = {"$in": status_in}  
        # Ordenar por data estimada e depois por criação  
        sort_order = [("estimated_delivery_date", ASCENDING), ("created_at", ASCENDING)]  
        return await self.list_by(query=query, skip=skip, limit=limit, sort=sort_order)

    async def list_by_status(  
        self,  
        status: str | List[str],  
        skip: int = 0,  
        limit: int = 100  
        ) -> List[DeliveryInDB]:  
         """Lista entregas por um ou mais status."""  
         query = {"current_status": status} if isinstance(status, str) else {"current_status": {"$in": status}}  
         return await self.list_by(query=query, skip=skip, limit=limit, sort=[("created_at", ASCENDING)])

    async def add_tracking_event(self, delivery_id: ObjectId, event: TrackingEvent) -> bool:  
         """Adiciona um evento de rastreamento ao histórico da entrega usando $push."""  
         log = logger.bind(delivery_id=str(delivery_id), event_status=event.status)  
         log.debug("Adicionando evento de tracking...")  
         try:  
             # Preparar evento para inserção (usando model_dump do Pydantic)  
             event_dict = event.model_dump(mode='json') # Garante tipos corretos para Mongo

             result: UpdateResult = await self.collection.update_one(  
                 {"_id": delivery_id},  
                 {  
                     "$push": {  
                         "tracking_history": {  
                             "$each": [event_dict], # Adiciona o evento  
                             "$position": 0,        # Adiciona no início do array (mais recente primeiro)  
                             "$slice": 50           # Opcional: Limitar o tamanho do histórico  
                         }  
                     },  
                     "$set": {"updated_at": datetime.utcnow()} # Atualiza timestamp da entrega  
                 }  
             )  
             if result.modified_count > 0:  
                  log.info("Evento de tracking adicionado com sucesso.")  
                  return True  
             else:  
                  # Pode acontecer se o delivery_id não for encontrado  
                  log.warning("Falha ao adicionar evento de tracking (entrega não encontrada ou erro?).")  
                  return False  
         except Exception as e:  
             self._handle_db_exception(e, "add_tracking_event", delivery_id)  
             return False

    # Update para status, driver, etc., pode usar o BaseRepository.update  
    # Se precisar de lógica mais complexa (validar transição), ela deve ir para o Service.

# Função de dependência FastAPI  
async def get_delivery_repository() -> DeliveryRepository:  
    """FastAPI dependency to get DeliveryRepository instance."""  
    db = get_database()  
    return DeliveryRepository(db)
