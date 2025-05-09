# agentos_core/app/core/database.py

import motor.motor_asyncio  
import redis.asyncio as redis  
from contextlib import asynccontextmanager, AbstractAsyncContextManager # Importar AbstractAsyncContextManager  
from loguru import logger  
from typing import Optional, cast # Importar cast para type hinting

from app.core.config import settings # Importar settings

# --- MongoDB ---  
class MongoDbContext(AbstractAsyncContextManager): # Usar context manager para garantir conexão  
    client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None  
    db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None

    async def __aenter__(self):  
        """Connects on entering the async context."""  
        await self.connect()  
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  
        """Disconnects on exiting the async context."""  
        await self.disconnect()

    async def connect(self):  
        """Establishes and verifies connection to MongoDB."""  
        if self.client and self.db:  
            logger.info("MongoDB connection already established.")  
            return

        logger.info(f"Connecting to MongoDB...") # Log mais genérico sem URI completo  
        logger.debug(f"MongoDB URI used: {settings.MONGODB_URI[:settings.MONGODB_URI.find('@')]}...") # Ocultar credenciais

        try:  
            self.client = motor.motor_asyncio.AsyncIOMotorClient(  
                settings.MONGODB_URI,  
                uuidRepresentation='standard',  
                serverSelectionTimeoutMS=5000 # Timeout para seleção de servidor  
            )  
            # Forçar conexão e verificação pingando o servidor  
            await self.client.admin.command('ping')

            # Extrair nome do DB da URI  
            uri_path = settings.MONGODB_URI.split('/')[-1]  
            db_name = uri_path.split('?')[0] if '?' in uri_path else uri_path  
            if not db_name or '@' in db_name or len(db_name) > 63:  
                db_name = "agentos_db"  
                logger.warning(f"Could not parse DB name from URI, using default: {db_name}")

            self.db = self.client[db_name]  
            logger.success(f"MongoDB connection successful to database '{db_name}'.")

        except Exception as e:  
            logger.critical(f"FATAL: Failed to connect to MongoDB: {e}", exc_info=True)  
            self.client = None  
            self.db = None  
            # Considerar raise SystemExit ou propagar erro para lifespan manager lidar  
            raise ConnectionError(f"MongoDB connection failed: {e}") from e

    async def disconnect(self):  
        """Closes the MongoDB connection."""  
        if self.client:  
            logger.info("Closing MongoDB connection...")  
            try:  
                self.client.close()  
                logger.info("MongoDB connection closed.")  
            except Exception as e:  
                logger.error(f"Error closing MongoDB connection: {e}")  
            finally:  
                 # Garantir que resetamos mesmo se close() falhar  
                self.client = None  
                self.db = None

    def get_db(self) -> AsyncIOMotorDatabase:  
        """Returns the database instance, raising error if not connected."""  
        if self.db is None:  
            logger.critical("Attempted to get MongoDB instance, but it's not available.")  
            raise RuntimeError("MongoDB database is not connected or initialized.")  
        # Usar cast para ajudar o type checker  
        return cast(AsyncIOMotorDatabase, self.db)

# Instância global do contexto MongoDB  
mongo_manager = MongoDbContext()

# Função utilitária para obter o DB (será chamada pelo get_database dependency)  
def get_mongo_db_instance() -> AsyncIOMotorDatabase:  
    return mongo_manager.get_db()

# --- Redis ---  
class RedisContext(AbstractAsyncContextManager):  
    client: Optional[redis.Redis] = None

    async def __aenter__(self):  
        await self.connect()  
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):  
        await self.disconnect()

    async def connect(self):  
        """Connects to Redis."""  
        if self.client:  
            logger.info("Redis connection already established.")  
            return  
        url = settings.REDIS_URL  
        logger.info(f"Connecting to Redis at {url}...")  
        try:  
            # Usar um pool de conexões para melhor performance  
            pool = redis.ConnectionPool.from_url(  
                url,  
                decode_responses=True, # Decodificar automaticamente  
                socket_connect_timeout=5,  
                socket_keepalive=True,  
                max_connections=20 # Limitar pool size  
            )  
            self.client = redis.Redis(connection_pool=pool)  
            await self.client.ping()  
            logger.success("Redis connection successful.")  
        except Exception as e:  
            logger.error(f"Could not connect to Redis: {e}")  
            self.client = None  
            # Aplicação pode continuar sem Redis? Depende.  
            # raise ConnectionError(f"Redis connection failed: {e}") from e

    async def disconnect(self):  
        """Closes the Redis connection pool."""  
        if self.client:  
            logger.info("Closing Redis connection pool...")  
            try:  
                # Fechar o pool de conexões associado ao cliente  
                await self.client.close() # Fecha o cliente  
                await self.client.connection_pool.disconnect() # Desconecta o pool  
                logger.info("Redis connection pool closed.")  
            except Exception as e:  
                 logger.error(f"Error closing Redis connection pool: {e}")  
            finally:  
                 self.client = None

    def get_client(self) -> redis.Redis:  
        """Returns the Redis client instance."""  
        if self.client is None:  
            logger.critical("Attempted to get Redis instance, but it's not available.")  
            raise RuntimeError("Redis client is not connected or initialized.")  
        return cast(redis.Redis, self.client)

# Instância global do contexto Redis  
redis_manager = RedisContext()

# Função utilitária para obter o cliente Redis  
def get_redis_client_instance() -> redis.Redis:  
    return redis_manager.get_client()

# --- Funções de Dependência FastAPI ---  
# Estas são as funções que você usará com Depends() nos seus endpoints/serviços

async def get_database() -> AsyncIOMotorDatabase:  
    """FastAPI dependency to get a MongoDB database instance."""  
    # A conexão é gerenciada pelo lifespan, aqui apenas retornamos a instância  
    try:  
        return get_mongo_db_instance()  
    except RuntimeError as e:  
        # Levantar 503 se o DB não estiver disponível quando solicitado  
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Database connection not available: {e}")

async def get_redis_client() -> redis.Redis:  
    """FastAPI dependency to get a Redis client instance."""  
    # A conexão é gerenciada pelo lifespan  
    try:  
        return get_redis_client_instance()  
    except RuntimeError as e:  
        # Levantar 503 se Redis não estiver disponível quando solicitado  
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Redis connection not available: {e}")

# Adicionar imports faltantes para as dependências  
from fastapi import Depends, HTTPException, status
