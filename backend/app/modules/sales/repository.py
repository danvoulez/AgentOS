# agentos_core/app/modules/sales/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from decimal import Decimal, InvalidOperation  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from pymongo import ReturnDocument, ASCENDING, DESCENDING, UpdateOne  
from pymongo.results import UpdateResult # Importar UpdateResult  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel # Importar BaseModel

from app.core.repository import BaseRepository  
# Importar modelos internos/DB do módulo Sales  
from .models import (  
    ProductInDB, ProductCreateInternal, ProductUpdateInternal, ProductPrices, PriceHistoryEntry,  
    OrderInDB, OrderCreateInternal, OrderUpdateInternal  
)  
# Importar get_database  
from app.core.database import get_database

# --- Repositório de Produtos ---  
PRODUCTS_COLLECTION = "products"

class ProductRepository(BaseRepository[ProductInDB, ProductCreateInternal, ProductUpdateInternal]):  
    model = ProductInDB  
    collection_name = PRODUCTS_COLLECTION

    async def create_indexes(self):  
        """Cria índices para SKU, nome, status e tags."""  
        try:  
            # SKU único (sparse permite múltiplos documentos sem SKU)  
            await self.collection.create_index("sku", unique=True, sparse=True)  
            # Índice de texto para busca no nome/descrição (opcional)  
            # await self.collection.create_index([("name", "text"), ("description", "text")])  
            # Índice normal para busca case-insensitive (requer collation no find)  
            await self.collection.create_index("name") # Usar collation na busca  
            await self.collection.create_index("is_active")  
            await self.collection.create_index("is_kit")  
            await self.collection.create_index("tags", sparse=True) # Índice em array  
            # Índice em preços? Depende das queries. Ex: preço de venda A  
            await self.collection.create_index("prices.sale_a", sparse=True)  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    async def get_by_sku(self, sku: str) -> Optional[ProductInDB]:  
        """Busca produto pelo SKU (case-insensitive se necessário)."""  
        if not sku: return None  
        # Fazer busca case-insensitive se o SKU puder variar  
        # return await self.get_by({"sku": {"$regex": f"^{re.escape(sku)}$", "$options": "i"}})  
        # Ou busca exata se SKU for sempre consistente:  
        return await self.get_by({"sku": sku})

    async def find_by_ids(self, product_ids: List[ObjectId]) -> List[ProductInDB]:  
         """Busca múltiplos produtos por uma lista de ObjectIds."""  
         if not product_ids: return []  
         # Garantir que todos os IDs são válidos? O find ignora os inválidos.  
         valid_ids = [pid for pid in product_ids if isinstance(pid, ObjectId)]  
         if not valid_ids: return []  
         return await self.list_by(query={"_id": {"$in": valid_ids}})

    def _prepare_data_for_db(self, data: Dict) -> Dict:  
        """Converte Decimals em 'prices' para string."""  
        prepared = super()._prepare_data_for_db(data) # Chama base (se houver)  
        if "prices" in prepared:  
            if isinstance(prepared["prices"], BaseModel):  
                 prepared["prices"] = prepared["prices"].model_dump(mode='json') # Usa encoder do modelo  
            elif isinstance(prepared["prices"], dict):  
                 # Conversão manual se for dict (redundante se veio de Pydantic com config)  
                 prepared["prices"] = {k: str(v) if isinstance(v, Decimal) else v  
                                       for k, v in prepared["prices"].items()}  
        # Tratar price_history (lista de objetos que podem ter Decimal)  
        if "price_history" in prepared and isinstance(prepared["price_history"], list):  
            for entry in prepared["price_history"]:  
                 if isinstance(entry, BaseModel):  
                      # Se for Pydantic, a serialização dele deve cuidar disso  
                      pass # Assumindo que model_dump do histórico lida com Decimal  
                 elif isinstance(entry, dict) and "prices" in entry and isinstance(entry["prices"], dict):  
                      entry["prices"] = {k: str(v) if isinstance(v, Decimal) else v  
                                         for k, v in entry["prices"].items()}  
        return prepared

    async def create(self, data_in: ProductCreateInternal | Dict) -> ProductInDB:  
        """Cria produto, inicializando histórico de preço."""  
        if isinstance(data_in, BaseModel):  
            create_data_dict = data_in.model_dump(exclude_unset=False)  
        else:  
            create_data_dict = data_in.copy()

        # Garantir que prices seja um dict pronto para o DB  
        prices_model = ProductPrices.model_validate(create_data_dict.get("prices", {}))  
        create_data_dict["prices"] = prices_model.model_dump(mode='json') # Armazenar como dict/string

        # Criar entrada inicial do histórico  
        initial_reason = create_data_dict.pop("initial_price_reason", "Initial Setup") # Pop para remover  
        initial_user_id = create_data_dict.pop("user_id", None) # Pop se vier user_id aqui

        initial_price_entry = PriceHistoryEntry(  
            user_id=initial_user_id,  
            reason=initial_reason,  
            # Usar preços validados e serializados  
            prices={k: v for k, v in create_data_dict["prices"].items() if v is not None} # Apenas preços não nulos  
        )  
        create_data_dict["price_history"] = [initial_price_entry.model_dump(mode='json')]

        # Preparar o dict final (converter Decimals restantes se houver)  
        create_data_prepared = self._prepare_data_for_db(create_data_dict)

        # Chamar create do BaseRepository  
        return await super().create(create_data_prepared)

    async def update(self, id: str | ObjectId, data_in: ProductUpdateInternal | Dict) -> Optional[ProductInDB]:  
        """Atualiza produto, adicionando ao histórico de preço se 'prices' mudar."""  
        obj_id = self._to_objectid(id)  
        if not obj_id: return None

        # Buscar documento atual para comparar preços  
        current_doc = await self.get_by_id(obj_id)  
        if not current_doc: return None

        if isinstance(data_in, BaseModel):  
            update_data_dict = data_in.model_dump(exclude_unset=True)  
        else:  
            update_data_dict = data_in.copy()

        update_payload = {} # Para $set  
        push_payload = {}   # Para $push

        price_update_reason = update_data_dict.pop("price_update_reason", "Update via API")  
        user_id_updater = update_data_dict.pop("user_id", None) # Capturar quem atualiza

        # Tratar atualização de 'prices'  
        new_prices_data = update_data_dict.pop("prices", None) # Remover prices do dict principal  
        if new_prices_data is not None:  
            try:  
                new_prices_model = ProductPrices.model_validate(new_prices_data)  
                # Comparar com preços atuais (já são Decimal no modelo Pydantic current_doc.prices)  
                if new_prices_model != current_doc.prices:  
                    logger.info(f"Detectada mudança de preço para produto {id}.")  
                    update_payload["prices"] = new_prices_model.model_dump(mode='json') # Atualizar campo principal

                    price_entry = PriceHistoryEntry(  
                        user_id=user_id_updater,  
                        reason=price_update_reason,  
                        prices={k: str(v) for k, v in new_prices_model.model_dump(exclude_none=True).items()}  
                    )  
                    push_payload["price_history"] = price_entry.model_dump(mode='json')  
                else:  
                     logger.debug(f"Update de produto {id} continha 'prices', mas sem alteração real.")  
            except Exception as e:  
                 logger.error(f"Erro ao processar 'prices' no update do produto {id}: {e}")  
                 raise ValueError(f"Invalid 'prices' data provided: {e}")

        # Adicionar outros campos ao $set (preparando para DB)  
        other_updates_prepared = self._prepare_data_for_db(update_data_dict)  
        for key, value in other_updates_prepared.items():  
             if key not in ["_id", "id", "created_at", "price_history", "reserved_stock"]: # Campos protegidos  
                 update_payload[key] = value

        if not update_payload and not push_payload:  
            logger.debug(f"Update chamado para produto {id} sem alterações detectadas.")  
            return current_doc

        # Adicionar updated_at ao $set  
        update_payload["updated_at"] = datetime.utcnow()

        # Construir operação final  
        final_update_op = {}  
        if update_payload: final_update_op["$set"] = update_payload  
        if push_payload:  
            final_update_op["$push"] = {  
                "price_history": { "$each": [push_payload["price_history"]], "$position": 0, "$slice": 50 }  
            }

        # Executar update_one  
        try:  
            result: UpdateResult = await self.collection.update_one({"_id": obj_id}, final_update_op)  
            # Mesmo se modified_count for 0 (só $push), retornar o doc atualizado  
            if result.matched_count == 0: return None  
            logger.debug(f"Produto atualizado: ID {id}, Matched: {result.matched_count}, Modified: {result.modified_count}, Upserted: {result.upserted_id}")  
            return await self.get_by_id(obj_id)  
        except Exception as e:  
            self._handle_db_exception(e, "update", obj_id) # Loga e levanta erro  
            raise # Re-raise a exceção que _handle_db_exception levantou

    async def update_stock_atomic(self, product_id: ObjectId, quantity_change: int, is_reservation: bool = False) -> bool:  
        """  
        Atualiza estoque atomicamente (stock_quantity e/ou reserved_stock).  
        Retorna True se bem-sucedido, False se estoque ficaria negativo ou erro.  
        """  
        log = logger.bind(product_id=str(product_id), change=quantity_change, type="reservation" if is_reservation else "physical")  
        log.info("Atualizando estoque atomicamente...")

        # Definir a query de filtro e a operação de update  
        query = {"_id": product_id}  
        update_op = {"$set": {"updated_at": datetime.utcnow()}}

        if is_reservation:  
            # Reservar: Incrementar reserved_stock (quantity_change deve ser positivo)  
            # Liberar Reserva: Decrementar reserved_stock (quantity_change deve ser negativo)  
            if quantity_change > 0: # Reservando  
                 query["stock_quantity"] = {"$gte": quantity_change} # Precisa ter estoque físico  
                 # Não verificar reserved_stock aqui, apenas físico  
            # else: Liberando, não precisa checar gte 0 em reserved? Sim, precisa.  
            if quantity_change < 0: # Liberando reserva  
                 query["reserved_stock"] = {"$gte": abs(quantity_change)} # Precisa ter reserva suficiente

            update_op["$inc"] = {"reserved_stock": quantity_change}  
            log.debug(f"Operação de reserva/liberação: Query={query}, Update={update_op}")

        else: # Atualização de estoque físico (confirmação de venda ou entrada)  
             # Confirmar Venda: Decrementar stock_quantity E reserved_stock (quantity_change < 0)  
             # Entrada Estoque: Incrementar stock_quantity (quantity_change > 0)  
             abs_change = abs(quantity_change)  
             if quantity_change < 0: # Saída de estoque (confirmação)  
                  query["stock_quantity"] = {"$gte": abs_change}  
                  query["reserved_stock"] = {"$gte": abs_change} # Precisa ter reserva E físico  
                  update_op["$inc"] = {"stock_quantity": quantity_change, "reserved_stock": quantity_change}  
             else: # Entrada de estoque  
                  update_op["$inc"] = {"stock_quantity": quantity_change}  
             log.debug(f"Operação de estoque físico: Query={query}, Update={update_op}")

        try:  
            # Usar find_one_and_update para garantir que a condição da query é atendida atomicamente  
            # Se a query não encontrar (ex: estoque insuficiente), result será None  
            result = await self.collection.find_one_and_update(query, update_op)  
            success = result is not None  
            if success: log.success("Atualização atômica de estoque bem-sucedida.")  
            else: log.warning("Atualização atômica de estoque falhou (condição não atendida - ex: estoque insuficiente?).")  
            return success  
        except Exception as e:  
             self._handle_db_exception(e, "update_stock_atomic", product_id)  
             return False

# --- Repositório de Pedidos ---  
ORDERS_COLLECTION = "orders"

class OrderRepository(BaseRepository[OrderInDB, OrderCreateInternal, OrderUpdateInternal]):  
    model = OrderInDB  
    collection_name = ORDERS_COLLECTION

    async def create_indexes(self):  
        """Cria índices para referência, cliente, status e data."""  
        try:  
            await self.collection.create_index("order_ref", unique=True)  
            await self.collection.create_index("customer_id")  
            await self.collection.create_index("status")  
            await self.collection.create_index([("created_at", DESCENDING)])  
            await self.collection.create_index("channel", sparse=True) # Índice se filtrar por canal  
            # Índice em itens? Ex: itens.product_id (se precisar buscar pedidos por produto)  
            await self.collection.create_index("items.product_id")  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    def _prepare_data_for_db(self, data: Dict) -> Dict:  
        """Converte Decimals para string em total_amount e items."""  
        prepared = super()._prepare_data_for_db(data)  
        if "total_amount" in prepared and isinstance(prepared.get("total_amount"), Decimal):  
            prepared["total_amount"] = str(prepared["total_amount"])  
        if "items" in prepared and isinstance(prepared.get("items"), list):  
            for item in prepared["items"]:  
                if isinstance(item, dict):  
                    if "price_at_purchase" in item and isinstance(item.get("price_at_purchase"), Decimal):  
                        item["price_at_purchase"] = str(item["price_at_purchase"])  
                    if "margin_at_purchase" in item and isinstance(item.get("margin_at_purchase"), Decimal):  
                        item["margin_at_purchase"] = str(item["margin_at_purchase"])  
                elif isinstance(item, BaseModel): # Se for Pydantic, deixar serializar  
                    pass  
        return prepared

    async def create(self, data_in: OrderCreateInternal | Dict) -> OrderInDB:  
        """Cria pedido, tratando Decimals."""  
        if isinstance(data_in, BaseModel):  
             create_data_dict = data_in.model_dump(exclude_unset=False)  
        else:  
             create_data_dict = data_in.copy()  
        # Preparar dados (converter Decimal)  
        create_data_prepared = self._prepare_data_for_db(create_data_dict)  
        return await super().create(create_data_prepared)

    async def update(self, id: str | ObjectId, data_in: OrderUpdateInternal | Dict) -> Optional[OrderInDB]:  
        """Atualiza pedido, tratando Decimals se houver campos."""  
        if isinstance(data_in, BaseModel):  
             update_data_dict = data_in.model_dump(exclude_unset=True)  
        else:  
             update_data_dict = data_in.copy()  
        # Preparar dados (tratar Decimals se houver campos atualizáveis com Decimal)  
        update_data_prepared = self._prepare_data_for_db(update_data_dict)  
        return await super().update(id, update_data_prepared)

    async def get_by_ref(self, order_ref: str) -> Optional[OrderInDB]:  
        """Busca pedido pela referência."""  
        return await self.get_by({"order_ref": order_ref})

    async def list_by_customer(self, customer_id: ObjectId, skip: int = 0, limit: int = 10) -> List[OrderInDB]:  
        """Lista pedidos de um cliente."""  
        return await self.list_by(  
            query={"customer_id": customer_id},  
            skip=skip,  
            limit=limit,  
            sort=[("created_at", DESCENDING)]  
        )

    # Adicionar método para buscar pedidos para o relatório financeiro? Ou usar list_by?  
    async def list_orders_for_report(  
        self,  
        start_date: datetime,  
        end_date: datetime,  
        valid_statuses: List[str],  
        channel: Optional[str] = None  
    ) -> List[OrderInDB]:  
        """Busca pedidos filtrados para relatórios."""  
        query: Dict[str, Any] = {  
            "created_at": {"$gte": start_date, "$lte": end_date},  
            "status": {"$in": valid_statuses}  
        }  
        if channel:  
            query["channel"] = channel  
        # Retornar lista completa para agregação no service? Ou agregar aqui?  
        # Por enquanto, retornar lista. Cuidado com performance para grandes volumes.  
        logger.debug(f"Buscando pedidos para relatório com query: {query}")  
        # Usar limit=0 para buscar todos? Perigoso. Adicionar um limite alto? Ou paginação?  
        # Por segurança, manter um limite alto padrão ou exigir paginação no service.  
        MAX_ORDERS_FOR_REPORT = 10000  
        return await self.list_by(query=query, limit=MAX_ORDERS_FOR_REPORT, sort=[("created_at", ASCENDING)])

# Funções de dependência FastAPI  
async def get_product_repository() -> ProductRepository:  
    db = get_database()  
    return ProductRepository(db)

async def get_order_repository() -> OrderRepository:  
    db = get_database()  
    return OrderRepository(db)

# Importar re para regex (se usado em get_by_sku)  
import re
