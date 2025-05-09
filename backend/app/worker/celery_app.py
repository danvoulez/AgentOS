# agentos_core/app/worker/celery_app.py

import os  
from celery import Celery  
from kombu import Queue # Opcional: para filas customizadas  
from loguru import logger

# Importar settings de forma segura  
try:  
    from app.core.config import settings  
except ImportError:  
    # Fallback se rodar celery diretamente sem PYTHONPATH configurado corretamente  
    logger.error("Could not import settings from app.core.config. Ensure PYTHONPATH is set correctly.")  
    # Usar valores padrão ou tentar carregar .env manualmente? Parar é mais seguro.  
    raise SystemExit("Celery worker cannot start without application settings.")

# Inicializar Celery App  
# O nome principal ('agentos_tasks') é usado internamente pelo Celery.  
# O broker e backend são lidos das settings (que leem do .env).  
celery_app = Celery(  
    "agentos_tasks",  
    broker=settings.CELERY_BROKER_URL,  
    backend=settings.CELERY_RESULT_BACKEND,  
    include=[ # Módulos onde as tasks (@celery_app.task) são definidas  
        "app.worker.tasks_agent",  
        "app.worker.tasks_whatsapp",  
    ]  
)

# --- Configuração do Celery ---  
# Carregar configurações adicionais do objeto settings ou definir diretamente.  
celery_app.conf.update(  
    # Serialização: JSON é seguro e legível  
    task_serializer='json',  
    accept_content=['json'],  
    result_serializer='json',

    # Timezone: Recomenda-se usar UTC  
    timezone='UTC',  
    enable_utc=True,

    # Confiabilidade: Importante para garantir processamento  
    # Processa uma task por vez por worker (bom para tasks longas/IO-bound)  
    worker_prefetch_multiplier=1,  
    # Confirma task apenas APÓS sucesso/falha final (evita perda se worker morrer)  
    task_acks_late=True,  
    # Re-enfileira task se o worker morrer inesperadamente  
    task_reject_on_worker_lost=True,

    # Concorrência Padrão (pode ser sobrescrita por variável de ambiente)  
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,

    # Expiração de Resultados (opcional, para limpar backend Redis)  
    result_expires=3600, # Resultados expiram após 1 hora

    # Configuração de Retry Padrão (pode ser sobrescrita por task)  
    task_publish_retry_policy={ # Política para retentar publicar a task se broker falhar  
        'max_retries': 3,  
        'interval_start': 0.5,  
        'interval_step': 0.5,  
        'interval_max': 3.0,  
    },

    # Opcional: Filas e Roteamento (descomentar e ajustar se necessário)  
    # task_default_queue='default',  
    # task_queues=(  
    #     Queue('default'),  
    #     Queue('whatsapp_send'), # Fila específica para envio WA  
    #     Queue('whatsapp_process'), # Fila para processamento IA  
    #     Queue('agent_commands'), # Fila para comandos gerais  
    # ),  
    # task_routes={  
    #     'app.worker.tasks_whatsapp.send_whatsapp_message': {'queue': 'whatsapp_send'},  
    #     'app.worker.tasks_whatsapp.process_agent_whatsapp_message': {'queue': 'whatsapp_process'},  
    #     'app.worker.tasks_agent.*': {'queue': 'agent_commands'},  
    # },

    # Opcional: Beat Schedule (para tasks periódicas)  
    # beat_schedule={  
    #     'cleanup-logs-daily': {  
    #         'task': 'app.worker.tasks_agent.cleanup_logs_task', # Nome da task  
    #         'schedule': crontab(hour=4, minute=0), # Ex: 4 AM UTC  
    #     },  
    # }  
)

# Opcional: Importar crontab se usar beat_schedule  
# from celery.schedules import crontab

# Integração de Logging (Loguru já intercepta, geralmente não necessário)  
# from celery.signals import setup_logging  
# @setup_logging.connect  
# def config_loggers(*args, **kwargs):  
#     from app.core.logging_config import setup_logging # Re-chamar setup? Ou usar config dict?  
#     logger.info("Configuring Celery worker logging...")  
#     # A configuração feita em main.py (intercept handler) deve ser suficiente.  
#     pass

logger.info(f"Celery App '{celery_app.main}' configurado.")  
logger.info(f"Broker: {settings.CELERY_BROKER_URL}")  
logger.info(f"Backend: {settings.CELERY_RESULT_BACKEND}")

# Bloco para permitir execução direta (mas desencorajado)  
if __name__ == "__main__":  
    logger.error("Este script não deve ser executado diretamente.")  
    logger.info("Use o comando 'celery -A app.worker.celery_app worker --loglevel=INFO'")  
    # celery_app.start() # Não recomendado iniciar worker assim
