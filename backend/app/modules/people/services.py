\# agentos_core/app/modules/sales/services.py

import asyncio  
from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime  
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP \# Adicionar ROUND_HALF_UP  
from bson import ObjectId  
from fastapi import HTTPException, status  
from loguru import logger  
from pydantic import BaseModel \# Importar BaseModel

\# Repositórios e Modelos Internos/DB  
from .repository import ProductRepository, OrderRepository  
from .models import (  
    ProductInDB, ProductCreateInternal, ProductUpdateInternal, ProductPrices,  
    OrderInDB, OrderCreateInternal, OrderUpdateInternal, OrderItemInternal, OrderItemCreateInternal  
)  
\# Modelos API (para tipo de retorno ou validação interna)  
from app.models.sales import Product, Order, OrderItem, ProductCreateAPI, OrderCreateAPI \# etc.

\# Outros Serviços e Repos necessáriso  
from app.core.counters import CounterService  
from .reservation_service import StockReservationService, ReservationError  
from app.modules.people.repository import UserRepository  
from app.modules.people.models import UserInDB \# Para tipo de customer  
from app.modules.banking.services import BankingService \# Para registrar transação  
from app.modules.banking.repository import TransactionRepository  
from app.modules.banking.models import TransactionCreateInternal  
from app.modules.stock.services import StockService \# Para marcar itens vendidos  
from app.modules.stock.repository import StockItemRepository

\# Eventos PubSub (se implementado)  
\# from app.core.redis_pubsub import publish_event

\# Configurações  
from app.core.config import settings

\# \--- Service de Produtos \---

class ProductService:  
    \\"\\"\\"Lógica de negócio para Produtos.\\"\\"\\"

    async def create_product(  
        self,  
        product_in: ProductCreateAPI, \# Recebe modelo API  
        product_repo: ProductRepository,  
        current_user: UserInDB \# Para histórico de preço  
    ) \-\> ProductInDB:  
        \\"\\"\\"Cria um novo produto.\\"\\"\\"  
        log \= logger.bind(sku=product_in.sku, name=product_in.name)  
        log.info(\\"Service: Criando novo produto...\\")

        \# Converter preços string da API para Decimal  
        try:  
            prices_internal \= ProductPrices.model_validate(product_in.prices)  
        except Exception as e:  
             log.warning(f\\"Dados de preço inválidos no payload de criação: {product_in.prices} \- {e}\\")  
             raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f\\"Invalid price data: {e}\\")

        \# Preparar dados internos  
        product_internal_data \= product_in.model_dump(exclude={\\"prices\\"})  
        product_internal_data\[\\"prices\\"\] \= prices_internal \# Usar modelo Pydantic validado  
        \# Adicionar info para histórico inicial  
        product_internal_data\[\\"initial_price_reason\\"\] \= \\"Criação via API\\"  
        product_internal_data\[\\"user_id\\"\] \= current_user.id \# ID de quem criou/definiu preço inicial

        try:  
            \# Usar repo.create que lida com histórico e timestamps  
            created_db \= await product_repo.create(product_internal_data)  
            log.success(f\\"Produto criado com sucesso. ID: {created_db.id}\\")  
            return created_db  
        except ValueError as e: \# DuplicateKey etc.  
             log.warning(f\\"Falha ao criar produto: {e}\\")  
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))  
        except RuntimeError as e: \# Erro DB genérico  
             log.error(f\\"Erro de DB ao criar produto: {e}\\")  
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def update_product(  
        self,  
        product_id_str: str,  
        product_in: ProductUpdateAPI, \# Modelo API  
        product_repo: ProductRepository,  
        current_user: UserInDB \# Para histórico de preço  
    ) \-\> Optional\[ProductInDB\]:  
        \\"\\"\\"Atualiza um produto existente.\\"\\"\\"  
        log \= logger.bind(product_id=product_id_str)  
        log.info(\\"Service: Atualizando produto...\\")

        product_id \= product_repo._to_objectid(product_id_str)  
        if not product_id:  
             log.warning(\\"ID de produto inválido para update.\\")  
             return None \# Router tratará como 404 ou 400

        update_data_internal: Dict\[str, Any\] \= {}

        \# Converter preços string para Decimal se fornecido  
        if product_in.prices is not None:  
             try:  
                 prices_internal \= ProductPrices.model_validate(product_in.prices)  
                 update_data_internal\[\\"prices\\"\] \= prices_internal \# Passar modelo Pydantic para repo  
                 \# Passar razão e usuário para histórico (repo.update pega do dict)  
                 if product_in.price_update_reason is None:  
                      raise ValueError(\\"price_update_reason is required when updating prices.\\")  
                 update_data_internal\[\\"price_update_reason\\"\] \= product_in.price_update_reason  
                 update_data_internal\[\\"user_id\\"\] \= current_user.id  
             except Exception as e:  
                  log.warning(f\\"Dados de preço inválidos no payload de atualização: {product_in.prices} \- {e}\\")  
                  raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f\\"Invalid price data: {e}\\")

        \# Adicionar outros campos do payload de update API  
        update_payload_api \= product_in.model_dump(exclude={\\"prices\\"}, exclude_unset=True)  
        update_data_internal.update(update_payload_api)

        if not update_data_internal:  
             log.info(\\"Nenhum dado fornecido para atualização do produto.\\")  
             return await product_repo.get_by_id(product_id) \# Retornar atual

        try:  
            updated_db \= await product_repo.update(product_id, update_data_internal)  
            if not updated_db:  
                 log.warning(\\"Produto não encontrado ou falha no update.\\")  
                 \# Repo retorna None se não encontrou, service repassa  
                 return None  
            log.success(f\\"Produto atualizado com sucesso.\\")  
            return updated_db  
        except ValueError as e: \# Duplicate SKU, etc.  
            log.warning(f\\"Falha ao atualizar produto: {e}\\")  
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))  
        except RuntimeError as e: \# Erro DB genérico  
            log.error(f\\"Erro de DB ao atualizar produto: {e}\\")  
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    async def get_product(self, product_id_str: str, product_repo: ProductRepository) \-\> Optional\[ProductInDB\]:  
        \\"\\"\\"Busca um produto pelo ID.\\"\\"\\"  
        log \= logger.bind(product_id=product_id_str)  
        log.debug(\\"Service: Buscando produto por ID...\\")  
        product \= await product_repo.get_by_id(product_id_str)  
        if not product: log.info(\\"Produto não encontrado.\\")  
        return product

    async def list_products(self, product_repo: ProductRepository, skip: int \= 0, limit: int \= 100, active_only: bool \= True) \-\> List\[ProductInDB\]:  
        \\"\\"\\"Lista produtos com paginação.\\"\\"\\"  
        logger.debug(f\\"Service: Listando produtos (skip={skip}, limit={limit}, active_only={active_only})...\\")  
        query \= {\\"is_active\\": True} if active_only else {}  
        \# Adicionar ordenação padrão? Ex: por nome  
        sort_order \= \[(\\"name\\", ASCENDING)\] \# Importar ASCENDING  
        return await product_repo.list_by(query=query, skip=skip, limit=limit, sort=sort_order)

    async def deactivate_product(self, product_id_str: str, product_repo: ProductRepository) \-\> bool:  
        \\"\\"\\"Marca um produto como inativo (deleção lógica).\\"\\"\\"  
        log \= logger.bind(product_id=product_id_str)  
        log.info(\\"Service: Desativando produto...\\")  
        \# Usar método específico do repo  
        updated_product \= await product_repo.set_active_status(product_id_str, is_active=False)  
        success \= updated_product is not None  
        if success: log.success(\\"Produto desativado com sucesso.\\")  
        else: log.warning(\\"Produto não encontrado ou já estava inativo.\\")  
        return success

\# \--- Service de Pedidos \---

class OrderService:  
    \\"\\"\\"Lógica de negócio para Pedidos.\\"\\"\\"

    \# Helper de seleção de preço (mantido como antes)  
    def _select_price_tier(self, product: ProductInDB, customer_profile_type: Optional\[str\], channel: Optional\[str\]) \-\> Tuple\[str, Optional\[Decimal\]\]:  
        \# (Lógica de seleção de preço como implementada anteriormente)  
        prices \= product.prices  
        profile_to_sale_tiers \= {\\"vip\\": \[\\"sale_a\\", \\"sale_b\\"\], \\"reseller\\": \[\\"resale_a\\", \\"resale_b\\"\], \\"regular\\": \[\\"sale_c\\", \\"sale_b\\", \\"sale_a\\"\]}  
        channel_to_sale_tiers \= {\\"whatsapp\\": \[\\"sale_b\\", \\"sale_a\\"\], \\"ui\\": \[\\"sale_a\\"\]}  
        default_tier_order \= \[\\"sale_a\\", \\"sale_b\\", \\"sale_c\\", \\"resale_a\\", \\"resale_b\\", \\"resale_c\\"\] \# Ordem de fallback  
        tiers_to_try: List\[str\] \= \[\]  
        if channel and channel in channel_to_sale_tiers: tiers_to_try.extend(channel_to_sale_tiers\[channel\])  
        if customer_profile_type and customer_profile_type in profile_to_sale_tiers: tiers_to_try.extend(profile_to_sale_tiers\[customer_profile_type\])  
        tiers_to_try.extend(default_tier_order)  
        for tier in tiers_to_try:  
            price \= getattr(prices, tier, None)  
            if price is not None: return tier, price  
        return \\"default\\", None

    \# Helper de processamento de itens (mantido como antes)  
    async def _process_order_items(  
        self,  
        items_in: List\[OrderItemCreateInternal\], \# Recebe modelo interno  
        product_repo: ProductRepository,  
        customer_profile_type: Optional\[str\],  
        channel: Optional\[str\]  
    ) \-\> Tuple\[List\[OrderItemInternal\], Decimal, List\[Tuple\[ObjectId, int\]\]\]: \# Retorna modelo interno  
        \# (Lógica como implementada anteriormente, usando _select_price_tier e calculando margem/total com Decimal)  
        processed_items: List\[OrderItemInternal\] \= \[\]  
        total_amount \= Decimal(\\"0.0\\")  
        stock_updates: List\[Tuple\[ObjectId, int\]\] \= \[\]  
        product_ids_obj \= \[product_repo._to_objectid(item.product_id) for item in items_in\] \# Validar/Converter aqui  
        valid_product_ids \= \[pid for pid in product_ids_obj if pid\]  
        if len(valid_product_ids) \!= len(items_in): raise HTTPException(400, \\"Invalid product_id format in items.\\")

        products \= await product_repo.find_by_ids(valid_product_ids)  
        products_map \= {str(prod.id): prod for prod in products}

        for item_in in items_in:  
            product_id_str \= str(item_in.product_id)  
            product \= products_map.get(product_id_str)  
            obj_product_id \= product_repo._to_objectid(product_id_str) \# Já validado

            if not product: raise HTTPException(404, f\\"Product {product_id_str} not found\\")  
            if not product.is_active: raise HTTPException(400, f\\"Product '{product.name}' unavailable\\")

            selected_tier, price_at_purchase \= self._select_price_tier(product, customer_profile_type, channel)  
            if price_at_purchase is None: raise HTTPException(400, f\\"No price found for product '{product.name}'\\")

            \# Validar estoque disponível (AGORA USA A PROPERTY)  
            if product.available_stock \< item_in.quantity:  
                raise HTTPException(400, f\\"Insufficient available stock for '{product.name}'. Available: {product.available_stock}\\")

            try:  
                quantity_decimal \= Decimal(item_in.quantity)  
                item_total \= price_at_purchase \* quantity_decimal  
                total_amount \+= item_total  
                margin: Optional\[Decimal\] \= None  
                if product.prices.cost is not None:  
                    margin \= (price_at_purchase \- product.prices.cost) \* quantity_decimal  
                    margin \= margin.quantize(Decimal(\\"0.01\\"), rounding=ROUND_HALF_UP)  
            except Exception as e: raise HTTPException(500, f\\"Calculation error for '{product.name}': {e}\\")

            processed_item \= OrderItemInternal( \# \<\<\< Usar modelo interno  
                product_id=obj_product_id,  
                quantity=item_in.quantity,  
                product_name=product.name,  
                price_at_purchase=price_at_purchase, \# Decimal  
                selected_price_tier=selected_tier,  
                margin_at_purchase=margin \# Decimal ou None  
            )  
            processed_items.append(processed_item)  
            stock_updates.append((obj_product_id, \-item_in.quantity)) \# Negativo para diminuir

        return processed_items, total_amount.quantize(Decimal(\\"0.01\\"), rounding=ROUND_HALF_UP), stock_updates

    \# Helper de validação de cliente (pode ser movido para people.services?)  
    async def _validate_customer(self, customer_id: ObjectId, user_repo: UserRepository):  
        customer \= await user_repo.get_by_id(customer_id)  
        if not customer: raise HTTPException(404, f\\"Customer with ID {customer_id} not found\\")  
        if not customer.is_active: raise HTTPException(400, \\"Customer account is inactive\\")  
        \# Verificar se tem role 'customer'? Opcional.  
        \# if \\"customer\\" not in customer.roles: raise HTTPException(400, \\"User is not a customer\\")  
        return customer \# Retornar cliente para pegar perfil

    async def create_order(  
        self,  
        order_in: OrderCreateAPI, \# Recebe modelo API  
        creator: UserInDB, \# Usuário logado  
        order_repo: OrderRepository,  
        product_repo: ProductRepository,  
        user_repo: UserRepository,  
        counter_service: CounterService,  
        reservation_service: StockReservationService,  
        audit_service: AuditService \# Para log interno se necessário  
        \# Não injetar banking_service aqui, será chamado no update_status  
    ) \-\> OrderInDB: \# Retorna modelo DB  
        \\"\\"\\"Cria um novo pedido, processa itens, reserva estoque.\\"\\"\\"  
        log \= logger.bind(user_id=str(creator.id), channel=order_in.channel)  
        log.info(\\"Service: Criando novo pedido...\\")  
        customer_id \= creator.id \# Pedido é sempre do usuário logado

        \# Validar cliente (redundante se creator é UserInDB ativo, mas boa prática)  
        customer \= await self._validate_customer(customer_id, user_repo)

        \# Determinar perfil do cliente para cálculo de preço  
        customer_profile_type \= order_in.customer_profile_type \# Vem da API?  
        if not customer_profile_type: \# Inferir das roles se não vier da API  
             customer_profile_type \= \\"reseller\\" if \\"reseller\\" in customer.roles else (\\"vip\\" if \\"vip\\" in customer.roles else \\"regular\\")  
        log.debug(f\\"Usando perfil '{customer_profile_type}' e canal '{order_in.channel}' para preços.\\")

        \# Converter itens da API para modelo interno  
        items_internal \= \[OrderItemCreateInternal(\*\*item.model_dump()) for item in order_in.items\]

        \# Processar Itens (valida estoque, calcula total/margem)  
        try:  
             processed_items, total_amount_decimal, stock_updates \= await self._process_order_items(  
                 items_internal, product_repo, customer_profile_type, order_in.channel  
             )  
        except HTTPException as http_exc:  
             log.warning(f\\"Falha no processamento de itens do pedido: {http_exc.detail}\\")  
             \# Logar auditoria de falha aqui? Ou deixar o router? Router é melhor.  
             raise http_exc \# Re-propagar erro 4xx para o router

        \# Gerar Referência  
        try:  
            order_ref \= await counter_service.generate_reference(\\"ORD\\")  
        except Exception as e: \# Capturar erro da geração de referência  
             raise HTTPException(status_code=500, detail=f\\"Failed to generate order reference: {e}\\")

        \# Preparar dados para salvar no DB (usando modelo interno)  
        order_data_internal \= OrderCreateInternal(  
            customer_id=customer_id,  
            order_ref=order_ref, \# Adicionar ref aqui  
            items=processed_items, \# Lista de OrderItemInternal  
            total_amount=total_amount_decimal, \# Decimal  
            status=\\"pending\\", \# Status inicial  
            channel=order_in.channel,  
            shipping_address=order_in.shipping_address,  
            billing_address=order_in.billing_address,  
            \# delivery_id, transaction_ids são None/\[\] por padrão  
        )  
        order_data_dict \= order_data_internal.model_dump()

        \# Reservar estoque via Reservation Service  
        reservation_id \= order_ref \# Usar order_ref como ID da reserva  
        log.info(f\\"Tentando reservar estoque para {len(stock_updates)} itens (ResID: {reservation_id})...\\")  
        reserve_tasks \= \[reservation_service.reserve_stock(reservation_id, pid, abs(qty)) for pid, qty in stock_updates\]  
        reserve_results \= await asyncio.gather(\*reserve_tasks, return_exceptions=True)

        failed_reservations \= \[info for info, res in zip(stock_updates, reserve_results) if isinstance(res, Exception) or not res\]  
        if failed_reservations:  
            log.error(f\\"Falha ao reservar estoque para pedido (ResID: {reservation_id}). Falhas: {failed_reservations}. Tentando rollback...\\")  
            \# Tentar liberar reservas bem-sucedidas  
            successful_products \= \[info\[0\] for info, res in zip(stock_updates, reserve_results) if not isinstance(res, Exception) and res\]  
            if successful_products:  
                release_tasks \= \[reservation_service._release_or_confirm_single(reservation_id, str(pid), confirm=False) for pid in successful_products\]  
                await asyncio.gather(\*release_tasks, return_exceptions=True) \# Logar erros de rollback  
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=\\"Stock reservation failed for one or more items.\\")  
        log.success(f\\"Reserva de estoque bem-sucedida para pedido {order_ref}.\\")

        \# Salvar Pedido no DB  
        try:  
            created_order_db \= await order_repo.create(order_data_dict) \# Repo lida com conversão Decimal  
            log.success(f\\"Pedido {order_ref} criado com sucesso no DB.\\")  
            \# Disparar evento Redis (opcional)  
            \# await publish_event(\\"sales.order.created\\", created_order_db.model_dump(mode='json'))  
            return created_order_db \# Retorna modelo DB  
        except (ValueError, RuntimeError) as e:  
            log.exception(f\\"Falha ao salvar pedido {order_ref} após reserva de estoque: {e}\\")  
            \# Tentar liberar TODAS as reservas feitas para este ID como melhor esforço  
            log.error(\\"Tentando liberar reservas após falha ao salvar pedido...\\")  
            await reservation_service.release_reservation(reservation_id) \# Chamar liberação geral  
            raise HTTPException(status_code=500, detail=f\\"Could not save order after reserving stock: {e}\\")

    async def update_order_status(  
        self,  
        order_id_str: str,  
        new_status: str, \# Validado pelo payload API ou aqui  
        notes: Optional\[str\], \# Notas adicionais para a mudança  
        order_repo: OrderRepository,  
        reservation_service: StockReservationService,  
        \# Dependências para ações disparadas pela mudança de status  
        banking_service: BankingService,  
        banking_repo: TransactionRepository,  
        counter_service: CounterService,  
        stock_service: StockService,  
        stock_item_repo: StockItemRepository,  
        audit_service: AuditService, \# Para log interno se service mudar status  
        \# current_user: UserInDB \# Para saber quem mudou o status  
    ) \-\> Optional\[OrderInDB\]:  
        \\"\\"\\"Atualiza o status de um pedido e dispara ações relacionadas (reserva, transação, RFID).\\"\\"\\"  
        log \= logger.bind(order_id=order_id_str, new_status=new_status)  
        log.info(\\"Service: Atualizando status do pedido...\\")

        order_id \= order_repo._to_objectid(order_id_str)  
        if not order_id: raise HTTPException(400, \\"Invalid Order ID format\\")

        order \= await order_repo.get_by_id(order_id)  
        if not order:  
            log.warning(\\"Pedido não encontrado.\\")  
            return None \# Router trata 404  
        current_status \= order.status

        if new_status \== current_status:  
            log.info(\\"Status do pedido já é o desejado. Nenhuma alteração.\\")  
            return order

        \# Validar transição de status (Exemplo simples)  
        valid_transitions \= {  
            \\"pending\\": \[\\"confirmed\\", \\"processing\\", \\"cancelled\\", \\"failed\\"\],  
            \\"confirmed\\": \[\\"processing\\", \\"awaiting_shipment\\", \\"cancelled\\", \\"failed\\"\],  
            \\"processing\\": \[\\"awaiting_shipment\\", \\"shipped\\", \\"cancelled\\", \\"failed\\"\],  
            \\"awaiting_shipment\\": \[\\"shipped\\", \\"cancelled\\", \\"failed\\"\],  
            \\"shipped\\": \[\\"delivered\\", \\"returned\\", \\"failed\\"\], \# Pode falhar na entrega  
            \\"delivered\\": \[\\"returned\\"\], \# Cliente pode devolver?  
            \\"cancelled\\": \[\], \# Não pode sair de cancelado?  
            \\"failed\\": \[\],    \# Não pode sair de falha? (Retry faria isso voltando pra pending?)  
            \\"returned\\": \[\],   \# Estado final?  
        }  
        if new_status not in valid_transitions.get(current_status, \[\]):  
             msg \= f\\"Invalid status transition from '{current_status}' to '{new_status}'.\\"  
             log.warning(msg)  
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

        log.info(f\\"Transição de status válida: {current_status} \-\> {new_status}\\")

        \# \--- Ações baseadas na Transição \---  
        \# 1\. Processar Reserva de Estoque  
        try:  
            reservation_id \= order.order_ref  
            if new_status in \[\\"cancelled\\", \\"failed\\", \\"returned\\"\] and current_status \!= new_status:  
                log.debug(f\\"Liberando reserva de estoque para pedido {reservation_id}...\\")  
                await reservation_service.release_reservation(reservation_id)  
            elif new_status in \[\\"confirmed\\", \\"paid\\", \\"processing\\"\] and current_status \== \\"pending\\":  
                log.debug(f\\"Confirmando reserva de estoque para pedido {reservation_id}...\\")  
                await reservation_service.confirm_reservation(reservation_id)  
                \# Após confirmar, o estoque físico foi debitado.  
        except ReservationError as e:  
             log.error(f\\"Erro ao processar reserva para pedido {reservation_id}: {e}\\")  
             \# Impedir a mudança de status ou continuar? Continuar e logar erro por enquanto.  
             \# Poderia adicionar um flag 'stock_inconsistent' ao pedido?  
             \# raise HTTPException(status_code=500, detail=f\\"Failed to update stock reservation: {e}\\")

        \# 2\. Registrar Transação Bancária (Ex: ao confirmar ou marcar como pago)  
        transaction_recorded \= False  
        \# Ajustar condição: registrar quando for confirmado E pago? Ou só confirmado?  
        \# Vamos registrar em 'processing' ou 'awaiting_shipment' assumindo que confirmação implica pagamento aqui.  
        if new_status in \[\\"processing\\", \\"awaiting_shipment\\", \\"paid\\"\] and current_status in \[\\"pending\\", \\"confirmed\\"\]:  
             log.debug(f\\"Registrando transação de receita para pedido {order.order_ref}...\\")  
             try:  
                 \# Garantir que total_amount é Decimal  
                 total_amount_decimal \= order.total_amount \# Já deve ser Decimal no modelo InDB  
                 if not isinstance(total_amount_decimal, Decimal): total_amount_decimal \= Decimal(str(total_amount_decimal))

                 income_trx \= TransactionCreateInternal( \# Usar modelo interno  
                     type=\\"sale_income\\", amount=total_amount_decimal,  
                     currency=order.currency if hasattr(order, 'currency') else settings.DEFAULT_CURRENCY,  
                     description=f\\"Receita Pedido {order.order_ref}\\",  
                     status=\\"completed\\", \# Ou 'pending' se esperar confirmação de pagamento?  
                     associated_order_id=order.id, associated_user_id=order.customer_id  
                 )  
                 \# Chamar service bancário (precisa do repo e counter)  
                 created_trx \= await banking_service.record_transaction(  
                     income_trx, banking_repo, counter_service, audit_service, current_user=None \# System action?  
                 )  
                 \# Salvar ID da transação no pedido  
                 await order_repo.update(order.id, {\\"$addToSet\\": {\\"transaction_ids\\": created_trx.id}})  
                 transaction_recorded \= True  
                 log.info(f\\"Transação {created_trx.transaction_ref} registrada para pedido {order.order_ref}\\")  
             except Exception as e:  
                 logger.exception(f\\"Falha ao registrar transação para pedido {order.order_ref}. Status será atualizado mesmo assim.\\")  
                 \# Não impedir a atualização de status por falha na transação? Depende da regra.

        \# 3\. Marcar Itens RFID como Vendidos (Ex: na entrega)  
        items_marked_sold \= False  
        if new_status \== \\"delivered\\":  
             log.debug(f\\"Marcando itens RFID como vendidos para pedido {order.order_ref}...\\")  
             try:  
                 prod_quantities \= {item.product_id: item.quantity for item in order.items}  
                 await stock_service.mark_items_as_sold(  
                     order_id=order.id, product_ids_quantities=prod_quantities,  
                     stock_repo=stock_item_repo, audit_service=audit_service \#, current_user=current_user \# Quem deu baixa?  
                 )  
                 items_marked_sold \= True  
             except Exception as e:  
                 logger.error(f\\"Falha ao marcar itens RFID como vendidos para pedido {order.order_ref}: {e}\\")

        \# \--- Atualizar Status do Pedido no DB \---  
        log.debug(\\"Atualizando documento do pedido no MongoDB...\\")  
        try:  
            update_payload \= {\\"status\\": new_status}  
            if new_status \== \\"delivered\\" and not order.actual_delivery_date: \# Assume que OrderInDB tem esse campo  
                 update_payload\[\\"actual_delivery_date\\"\] \= datetime.utcnow()  
            \# Adicionar notas se vieram do request  
            if notes is not None: update_payload\[\\"notes\\"\] \= notes \# Assume que OrderInDB tem campo 'notes'

            updated_db \= await order_repo.update(order_id, update_payload)  
            if not updated_db:  
                 \# Algo muito errado se chegamos aqui e o pedido sumiu  
                 log.critical(f\\"CRITICAL: Pedido {order_id} não encontrado durante atualização final de status para '{new_status}'\!\\")  
                 \# Reverter ações anteriores (estoque, transação)? Complexo.  
                 raise HTTPException(status_code=500, detail=\\"Failed to finalize order status update.\\")

            log.success(f\\"Status do pedido {order.order_ref} atualizado para {new_status}.\\")  
            \# Disparar evento Redis (opcional)  
            \# await publish_event(\\"sales.order.status.updated\\", updated_db.model_dump(mode='json'))  
            return updated_db  
        except (ValueError, RuntimeError) as e:  
             log.error(f\\"Erro de DB ao atualizar status final do pedido {order.order_ref}: {e}\\")  
             raise HTTPException(status_code=500, detail=f\\"Database error updating order status: {e}\\")

    async def get_order(self, order_id_str: str, order_repo: OrderRepository, user_repo: UserRepository) \-\> Optional\[OrderAPI\]:  
        \\"\\"\\"Busca um pedido e enriquece com detalhes do cliente.\\"\\"\\"  
        log \= logger.bind(order_id=order_id_str)  
        log.debug(\\"Service: Buscando pedido por ID...\\")  
        order_db \= await order_repo.get_by_id(order_id_str)  
        if not order_db:  
             log.info(\\"Pedido não encontrado.\\")  
             return None

        order_api \= OrderAPI.model_validate(order_db) \# Validar/Converter para modelo API

        \# Enriquecer com nome do cliente  
        customer \= await user_repo.get_by_id(order_db.customer_id)  
        if customer and customer.profile:  
             order_api.customer_details \= {\\"name\\": f\\"{customer.profile.first_name or ''} {customer.profile.last_name or ''}\\".strip()}

        return order_api

    async def list_orders_by_customer(self, customer_id: ObjectId, order_repo: OrderRepository, user_repo: UserRepository, skip: int \= 0, limit: int \= 10\) \-\> List\[OrderAPI\]:  
         \\"\\"\\"Lista pedidos de um cliente, enriquecendo com nome.\\"\\"\\"  
         orders_db \= await order_repo.list_by_customer(customer_id, skip=skip, limit=limit)  
         \# Enriquecer todos (pode ser ineficiente)  
         orders_api \= \[\]  
         customer_name \= None \# Buscar nome uma vez  
         if orders_db:  
              customer \= await user_repo.get_by_id(customer_id)  
              if customer and customer.profile: customer_name \= f\\"{customer.profile.first_name or ''} {customer.profile.last_name or ''}\\".strip()

         for order_db in orders_db:  
              order_api \= OrderAPI.model_validate(order_db)  
              if customer_name: order_api.customer_details \= {\\"name\\": customer_name}  
              orders_api.append(order_api)  
         return orders_api

\# Função de dependência para o Service  
async def get_sales_service() \-\> OrderService: \# Renomear para get_order_service?  
    \\"\\"\\"FastAPI dependency for OrderService.\\"\\"\\"  
    \# Service sem estado, instanciar diretamente  
    \# As dependências (repos, outros services) serão injetadas nos endpoints  
    return OrderService()

\# Importar ASCENDING e Decimal  
from pymongo import ASCENDING
