\# agentos_core/app/modules/agreements/services.py

from typing import Optional, List, Dict, Any, Literal \# Adicionar Literal  
from datetime import datetime  
from bson import ObjectId  
from fastapi import HTTPException, status  
from loguru import logger  
from pydantic import BaseModel \# Para validar dados internos

\# Repositórios e Modelos Internos/DB  
from .repository import AgreementRepository  
from .models import ( \# Usar nomes internos  
    AgreementInDB, AgreementCreateInternal, AgreementUpdateInternal,  
    WitnessStatus, AGREEMENT_STATUSES  
)  
\# Modelos API (para tipo de retorno)  
from app.models.agreements import Agreement, AgreementCreateAPI, AgreementUpdateAPI, ConversationListItem \# ConversationListItem não pertence aqui

\# Repositório de Usuários (para buscar nomes e validar)  
from app.modules.people.repository import UserRepository  
from app.modules.people.models import UserInDB \# Para info do usuário

\# Serviços Core e de Auditoria  
from app.core.counters import CounterService  
from app.modules.office.services_audit import AuditService

\# Notificações (Placeholder)  
async def notify_witnesses_of_new_agreement(agreement_ref: str, witness_ids: List\[ObjectId\]):  
    logger.info(f\\"Placeholder: Notificando testemunhas {witness_ids} sobre novo acordo {agreement_ref}\\")  
    \# TODO: Implementar envio de email, WS ou outra notificação  
    await asyncio.sleep(0.1) \# Simular IO

async def notify_creator_of_acceptance(agreement_ref: str, creator_id: ObjectId, witness_id: ObjectId):  
    logger.info(f\\"Placeholder: Notificando criador {creator_id} que testemunha {witness_id} aceitou acordo {agreement_ref}\\")  
    await asyncio.sleep(0.1)

async def notify_creator_of_status_change(agreement_ref: str, creator_id: ObjectId, new_status: str):  
     logger.info(f\\"Placeholder: Notificando criador {creator_id} que acordo {agreement_ref} mudou para status {new_status}\\")  
     await asyncio.sleep(0.1)

class AgreementService:  
    \\"\\"\\"Lógica de negócio para Acordos.\\"\\"\\"

    \# Helper para enriquecer com nomes (reutilizável)  
    async def _enrich_agreement(self, agreement_db: AgreementInDB, user_repo: UserRepository) \-\> Agreement:  
        \\"\\"\\"Adiciona detalhes do criador e testemunhas.\\"\\"\\"  
        \# Validar/Converter para modelo API  
        agreement_api \= Agreement.model_validate(agreement_db)

        users_to_fetch \= {agreement_db.created_by}  
        for ws in agreement_db.witness_status:  
            users_to_fetch.add(ws.witness_id)

        \# Buscar todos os usuários necessários de uma vez  
        user_docs \= await user_repo.list_by({\\"_id\\": {\\"$in\\": list(users_to_fetch)}})  
        user_map \= {str(u.id): u for u in user_docs} \# Mapear por ID string

        \# Adicionar detalhes do criador  
        creator \= user_map.get(str(agreement_db.created_by))  
        agreement_api.created_by_details \= {  
            \\"id\\": str(agreement_db.created_by),  
            \\"name\\": f\\"{creator.profile.first_name or ''} {creator.profile.last_name or ''}\\".strip() if creator else \\"Usuário Desconhecido\\"  
        }

        \# Adicionar detalhes das testemunhas  
        witness_details \= \[\]  
        for ws in agreement_db.witness_status:  
            witness_id_str \= str(ws.witness_id)  
            witness_user \= user_map.get(witness_id_str)  
            witness_details.append({  
                \\"id\\": witness_id_str,  
                \\"name\\": f\\"{witness_user.profile.first_name or ''} {witness_user.profile.last_name or ''}\\".strip() if witness_user else \\"Testemunha Desconhecida\\",  
                \\"accepted\\": ws.accepted,  
                \\"accepted_at\\": ws.accepted_at.isoformat() if ws.accepted_at else None  
            })  
        agreement_api.witness_details \= witness_details

        return agreement_api

    async def create_agreement(  
        self,  
        agreement_in: AgreementCreateAPI, \# Recebe modelo API  
        creator: UserInDB, \# Usuário logado  
        agreement_repo: AgreementRepository,  
        user_repo: UserRepository, \# Para validar testemunhas  
        counter_service: CounterService,  
        audit_service: AuditService,  
    ) \-\> Agreement: \# Retorna modelo API  
        \\"\\"\\"Cria um novo acordo, validando testemunhas, gerando ref e logando.\\"\\"\\"  
        log \= logger.bind(creator_id=str(creator.id), creator_email=creator.email)  
        log.info(\\"Service: Criando novo acordo...\\")

        \# 1\. Validar Testemunhas (existência, atividade, não ser o criador)  
        witness_ids_obj: List\[ObjectId\] \= \[\]  
        if not agreement_in.witness_ids:  
             raise HTTPException(status.HTTP_400_BAD_REQUEST, \\"At least one witness is required.\\")

        invalid_witness_details \= \[\]  
        for w_ref in set(agreement_in.witness_ids): \# Usar set para evitar buscas duplicadas  
             \# Tentar buscar por ID ou Email? API recebe ID string.  
             w_id_obj \= agreement_repo._to_objectid(w_ref)  
             witness \= None  
             if w_id_obj:  
                 witness \= await user_repo.get_by_id(w_id_obj)  
             \# TODO: Adicionar busca por email se w_ref não for ObjectId?  
             \# elif '@' in w_ref: witness \= await user_repo.get_by_email(w_ref)

             if not witness:  
                 invalid_witness_details.append(f\\"Witness '{w_ref}' not found.\\")  
                 continue  
             if not witness.is_active:  
                  invalid_witness_details.append(f\\"Witness '{w_ref}' ({witness.email}) is inactive.\\")  
                  continue  
             if witness.id \== creator.id:  
                  invalid_witness_details.append(f\\"Creator ({creator.email}) cannot be their own witness.\\")  
                  continue  
             witness_ids_obj.append(witness.id)

        if invalid_witness_details:  
             log.warning(f\\"Falha na validação das testemunhas: {invalid_witness_details}\\")  
             raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=f\\"Invalid witnesses: {'; '.join(invalid_witness_details)}\\")

        unique_witness_ids \= list(set(witness_ids_obj)) \# Garantir IDs únicos de ObjectId  
        if not unique_witness_ids: \# Caso todos sejam inválidos ou o próprio criador  
             raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=\\"No valid witnesses provided for the agreement.\\")

        \# 2\. Gerar Referência  
        try:  
            agreement_ref \= await counter_service.generate_reference(\\"AGR\\")  
        except Exception as e:  
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f\\"Could not generate agreement reference: {e}\\")

        \# 3\. Preparar dados internos  
        agreement_internal_data \= AgreementCreateInternal(  
            agreement_ref=agreement_ref,  
            created_by=creator.id,  
            witness_ids=unique_witness_ids,  
            description=agreement_in.description,  
            location_context=agreement_in.location_context,  
            tags=agreement_in.tags or \[\]  
            \# status, witness_status, timestamps serão tratados pelo repo/modelo  
        )

        \# 4\. Criar no repositório  
        try:  
            created_db \= await agreement_repo.create(agreement_internal_data) \# Repo lida com inicialização de witness_status  
            log.success(f\\"Acordo {agreement_ref} criado com sucesso.\\")

            \# Logar auditoria (passando request=None pois service não tem acesso direto)  
            await audit_service.log_audit_event(  
                 action=\\"agreement_created\\", status=\\"success\\", entity_type=\\"Agreement\\",  
                 entity_id=created_db.id, audit_repo=None, \# Repo no service  
                 details=created_db.model_dump(mode='json'), \# Logar dados completos internos  
                 current_user=creator, request=None  
            )

            \# Disparar notificação para testemunhas (assíncrono)  
            asyncio.create_task(notify_witnesses_of_new_agreement(agreement_ref, unique_witness_ids))

            \# Enriquecer e retornar modelo API  
            return await self._enrich_agreement(created_db, user_repo)

        except (ValueError, RuntimeError, Exception) as e:  
             \# ValueError pode ser DuplicateKey ou erro de validação interna  
             logger.exception(f\\"Falha ao criar acordo no banco de dados: {e}\\")  
             await audit_service.log_audit_event(action=\\"agreement_create_failed\\", status=\\"failure\\", ..., error_message=str(e))  
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f\\"Could not create agreement: {e}\\")

    async def accept_agreement(  
        self,  
        agreement_id_str: str,  
        witness: UserInDB, \# Testemunha logada  
        agreement_repo: AgreementRepository,  
        user_repo: UserRepository, \# Para enriquecer retorno  
        audit_service: AuditService,  
    ) \-\> Agreement: \# Retorna modelo API  
        \\"\\"\\"Registra a aceitação de uma testemunha e atualiza status se necessário.\\"\\"\\"  
        log \= logger.bind(agreement_id=agreement_id_str, witness_id=str(witness.id))  
        log.info(\\"Service: Testemunha aceitando acordo...\\")

        agreement_id \= agreement_repo._to_objectid(agreement_id_str)  
        if not agreement_id: raise HTTPException(400, \\"Invalid agreement ID\\")

        \# Buscar acordo para validações  
        agreement \= await agreement_repo.get_by_id(agreement_id)  
        if not agreement: raise HTTPException(404, \\"Agreement not found\\")  
        if agreement.status \!= \\"pending\\": raise HTTPException(400, \\"Agreement is not pending acceptance\\")  
        if witness.id not in agreement.witness_ids: raise HTTPException(403, \\"User is not a listed witness\\")

        \# Verificar se já aceitou  
        if any(ws.witness_id \== witness.id and ws.accepted for ws in agreement.witness_status):  
             log.info(\\"Testemunha já aceitou este acordo.\\")  
             return await self._enrich_agreement(agreement, user_repo) \# Retorna estado atual

        \# Atualizar aceitação no repositório  
        accepted_db \= await agreement_repo.update_witness_acceptance(agreement_id, witness.id, accepted=True)  
        if not accepted_db:  
            log.error(\\"Falha ao atualizar status da testemunha no DB.\\")  
            \# Logar auditoria de falha  
            await audit_service.log_audit_event(action=\\"agreement_accept_failed\\", status=\\"failure\\",...)  
            raise HTTPException(500, \\"Failed to record witness acceptance\\")

        log.success(f\\"Testemunha {witness.email} aceitou o acordo {agreement.agreement_ref}\\")  
        \# Logar auditoria de sucesso (aceitação)  
        await audit_service.log_audit_event(action=\\"agreement_accepted_by_witness\\", status=\\"success\\", ...)

        \# Notificar criador (assíncrono)  
        asyncio.create_task(notify_creator_of_acceptance(agreement.agreement_ref, agreement.created_by, witness.id))

        \# Verificar se todas testemunhas aceitaram para mudar status principal  
        \# Buscar o acordo ATUALIZADO  
        updated_agreement \= await agreement_repo.get_by_id(agreement_id)  
        if updated_agreement and all(ws.accepted for ws in updated_agreement.witness_status):  
            log.info(\\"Todas as testemunhas aceitaram. Atualizando status do acordo para 'accepted'.\\")  
            status_updated \= await agreement_repo.update_agreement_status(agreement_id, \\"accepted\\", accepted_by_all=True) \# Usar condição  
            if status_updated:  
                 log.success(f\\"Status do acordo {agreement.agreement_ref} atualizado para 'accepted'\\")  
                 await audit_service.log_audit_event(action=\\"agreement_status_updated\\", status=\\"success\\", entity_id=agreement_id, details={\\"new_status\\": \\"accepted\\", \\"reason\\": \\"All witnesses accepted\\"}, ...)  
                 \# Notificar criador da mudança de status geral  
                 asyncio.create_task(notify_creator_of_status_change(agreement.agreement_ref, agreement.created_by, \\"accepted\\"))  
                 \# Buscar novamente para garantir que temos o último estado  
                 updated_agreement \= await agreement_repo.get_by_id(agreement_id)

        \# Enriquecer e retornar acordo final  
        final_agreement_enriched \= await self._enrich_agreement(updated_agreement, user_repo)  
        return final_agreement_enriched

    async def conclude_or_dispute_agreement(  
        self,  
        agreement_id_str: str,  
        action_user: UserInDB, \# Usuário realizando a ação  
        new_status: Literal\[\\"concluded\\", \\"disputed\\"\], \# Apenas estes dois status  
        notes: Optional\[str\],  
        agreement_repo: AgreementRepository,  
        user_repo: UserRepository, \# Para enriquecer  
        audit_service: AuditService,  
    ) \-\> Agreement: \# Retorna modelo API  
        \\"\\"\\"Marca um acordo como concluído ou disputado.\\"\\"\\"  
        log \= logger.bind(agreement_id=agreement_id_str, new_status=new_status, user_id=str(action_user.id))  
        log.info(f\\"Service: Marcando acordo como '{new_status}'...\\")

        agreement_id \= agreement_repo._to_objectid(agreement_id_str)  
        if not agreement_id: raise HTTPException(400, \\"Invalid agreement ID\\")

        agreement \= await agreement_repo.get_by_id(agreement_id)  
        if not agreement: raise HTTPException(404, \\"Agreement not found\\")

        \# Validação de permissão e status  
        is_creator \= agreement.created_by \== action_user.id  
        is_admin \= \\"admin\\" in action_user.roles  
        if not is_creator and not is_admin:  
             raise HTTPException(403, \\"Only the creator or an admin can conclude/dispute.\\")  
        if agreement.status not in \[\\"pending\\", \\"accepted\\"\]: \# Só pode concluir/disputar se pendente ou aceito?  
             raise HTTPException(400, f\\"Cannot conclude/dispute agreement in status '{agreement.status}'\\")

        \# Atualizar status e notas  
        success \= await agreement_repo.update_agreement_status(agreement_id, new_status, resolution_notes=notes)  
        if not success:  
            log.error(f\\"Falha ao atualizar status do acordo para '{new_status}'.\\")  
            await audit_service.log_audit_event(action=f\\"agreement_{new_status}_failed\\", status=\\"failure\\", ...)  
            raise HTTPException(500, f\\"Failed to update agreement status to '{new_status}'\\")

        log.success(f\\"Acordo {agreement.agreement_ref} marcado como '{new_status}'.\\")  
        await audit_service.log_audit_event(action=f\\"agreement_{new_status}\\", status=\\"success\\", ...)

        \# Notificar criador (se não foi ele mesmo quem fez)  
        if not is_creator:  
            asyncio.create_task(notify_creator_of_status_change(agreement.agreement_ref, agreement.created_by, new_status))

        updated_agreement \= await agreement_repo.get_by_id(agreement_id)  
        return await self._enrich_agreement(updated_agreement, user_repo)

    async def list_agreements_for_user(  
        self,  
        user: UserInDB, \# Usuário logado  
        agreement_repo: AgreementRepository,  
        user_repo: UserRepository, \# Para buscar nomes  
        status: Optional\[str\] \= None,  
        tags: Optional\[List\[str\]\] \= None,  
        skip: int \= 0,  
        limit: int \= 50  
        ) \-\> List\[Agreement\]: \# Retorna lista de modelo API  
         \\"\\"\\"Lista acordos onde o usuário é criador ou testemunha, enriquecendo.\\"\\"\\"  
         log \= logger.bind(user_id=str(user.id))  
         log.debug(\\"Service: Listando acordos para usuário...\\")  
         agreements_db \= await agreement_repo.list_agreements(  
             user_id_str=str(user.id), \# Passar ID como string para repo  
             status=status, tags=tags, skip=skip, limit=limit  
         )  
         \# Enriquecer com detalhes de nomes  
         enriched_agreements \= \[await self._enrich_agreement(a, user_repo) for a in agreements_db\]  
         log.info(f\\"Retornando {len(enriched_agreements)} acordos para usuário.\\")  
         return enriched_agreements

    async def get_agreement(  
        self,  
        agreement_id_str: str,  
        requester: UserInDB, \# Usuário pedindo  
        agreement_repo: AgreementRepository,  
        user_repo: UserRepository  
    ) \-\> Agreement: \# Retorna modelo API  
         \\"\\"\\"Busca um acordo específico, verifica permissão e enriquece.\\"\\"\\"  
         log \= logger.bind(agreement_id=agreement_id_str, user_id=str(requester.id))  
         log.debug(\\"Service: Buscando acordo por ID...\\")  
         agreement_db \= await agreement_repo.get_by_id(agreement_id_str)  
         if not agreement_db:  
              raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=\\"Agreement not found\\")

         \# Verificar permissão  
         is_creator \= agreement_db.created_by \== requester.id  
         is_witness \= requester.id in agreement_db.witness_ids  
         is_admin \= \\"admin\\" in requester.roles  
         if not (is_creator or is_witness or is_admin):  
              log.warning(\\"Acesso negado ao acordo.\\")  
              \# Auditoria é feita no router que chama este service  
              raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=\\"Not authorized to view this agreement\\")

         return await self._enrich_agreement(agreement_db, user_repo)

\# Função de dependência FastAPI  
async def get_agreement_service() \-\> AgreementService:  
    \\"\\"\\"FastAPI dependency for AgreementService.\\"\\"\\"  
    return AgreementService()

\# Importar asyncio para tasks de notificação  
import asyncio
