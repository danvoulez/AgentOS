# agentos_core/app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict  
from pydantic import Field  
from functools import lru_cache  
from loguru import logger  
from pathlib import Path  
import warnings  
import os

# Helper function find_dotenv_path (mantido)  
def find_dotenv_path(filename='.env', raise_error_if_not_found=False, usecwd=False) -> str | None:  
    # (Código da função find_dotenv_path como na resposta anterior)  
    if usecwd or '__file__' not in globals(): start_dir = Path.cwd()  
    else: start_dir = Path(__file__).resolve().parent  
    current_dir = start_dir  
    for _ in range(10):  
        env_path = current_dir / filename  
        if env_path.is_file(): logger.debug(f"Found .env file at: {env_path}"); return str(env_path)  
        parent_dir = current_dir.parent  
        if parent_dir == current_dir: break  
        current_dir = parent_dir  
    if not usecwd and '__file__' in globals():  
         env_path_cwd = Path.cwd() / filename  
         if env_path_cwd.is_file(): logger.debug(f"Found .env file at CWD: {env_path_cwd}"); return str(env_path_cwd)  
    logger.debug(f"{filename} not found in parent directories of {start_dir} or CWD.")  
    if raise_error_if_not_found: raise IOError(f'{filename} not found')  
    return None

class Settings(BaseSettings):  
    PROJECT_NAME: str = "AgentOS Core"  
    API_V1_STR: str = "/api/v1"  
    LOG_LEVEL: str = "INFO"

    # Database & Cache  
    MONGODB_URI: str  
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")  
    CELERY_BROKER_URL: str  
    CELERY_RESULT_BACKEND: str

    # AI Services  
    OPENAI_API_KEY: str  
    GEMINI_API_KEY: str | None = None

    # Embedding  
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", env="EMBEDDING_MODEL")  
    EMBEDDING_DIMENSIONS: int = Field(default=1536, env="EMBEDDING_DIMENSIONS")

    # MongoDB Atlas Search  
    MONGO_MEMORY_SEARCH_INDEX_NAME: str = Field(default="vector_index_memories", env="MONGO_MEMORY_SEARCH_INDEX_NAME")

    # Security  
    SECRET_KEY: str # For JWT  
    ALGORITHM: str = "HS256"  
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  
    API_KEY: str # Static API Key

    # Meta / WhatsApp API Credentials  
    META_APP_SECRET: str | None = None  
    META_ACCESS_TOKEN: str | None = None  
    META_PHONE_NUMBER_ID: str | None = None  
    META_VERIFY_TOKEN: str | None = None

    # Sentry (Optional)  
    SENTRY_DSN: str | None = None

    # Default Test User (Para testes e mocks iniciais)  
    DEFAULT_TEST_USERNAME: str = "testuser"  
    DEFAULT_TEST_PASSWORD: str = "testpassword"  
    # Default Currency (Exemplo)  
    DEFAULT_CURRENCY: str = "BRL"

    # Celery Concurrency (Exemplo de leitura direta do env)  
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv('CELERY_WORKER_CONCURRENCY', '4'))

    model_config = SettingsConfigDict(  
        # Tenta carregar .env primeiro, depois .env.local (que pode sobrescrever)  
        env_file=(find_dotenv_path('.env'), find_dotenv_path('.env.local')),  
        env_file_encoding='utf-8',  
        extra='ignore', # Ignora variáveis extras no .env  
        case_sensitive=False, # Permite variáveis de ambiente em maiúsculas ou minúsculas  
    )

@lru_cache()  
def get_settings() -> Settings:  
    """Carrega e valida as configurações da aplicação."""  
    logger.info("Loading application settings...")  
    # Logar qual arquivo .env foi encontrado (se algum)  
    env_files_found = [p for p in [find_dotenv_path('.env'), find_dotenv_path('.env.local')] if p]  
    if env_files_found:  
        logger.info(f"Loading environment variables from: {', '.join(env_files_found)}")  
    else:  
        logger.warning("No .env file found. Loading settings from system environment variables only.")

    try:  
        # Pydantic-settings carrega do .env e depois sobrescreve com variáveis de ambiente do sistema  
        settings_instance = Settings()

        # Validação Mínima de Variáveis Críticas  
        required_vars = ['MONGODB_URI', 'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND', 'OPENAI_API_KEY', 'SECRET_KEY', 'API_KEY']  
        missing = [k for k in required_vars if not getattr(settings_instance, k, None)] # Usar getattr com default None  
        if missing:  
            logger.critical(f"Missing critical environment variables: {', '.join(missing)}")  
            raise ValueError(f"Missing critical environment variables: {', '.join(missing)}")

        # Alerta de Segurança para SECRET_KEY padrão  
        if settings_instance.SECRET_KEY == "!!!GENERATE_A_STRONG_SECRET_KEY_32_BYTES_HEX!!!":  
            logger.warning("SECURITY WARNING: Using default SECRET_KEY. Generate a strong key (e.g., `openssl rand -hex 32`) and set it in your environment!")  
            warnings.warn("SECURITY WARNING: Using default SECRET_KEY. Please generate and set a strong secret key!")

        # Validação WhatsApp (Apenas logar aviso se faltar)  
        wa_keys = ['META_APP_SECRET', 'META_ACCESS_TOKEN', 'META_PHONE_NUMBER_ID', 'META_VERIFY_TOKEN']  
        missing_wa = [k for k in wa_keys if not getattr(settings_instance, k, None)]  
        if missing_wa:  
            logger.warning(f"WhatsApp API keys missing ({', '.join(missing_wa)}). WhatsApp functionality will be limited or disabled.")

        logger.info("Settings loaded and validated successfully.")  
        return settings_instance  
    except ValueError as val_err: # Capturar erro de validação Pydantic  
        logger.critical(f"CRITICAL ERROR in settings validation: {val_err}", exc_info=True)  
        raise SystemExit(f"Settings validation failed: {val_err}")  
    except Exception as e: # Capturar outros erros de carregamento  
        logger.critical(f"CRITICAL ERROR loading settings: {e}", exc_info=True)  
        raise SystemExit(f"Failed to load critical settings: {e}")

# Instância global das configurações para fácil importação  
settings = get_settings()
