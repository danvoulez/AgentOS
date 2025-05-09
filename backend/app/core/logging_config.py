# agentos_core/app/core/logging_config.py

import sys  
import logging  
from loguru import logger  
from app.core.config import settings  
import uuid  
import contextvars  
from typing import cast # Adicionar cast  
from datetime import datetime, timezone

# Context variable para Trace ID  
# Usar um tipo mais específico, Default a None  
trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="unset")

# Handler para interceptar logging padrão  
class InterceptHandler(logging.Handler):  
    def emit(self, record: logging.LogRecord):  
        # Tentar obter nível do Loguru correspondente  
        try: level = logger.level(record.levelname).name  
        except ValueError: level = record.levelno

        # Encontrar frame correto (fora do módulo logging)  
        frame, depth = logging.currentframe(), 2  
        while frame.f_code.co_filename == logging.__file__:  
            frame = frame.f_back # type: ignore  
            depth += 1  
        # Se frame for None (improvável), logar do ponto atual  
        if frame is None: frame = logging.currentframe(); depth = 0

        # Obter trace_id do contexto atual  
        trace_id = trace_id_var.get() # Pode ser "unset" se não definido

        # Vincular trace_id ao log do Loguru  
        logger.opt(depth=depth, exception=record.exc_info, lazy=True).bind(  
            trace_id=trace_id  
        ).log(level, record.getMessage()) # Formatar mensagem aqui

# Função de Setup do Logging  
def setup_logging():  
    """Configura Loguru como handler principal e define formatos."""  
    logger.info("Initializing Loguru logging configuration...")

    # Remover handlers padrão do Loguru para evitar duplicação  
    logger.remove()

    log_level = settings.LOG_LEVEL.upper()  
    # Ativar diagnose (mais detalhes em erros) apenas se o nível for DEBUG  
    diagnose_flag = log_level == "DEBUG"

    # Sink para Console (stderr) - formato rico e colorido  
    logger.add(  
        sys.stderr,  
        level=log_level,  
        format=(  
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}Z</green> | "  
            "<level>{level: <8}</level> | "  
            "<cyan>{name}:{function}:{line}</cyan> | "  
            # Formatar trace_id, usando '...' se for muito longo ou 'NoTID' se 'unset'  
            "<magenta>TID:{extra[trace_id]: >12.12}</magenta> | "  
            "<level>{message}</level>"  
        ),  
        enqueue=True,       # Escrita assíncrona para performance  
        backtrace=True,     # Tracebacks mais detalhados  
        diagnose=diagnose_flag, # Detalhes extras em erros (se DEBUG)  
        colorize=True       # Habilitar cores no terminal  
    )

    # Opcional: Sink para Arquivo  
    # log_file_path = "logs/agentos_core_{time:YYYY-MM-DD}.log"  
    # try:  
    #     logger.add(  
    #         log_file_path,  
    #         level="INFO", # Nível diferente para arquivo  
    #         rotation="10 MB", retention="7 days", compression="zip",  
    #         enqueue=True,  
    #         # Formato mais completo para arquivo  
    #         format="{time:YYYY-MM-DD HH:mm:ss.SSS}Z|{level: <8}|{process}|{thread}|{name}:{function}:{line}|TID:{extra[trace_id]}|{message}",  
    #         encoding="utf-8"  
    #     )  
    #     logger.info(f"File logging configured: {log_file_path}")  
    # except Exception as e:  
    #     logger.error(f"Failed to configure file logging: {e}")

    # Interceptar logging padrão do Python  
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)  
    # Silenciar loggers muito verbosos de bibliotecas (opcional)  
    # logging.getLogger("httpx").setLevel(logging.WARNING)  
    # logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.success(f"Loguru configured. Console log level: {log_level}")

# Middleware FastAPI para Trace ID  
async def add_trace_id_middleware(request, call_next):  
    """Gera/propaga Trace ID via contextvars para cada request."""  
    # Tenta pegar ID existente ou gera um novo  
    request_trace_id = request.headers.get("X-Request-ID") or f"req_{uuid.uuid4().hex[:12]}"  
    # Define o trace_id para este contexto de requisição  
    token = trace_id_var.set(request_trace_id)

    # Vincular ao logger para todos os logs dentro desta requisição  
    with logger.contextualize(trace_id=request_trace_id):  
        client_host = request.client.host if request.client else "unknown_host"  
        client_port = request.client.port if request.client else "unknown_port"  
        logger.info(f"Request START: {request.method} {request.url.path} from {client_host}:{client_port}")  
        start_time = datetime.now(timezone.utc)  
        response = None  
        try:  
            response = await call_next(request) # Processa a requisição  
            # Adicionar trace ID ao header da resposta  
            response.headers["X-Trace-ID"] = request_trace_id  
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000  
            logger.info(f"Request END: {request.method} {request.url.path} Status: {response.status_code} Duration: {duration_ms:.2f}ms")  
            return response  
        except Exception as e:  
             # Logar exceção não tratada com traceback completo  
             duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000  
             logger.exception(f"Unhandled exception during request {request.method} {request.url.path}. Duration: {duration_ms:.2f}ms")  
             # Adicionar trace ID à resposta de erro (se possível, handler de exceção fará isso)  
             # if response: response.headers["X-Trace-ID"] = request_trace_id # Response pode não existir aqui  
             raise e # Re-lançar para handler global do FastAPI  
        finally:  
            # Limpar contextvar ao final da requisição  
            trace_id_var.reset(token)
