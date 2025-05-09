# agentos_core/app/modules/agreements/repository.py

from typing import Optional, List, Tuple, Dict, Any  
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection # Adicionar Collection  
from pymongo import ASCENDING, DESCENDING  
from pymongo.results import UpdateResult # Adicionar UpdateResult  
from bson import ObjectId  
from loguru import logger  
from pydantic import BaseModel # Adicionar BaseModel

# Importar Base e modelos internos/DB  
from app.core.repository import BaseRepository  
from .models import AgreementInDB, AgreementCreateInternal, AgreementUpdateInternal, WitnessStatus # Usar nomes internos

# Importar get_database  
from app.core.database import get_database

COLLECTION_NAME = "agreements"

class AgreementRepository(BaseRepository[AgreementInDB, AgreementCreateInternal, AgreementUpdateInternal]):  
    model = AgreementInDB  
    collection_name = COLLECTION_NAME

    async def create_indexes(self):  
        """Cria índices para consulta eficiente de acordos."""  
        try:  
            await self.collection.create_index("agreement_ref", unique=True)  
            await self.collection.create_index("created_by")  
            # Indexar ambos os campos dentro do array witness_status  
            await self.collection.create_index("witness_status.witness_id")  
            await self.collection.create_index("witness_status.accepted")  
            # Indexar o array witness_ids diretamente para buscas $in ou $all  
            await self.collection.create_index("witness_ids")  
            await self.collection.create_index("status")  
            await self.collection.create_index([("created_at", DESCENDING)])  
            await self.collection.create_index("tags", sparse=True)  
            logger.info(f"Índices criados/verificados para a coleção: {self.collection_name}")  
        except Exception as e:  
            logger.exception(f"Erro ao criar índices para {self.collection_name}: {e}")

    async def create(self, data_in: AgreementCreateInternal | Dict) -> AgreementInDB:  
         """Cria acordo, inicializando status das testemunhas."""  
         if isinstance(data_in, BaseModel):  
             create_data = data_in.model_dump(exclude_unset=False)  
         else:  
             create_data = data_in.copy()

         # Validar e converter witness_ids para ObjectId  
         raw_witness_ids = create_data.get("witness_ids", [])  
         witness_ids_obj: List[ObjectId] = []  
         invalid_ids = []  
         for w_id_str in raw_witness_ids:  
              obj_id = self._to_objectid(w_id_str)  
              if obj_id:  
                  # Verificar se não é o criador (requer creator_id aqui)  
                  if "created_by" in create_data and obj_id == create_data["created_by"]:  
                       logger.warning(f"Criador {obj_id} não pode ser testemunha no acordo.")  
                       # Levantar erro ou apenas ignorar? Ignorar por enquanto.  
                  else:  
                       witness_ids_obj.append(obj_id)  
              else:  
                   invalid_ids.append(w_id_str)

         if invalid_ids:  
              raise ValueError(f"Invalid witness ID format found: {invalid_ids}")  
         if not witness_ids_obj:  
             raise ValueError("At least one valid witness ID is required.")

         # Remover duplicatas e salvar ObjectIds  
         unique_witness_ids = list(set(witness_ids_obj))  
         create_data["witness_ids"] = unique_witness_ids

         # Inicializar witness_status  
         create_data["witness_status"] = [  
             WitnessStatus(witness_id=w_id, accepted=False).model_dump() # Salvar como dict  
             for w_id in unique_witness_ids  
         ]

         # Garantir defaults  
         create_data.setdefault("status", "pending")  
         now = datetime.utcnow()  
         create_data.setdefault("created_at", now)  
         create_data.setdefault("last_updated_at", now)  
         # Garantir que created_by é ObjectId  
         if "created_by" in create_data:  
              creator_id = self._to_objectid(create_data["created_by"])  
              if not creator_id: raise ValueError("Invalid creator_id format.")  
              create_data["created_by"] = creator_id

         # Chamar create do BaseRepository  
         return await super().create(create_data)

    async def update_witness_acceptance(self, agreement_id: ObjectId, witness_id: ObjectId, accepted: bool) -> bool:  
         """Atualiza o status de aceitação de uma testemunha específica no array."""  
         now = datetime.utcnow()  
         log = logger.bind(agreement_id=str(agreement_id), witness_id=str(witness_id), accepted=accepted)  
         log.debug("Atualizando status de aceitação da testemunha...")  
         try:  
             # Usar operador posicional '$' para atualizar o elemento correto do array  
             result: UpdateResult = await self.collection.update_one(  
                 {"_id": agreement_id, "witness_status.witness_id": witness_id},  
                 {"$set": {  
                     "witness_status.$.accepted": accepted,  
                     "witness_status.$.accepted_at": now if accepted else None,  
                     "last_updated_at": now  
                     }  
                 }  
             )  
             success = result.modified_count > 0  
             if success: log.info("Status da testemunha atualizado com sucesso.")  
             else: log.warning("Nenhuma testemunha correspondente encontrada ou status já era o mesmo.")  
             return success  
         except Exception as e:  
             self._handle_db_exception(e, "update_witness_acceptance", agreement_id)  
             return False

    async def update_agreement_status(  
            self,  
            agreement_id: ObjectId,  
            new_status: str,  
            accepted_by_all: Optional[bool] = None, # Opcional: condição extra  
            resolution_notes: Optional[str] = None  
            ) -> bool:  
         """  
         Atualiza o status principal, opcionalmente notas, e data de conclusão/disputa.  
         Pode incluir condição extra (ex: só atualizar para 'accepted' se todas testemunhas aceitaram).  
         """  
         now = datetime.utcnow()  
         log = logger.bind(agreement_id=str(agreement_id), new_status=new_status)  
         log.debug("Atualizando status principal do acordo...")

         query: Dict[str, Any] = {"_id": agreement_id}  
         # Adicionar condição extra à query, se fornecida  
         if accepted_by_all is True:  
              # Garante que todos os elementos em witness_status têm accepted=true  
              # e que NENHUM tem accepted=false. $not/$elemMatch é mais seguro que $ne.  
              query["witness_status"] = {"$not": {"$elemMatch": {"accepted": False}}}  
              log.debug("Condição adicional: todas as testemunhas devem ter aceitado.")  
         elif accepted_by_all is False: # Condição inversa (pelo menos uma não aceitou)  
               query["witness_status.accepted"] = False # Mais simples

         update_payload: Dict[str, Any] = {"status": new_status, "last_updated_at": now}  
         if resolution_notes is not None:  
             update_payload["resolution_notes"] = resolution_notes  
         if new_status in ["concluded", "disputed"]:  
             update_payload["concluded_at"] = now

         try:  
             result: UpdateResult = await self.collection.update_one(  
                 query, # Aplicar query com condição opcional  
                 {"$set": update_payload}  
             )  
             success = result.modified_count > 0  
             if success: log.info("Status do acordo atualizado com sucesso.")  
             elif result.matched_count > 0: log.info("Status do acordo já era o desejado ou condição extra não atendida.")  
             else: log.warning("Acordo não encontrado para atualização de status.")  
             return success  
         except Exception as e:  
             self._handle_db_exception(e, "update_agreement_status", agreement_id)  
             return False

    async def list_agreements(  
        self,  
        # ... (filtros como antes: user_id, witness_id, created_by_id, status, tags) ...  
        user_id_str: Optional[str] = None, # Renomear para clareza  
        witness_id_str: Optional[str] = None,  
        created_by_id_str: Optional[str] = None,  
        status: Optional[str] = None,  
        tags: Optional[List[str]] = None,  
        # ... (skip, limit) ...  
        ) -> List[AgreementInDB]:  
        """Lista acordos com filtros flexíveis."""  
        query = {}  
        if status: query["status"] = status  
        if tags: query["tags"] = {"$in": tags}

        user_objid = self._to_objectid(user_id_str) if user_id_str else None  
        witness_objid = self._to_objectid(witness_id_str) if witness_id_str else None  
        creator_objid = self._to_objectid(created_by_id_str) if created_by_id_str else None

        # Lógica de filtro por usuário  
        if witness_objid: # Filtro mais específico tem prioridade  
            query["witness_ids"] = witness_objid  
        elif creator_objid:  
            query["created_by"] = creator_objid  
        elif user_objid: # Filtro genérico para criador OU testemunha  
             query["$or"] = [  
                 {"created_by": user_objid},  
                 {"witness_ids": user_objid}  
             ]

        return await self.list_by(query=query, skip=skip, limit=limit, sort=[("created_at", DESCENDING)])

# Função de dependência FastAPI  
async def get_agreement_repository() -> AgreementRepository:  
    """FastAPI dependency to get AgreementRepository instance."""  
    db = get_database()  
    return AgreementRepository(db)
