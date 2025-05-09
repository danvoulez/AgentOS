\# agentos_core/app/modules/delivery/services.py

from typing import Optional, List, Dict, Any  
from datetime import datetime  
from bson import ObjectId  
from fastapi import HTTPException, status  
from loguru import logger  
from pydantic import BaseModel \# Para validar dados

\# Repositórios e Modelos Internos/DB  
from .repository import DeliveryRepository  
from .models import DeliveryInDB, DeliveryCreateInternal, DeliveryUpdateInternal, TrackingEvent, AddTrackingEventInternal, DELIVERY_STATUSES \# Usar nomes internos  
\# Modelos API (para tipo de retorno)  
from app.models.delivery import Delivery, TrackingEventAPI

\# Repositórios e Modelos de outros módulos  
from app.modules.sales.repository import OrderRepository  
from app.modules.sales.models import OrderInDB \# Para buscar dados do pedido  
from app.modules.people.repository import UserRepository  
from app.modules.people.models import UserInDB \# Para validar motorista e auditoria

\# Serviços Core e de Auditoria  
from app.core.counters import CounterService  
from app.modules.office.services_audit import AuditService

\# PubSub (Opcional)  
\# from app.core.redis_pubsub import publish_event

class DeliveryService:  
    \\"\\"\\"Lógica de negócio para Entregas.\\"\\"\\"

    async def create_delivery_from_order(  
        self,  
        order_id_str: str,  
        delivery_repo: DeliveryRepository,  
        order_repo: OrderRepository,  
        counter_service: CounterService,  
        \# audit_service: AuditService, \# Auditoria será chamada pelo Router  
        \# current_user: UserInDB \# Quem disparou a criação? Sistema ou Usuário?  
    ) \-\> DeliveryInDB: \# Retorna modelo DB  
        \\"\\"\\"  
        Cria uma nova entrega baseada em um pedido. Valida o pedido e status.  
        \\"\\"\\"  
        log \= logger.bind(order_id=order_id_str, service=\\"DeliveryService\\")  
        log.info(\\"Service: Tentando criar entrega a partir do pedido...\\")

        order_id \= order_repo._to_objectid(order_id_str)  
        if not order_id:  
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=\\"Invalid Order ID format\\")

        \# 1\. Verificar se já existe entrega para este pedido  
        existing_delivery \= await delivery_repo.get_by_order_id(order_id)  
        if existing_delivery:  
            log.warning(\\"Entrega já existe para este pedido.\\")  
            raise HTTPException(  
                status_code=status.HTTP_409_CONFLICT,  
                detail=f\\"Delivery already exists for order {order_id_str} (Ref: {existing_delivery.delivery_ref})\\"  
            )

        \# 2\. Buscar o pedido  
        order \= await order_repo.get_by_id(order_id)  
        if not order:  
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f\\"Order {order_id_str} not found\\")

        \# 3\. Validar Status do Pedido e Endereço  
        \# Definir quais status de pedido permitem criar entrega  
        allowed_order_statuses \= \[\\"confirmed\\", \\"processing\\", \\"awaiting_shipment\\", \\"paid\\"\] \# Ajustar  
        if order.status not in allowed_order_statuses:  
            raise HTTPException(  
                status_code=status.HTTP_400_BAD_REQUEST,  
                detail=f\\"Cannot create delivery for order in status '{order.status}'\\"  
            )  
        if not order.shipping_address or not isinstance(order.shipping_address, dict) or not order.shipping_address.get(\\"street\\"): \# Verificar se endereço é minimamente válido  
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=\\"Order is missing a valid shipping address\\")

        \# 4\. Gerar Referência  
        try:  
            delivery_ref \= await counter_service.generate_reference(\\"DLV\\")  
        except Exception as e:  
            raise HTTPException(status_code=500, detail=f\\"Could not generate delivery reference: {e}\\")

        \# 5\. Preparar dados internos para criação  
        \# Estimar data de entrega (exemplo simples: \+2 dias)  
        estimated_delivery \= datetime.utcnow() \+ timedelta(days=2) \# Simplista, idealmente baseado em regras/CEP

        delivery_internal_data \= DeliveryCreateInternal(  
            delivery_ref=delivery_ref,  
            order_id=order.id,  
            customer_id=order.customer_id,  
            delivery_address=order.shipping_address,  
            current_status=\\"pending\\", \# Status inicial  
            shipping_notes=order.shipping_notes if hasattr(order, 'shipping_notes') else None, \# Pegar notas do pedido se existir  
            estimated_delivery_date=estimated_delivery,  
            tracking_history=\[ \# Evento inicial  
                TrackingEvent(status=\\"pending\\", location_note=\\"Delivery created from order\\")  
            \]  
        )  
        create_data_dict \= delivery_internal_data.model_dump()

        \# 6\. Criar usando o repositório  
        try:  
            \# O create do BaseRepository lida com timestamps  
            created_delivery_db \= await delivery_repo.create(create_data_dict)  
            log.success(f\\"Entrega {delivery_ref} criada com sucesso para pedido {order.order_ref}.\\")

            \# Opcional: Atualizar pedido com delivery_id (importante para ligação)  
            try:  
                await order_repo.update(order.id, {\\"delivery_id\\": created_delivery_db.id})  
                log.debug(f\\"Pedido {order.order_ref} atualizado com delivery_id {created_delivery_db.id}.\\")  
            except Exception as order_update_err:  
                 \# Logar erro mas não falhar a criação da entrega por isso?  
                 log.error(f\\"Falha ao atualizar pedido {order.order_ref} com delivery_id: {order_update_err}\\")

            \# Disparar evento Pub/Sub (opcional)  
            \# await publish_event(\\"delivery.created\\", created_delivery_db.model_dump(mode='json'))

            return created_delivery_db \# Retorna modelo DB  
        except (ValueError, RuntimeError) as e: \# DuplicateKey (ref/order_id) ou erro DB  
             log.error(f\\"Falha ao criar entrega no DB: {e}\\")  
             raise HTTPException(status_code=500, detail=f\\"Could not save delivery record: {e}\\")

    async def update_delivery_status(  
        self,  
        delivery_id_str: str,  
        new_status: str, \# Já validado como membro de DELIVERY_STATUSES pelo PayloadAPI  
        delivery_repo: DeliveryRepository,  
        notes: Optional\[str\] \= None,  
        location: Optional\[str\] \= None  
        \# audit_service: AuditService, \# Auditoria feita no Router  
        \# current_user: UserInDB  
    ) \-\> DeliveryInDB: \# Retorna modelo DB  
        \\"\\"\\"Atualiza o status da entrega e adiciona um evento de rastreamento.\\"\\"\\"  
        log \= logger.bind(delivery_id=delivery_id_str, new_status=new_status)  
        log.info(\\"Service: Atualizando status da entrega...\\")

        delivery_id \= delivery_repo._to_objectid(delivery_id_str)  
        if not delivery_id: raise HTTPException(400, \\"Invalid Delivery ID format\\")

        \# 1\. Buscar entrega atual  
        current_delivery \= await delivery_repo.get_by_id(delivery_id)  
        if not current_delivery: raise HTTPException(404, \\"Delivery not found\\")  
        current_status \= current_delivery.current_status

        if new_status \== current_status:  
            log.info(\\"Status já é o desejado. Nenhuma alteração.\\")  
            return current_delivery

        \# 2\. Validar transição de status (Exemplo: não voltar de 'delivered')  
        if current_status \== \\"delivered\\" and new_status \!= \\"delivered\\": \# Ou 'returned'?  
            msg \= f\\"Cannot change status from '{current_status}' to '{new_status}'.\\"  
            log.warning(msg)  
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)  
        \# Adicionar mais regras de transição complexas aqui se necessário

        \# 3\. Adicionar evento de rastreamento  
        tracking_event \= TrackingEvent(status=new_status, location_note=location, notes=notes)  
        event_added \= await delivery_repo.add_tracking_event(delivery_id, tracking_event)  
        if not event_added:  
             \# Falha ao adicionar evento pode indicar que entrega sumiu? Erro DB?  
             log.error(\\"Falha ao adicionar evento de tracking antes de atualizar status.\\")  
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=\\"Failed to add tracking event.\\")

        \# 4\. Atualizar o status principal e data de entrega (se aplicável)  
        update_payload: Dict\[str, Any\] \= {\\"status\\": new_status}  
        if new_status \== \\"delivered\\" and not current_delivery.actual_delivery_date:  
            update_payload\[\\"actual_delivery_date\\"\] \= datetime.utcnow()  
        \# Usar o update do BaseRepository  
        updated_delivery_db \= await delivery_repo.update(delivery_id, update_payload)

        if not updated_delivery_db:  
             \# Inconsistência: evento adicionado, mas status não atualizado?  
             log.critical(f\\"CRITICAL: Falha ao atualizar status da entrega {delivery_id} após adicionar evento de tracking\!\\")  
             \# Tentar reverter evento? Difícil. Levantar erro.  
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=\\"Failed to finalize delivery status update after tracking.\\")

        log.success(f\\"Status da entrega atualizado para {new_status}.\\")  
        \# Disparar evento Pub/Sub (opcional)  
        \# await publish_event(f\\"delivery.status.{new_status}\\", updated_delivery_db.model_dump(mode='json'))  
        return updated_delivery_db

    async def assign_driver(  
        self,  
        delivery_id_str: str,  
        driver_id_str: str,  
        delivery_repo: DeliveryRepository,  
        user_repo: UserRepository, \# Para validar motorista  
        audit_service: AuditService, \# Logar aqui ou no router? Aqui faz sentido.  
        current_user: UserInDB \# Quem está atribuindo  
    ) \-\> DeliveryInDB:  
        \\"\\"\\"Atribui um motorista a uma entrega.\\"\\"\\"  
        log \= logger.bind(delivery_id=delivery_id_str, driver_id=driver_id_str)  
        log.info(\\"Service: Atribuindo motorista à entrega...\\")

        delivery_id \= delivery_repo._to_objectid(delivery_id_str)  
        if not delivery_id: raise HTTPException(400, \\"Invalid Delivery ID\\")  
        driver_id \= user_repo._to_objectid(driver_id_str)  
        if not driver_id: raise HTTPException(400, \\"Invalid Driver ID\\")

        \# 1\. Validar motorista  
        driver \= await user_repo.get_by_id(driver_id)  
        \# Assumir role 'delivery_driver'  
        if not driver or not driver.is_active or \\"delivery_driver\\" not in driver.roles:  
             raise HTTPException(404, f\\"Driver user {driver_id_str} not found, inactive, or invalid role.\\")

        \# 2\. Buscar entrega e validar status  
        delivery \= await delivery_repo.get_by_id(delivery_id)  
        if not delivery: raise HTTPException(404, \\"Delivery not found\\")  
        if delivery.current_status \!= \\"pending\\": \# Só atribuir se pendente?  
            raise HTTPException(400, f\\"Cannot assign driver to delivery in status '{delivery.current_status}'\\")

        \# 3\. Atualizar entrega e adicionar evento  
        old_driver_id \= delivery.assigned_driver_id  
        update_data \= {  
            \\"assigned_driver_id\\": driver_id,  
            \\"current_status\\": \\"assigned\\", \# Mudar status  
            \\"updated_at\\": datetime.utcnow() \# BaseRepo adiciona, mas pode setar aqui  
        }  
        tracking_event \= TrackingEvent(  
            status=\\"assigned\\",  
            notes=f\\"Assigned to driver {driver.profile.first_name} ({driver.id})\\"  
        )

        \# Executar em sequência ou paralelo? Sequência é mais seguro para consistência.  
        event_added \= await delivery_repo.add_tracking_event(delivery_id, tracking_event)  
        if not event_added: raise HTTPException(500, \\"Failed to add assignment tracking event.\\")

        updated_delivery_db \= await delivery_repo.update(delivery_id, update_data)  
        if not updated_delivery_db:  
             \# Inconsistência\!  
             log.critical(f\\"CRITICAL: Falha ao atualizar entrega {delivery_id} após adicionar evento de atribuição\!\\")  
             \# TODO: Tentar reverter evento?  
             raise HTTPException(500, \\"Failed to update delivery after assignment tracking.\\")

        log.success(f\\"Motorista {driver.email} atribuído à entrega {delivery.delivery_ref}\\")  
        \# Logar auditoria da atribuição (Service faz sentido aqui)  
        await audit_service.log_audit_event(  
            action=\\"delivery_driver_assigned\\", status=\\"success\\", entity_type=\\"Delivery\\",  
            entity_id=delivery_id, audit_repo=None, \# Repo no service  
            details={\\"delivery_ref\\": delivery.delivery_ref, \\"new_driver_id\\": str(driver_id), \\"old_driver_id\\": str(old_driver_id) if old_driver_id else None},  
            current_user=current_user  
        )  
        return updated_delivery_db

    async def add_manual_tracking_event(  
        self,  
        delivery_id_str: str,  
        event_data: AddTrackingEventInternal, \# Usar modelo interno  
        delivery_repo: DeliveryRepository,  
        \# audit_service: AuditService, \# Logar no Router  
        \# current_user: UserInDB  
    ) \-\> DeliveryInDB:  
        \\"\\"\\"Adiciona um evento de tracking manualmente sem mudar status principal.\\"\\"\\"  
        log \= logger.bind(delivery_id=delivery_id_str, event_status=event_data.status)  
        log.info(\\"Service: Adicionando evento de tracking manual...\\")

        delivery_id \= delivery_repo._to_objectid(delivery_id_str)  
        if not delivery_id: raise HTTPException(400, \\"Invalid Delivery ID\\")

        \# Verificar se entrega existe? add_tracking_event falhará se não existir.  
        \# delivery \= await delivery_repo.get_by_id(delivery_id)  
        \# if not delivery: raise HTTPException(404, \\"Delivery not found\\")

        \# Criar evento  
        tracking_event \= TrackingEvent(  
            status=event_data.status,  
            location_note=event_data.location_note,  
            notes=event_data.notes  
            \# timestamp é default_factory  
        )  
        \# Adicionar ao histórico via repo  
        event_added \= await delivery_repo.add_tracking_event(delivery_id, tracking_event)  
        if not event_added:  
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Delivery not found or failed to add tracking event.\\")

        log.success(\\"Evento de tracking manual adicionado.\\")  
        \# Buscar e retornar entrega atualizada  
        updated_delivery \= await delivery_repo.get_by_id(delivery_id)  
        if not updated_delivery: \# Pouco provável, mas...  
             raise HTTPException(status_code=404, detail=\\"Delivery disappeared after adding tracking event.\\")  
        return updated_delivery

    async def get_delivery(  
        self,  
        delivery_id_str: str,  
        delivery_repo: DeliveryRepository,  
        user_repo: UserRepository \# Para enriquecer com nome do motorista  
        ) \-\> Optional\[DeliveryAPI\]: \# Retorna modelo API  
         \\"\\"\\"Busca entrega e enriquece com detalhes do motorista.\\"\\"\\"  
         log \= logger.bind(delivery_id=delivery_id_str)  
         log.debug(\\"Service: Buscando entrega por ID com enriquecimento...\\")  
         delivery_db \= await delivery_repo.get_by_id(delivery_id_str)  
         if not delivery_db:  
             log.info(\\"Entrega não encontrada.\\")  
             return None

         delivery_api \= DeliveryAPI.model_validate(delivery_db) \# Validar/Converter

         \# Enriquecer com nome do motorista  
         if delivery_db.assigned_driver_id:  
              driver \= await user_repo.get_by_id(delivery_db.assigned_driver_id)  
              if driver and driver.profile:  
                  delivery_api.driver_details \= {\\"name\\": f\\"{driver.profile.first_name or ''} {driver.profile.last_name or ''}\\".strip()}

         return delivery_api

\# Função de dependência para o Service  
async def get_delivery_service() \-\> DeliveryService:  
    \\"\\"\\"FastAPI dependency for DeliveryService.\\"\\"\\"  
    return DeliveryService()

\# Importar timedelta para exemplo de data estimada  
from datetime import timedelta
