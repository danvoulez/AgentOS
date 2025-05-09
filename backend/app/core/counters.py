# agentos_core/app/core/counters.py

from datetime import datetime  
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection  
from pymongo import ReturnDocument  
from loguru import logger

# Importar get_database diretamente para a função de dependência  
from app.core.database import get_database

COUNTERS_COLLECTION = "counters"

class CounterService:  
    """Gera IDs sequenciais amigáveis (ex: ORD-YYYY-XXXXX)."""

    def __init__(self, db: AsyncIOMotorDatabase):  
        if not isinstance(db, AsyncIOMotorDatabase):  
             # Adicionar verificação de tipo para segurança  
             raise TypeError("CounterService requires a valid AsyncIOMotorDatabase instance.")  
        self.collection: AsyncIOMotorCollection = db[COUNTERS_COLLECTION]  
        logger.debug(f"CounterService initialized with collection '{COUNTERS_COLLECTION}'.")

    async def _get_next_sequence(self, name: str) -> int:  
        """Obtém o próximo valor da sequência de forma atômica."""  
        log = logger.bind(counter_name=name)  
        log.debug("Getting next sequence value...")  
        try:  
            # find_one_and_update com upsert=True é atômico  
            counter = await self.collection.find_one_and_update(  
                {"_id": name}, # Usar nome como _id  
                {"$inc": {"sequence_value": 1}}, # Incrementar  
                upsert=True, # Criar se não existir (começará em 1 após $inc)  
                return_document=ReturnDocument.AFTER # Retornar o documento *depois* da atualização  
            )  
            if counter is None or "sequence_value" not in counter:  
                # Isso é muito inesperado com upsert=True e ReturnDocument.AFTER  
                log.critical(f"CRITICAL: Failed to get or create counter - find_one_and_update returned unexpected value: {counter}")  
                raise RuntimeError(f"Failed to reliably get or create counter '{name}'")

            next_val = counter["sequence_value"]  
            log.debug(f"Next sequence value obtained: {next_val}")  
            return next_val  
        except Exception as e:  
            # Capturar erros de DB (ex: timeout, falha de conexão)  
            log.exception(f"Database error while getting next sequence for counter '{name}': {e}")  
            raise RuntimeError(f"Database error accessing counter '{name}'") from e

    async def generate_reference(self, prefix: str) -> str:  
        """Gera a referência completa (ex: ORD-2025-00001)."""  
        if not prefix or not isinstance(prefix, str) or not prefix.isalnum():  
            raise ValueError("Prefix must be a non-empty alphanumeric string.")

        year = datetime.utcnow().year  
        counter_name = f"{prefix.lower()}_{year}_counter" # Nome do contador específico  
        log = logger.bind(prefix=prefix, year=year, counter_name=counter_name)  
        log.info(f"Generating reference ID...")

        try:  
            sequence = await self._get_next_sequence(counter_name)  
            # Formatar com padding de zeros à esquerda (5 dígitos para sequência)  
            ref_id = f"{prefix.upper()}-{year}-{sequence:05d}"  
            log.success(f"Reference ID generated successfully: {ref_id}")  
            return ref_id  
        except Exception as e:  
            # Erros já logados em _get_next_sequence, apenas re-propagar  
            # Logar aqui também pode ser útil para contexto da falha na geração  
            log.error(f"Failed to generate reference ID for prefix '{prefix}': {e}")  
            # Levantar um erro mais específico da aplicação? Ou manter RuntimeError?  
            raise RuntimeError(f"Could not generate reference ID for prefix {prefix}") from e

# Função de dependência para injetar o serviço nos endpoints/outros serviços  
async def get_counter_service() -> CounterService:  
    """FastAPI dependency to get CounterService instance."""  
    # Sempre obtém a instância do DB atual  
    db = get_database()  
    # Retorna uma nova instância do serviço (sem estado)  
    return CounterService(db)
