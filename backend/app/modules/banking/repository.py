# agentos_core/app/modules/banking/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from decimal import Decimal, InvalidOperation  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase  
from pymongo import ASCENDING, DESCENDING  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import TransactionInDB, TransactionCreateInternal, TransactionUpdateInternal # Usar modelos internos

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "transactions"

class TransactionRepository(BaseRepository[TransactionInDB, TransactionCreateInternal, TransactionUpdateInternal]):  
    model = TransactionInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de transações."""  
        try:  
            await self.collection.create_index("transaction_ref", unique=True)  
            await self.collection.create_index("type")  
            await self.collection.create_index("status")  
            await self.collection.create_index("associated_order_id", sparse=True)  
            await self.collection.create_index("associated_user_id", sparse=True)  
            await self.collection.create_index([("timestamp", DESCENDING)]) # Principal para buscas recentes  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    def _prepare_data_for_db(self, data: Dict) -> Dict:  
        """Converte Decimals para string antes de salvar."""  
        prepared = data.copy() # Evitar modificar original  
        try:  
            if "amount" in prepared and isinstance(prepared.get("amount"), Decimal):  
                 # O modelo Pydantic já deve ter arredondado, apenas converter  
                 prepared["amount"] = str(prepared["amount"])  
        except Exception as e:  
            logger.error(f"Erro ao preparar campo 'amount' para DB: {prepared.get('amount')} - {e}")  
            raise ValueError("Invalid value provided for 'amount'")  
        return prepared

    async def create(self, data_in: TransactionCreateInternal | Dict) -> TransactionInDB:  
        """Cria transação, tratando Decimal e adicionando timestamp."""  
        if isinstance(data_in, BaseModel):  
            create_data_dict = data_in.model_dump(exclude_unset=False)  
        else:  
            create_data_dict = data_in.copy()

        # Garantir timestamp e preparar dados  
        create_data_dict.setdefault("timestamp", datetime.utcnow())  
        create_data_prepared = self._prepare_data_for_db(create_data_dict)

        # transaction_ref é adicionado pelo Service antes de chamar create  
        if "transaction_ref" not in create_data_prepared:  
             logger.error("Tentativa de criar transação sem transaction_ref.")  
             raise ValueError("Transaction reference is required for creation.")

        return await super().create(create_data_prepared)

    async def update(self, id: str | ObjectId, data_in: TransactionUpdateInternal | Dict) -> Optional[TransactionInDB]:  
        """Atualiza transação, tratando campos imutáveis."""  
        if isinstance(data_in, BaseModel):  
            update_data_dict = data_in.model_dump(exclude_unset=True)  
        else:  
            update_data_dict = data_in.copy()

        # Preparar dados (se houver campos Decimal atualizáveis)  
        update_data_prepared = self._prepare_data_for_db(update_data_dict)

        # Remover campos imutáveis explicitamente (mesmo que BaseRepository tente)  
        immutable_fields = ["amount", "currency", "type", "associated_order_id",  
                            "associated_user_id", "transaction_ref", "timestamp",  
                            "created_at", "_id", "id"]  
        for field in immutable_fields:  
            update_data_prepared.pop(field, None)

        if not update_data_prepared:  
             logger.warning(f"Tentativa de update em Transaction {id} sem dados alteráveis.")  
             return await self.get_by_id(id) # Retorna o doc atual

        return await super().update(id, update_data_prepared)

    async def list_by_order_id(self, order_id: ObjectId) -> List[TransactionInDB]:  
        """Lista transações associadas a um pedido."""  
        return await self.list_by(query={"associated_order_id": order_id}, sort=[("timestamp", ASCENDING)])

    async def list_by_filter(  
        self,  
        start_date: Optional[datetime] = None,  
        end_date: Optional[datetime] = None,  
        transaction_type: Optional[str] = None,  
        status: Optional[str] = None,  
        order_id_str: Optional[str] = None, # <<< Renomear para clareza  
        user_id_str: Optional[str] = None,  # <<< Renomear para clareza  
        skip: int = 0,  
        limit: int = 100  
    ) -> List[TransactionInDB]:  
        """Lista transações com filtros."""  
        query: Dict[str, Any] = {}  
        if start_date or end_date:  
            query["timestamp"] = {}  
            if start_date: query["timestamp"]["$gte"] = start_date  
            if end_date: query["timestamp"]["$lte"] = end_date # Ajustar para fim do dia se necessário  
        if transaction_type: query["type"] = transaction_type  
        if status: query["status"] = status

        obj_order_id = self._to_objectid(order_id_str) if order_id_str else None  
        if obj_order_id: query["associated_order_id"] = obj_order_id

        obj_user_id = self._to_objectid(user_id_str) if user_id_str else None  
        if obj_user_id: query["associated_user_id"] = obj_user_id

        return await self.list_by(query=query, skip=skip, limit=limit, sort=[("timestamp", DESCENDING)])

# Função de dependência FastAPI  
async def get_transaction_repository() -> TransactionRepository:  
    """FastAPI dependency to get TransactionRepository instance."""  
    db = get_database()  
    return TransactionRepository(db)
