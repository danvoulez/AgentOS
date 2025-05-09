# agentos_core/app/services/embedding_service.py

from openai import AsyncOpenAI, OpenAIError  
from app.core.config import settings  
from loguru import logger  
from typing import List, Optional  
from app.core.logging_config import trace_id_var  
from functools import lru_cache  
from fastapi import HTTPException, status # Para erros críticos

# Usar um cliente separado para embeddings pode ter timeouts/retries diferentes  
@lru_cache()  
def get_embedding_client() -> Optional[AsyncOpenAI]:  
    """Obtém uma instância cacheada do cliente OpenAI para embeddings."""  
    if not settings.OPENAI_API_KEY:  
        logger.error('[Embedding Service] OPENAI_API_KEY not configured. Embedding generation disabled.')  
        return None  
    try:  
        # Timeout um pouco mais curto para embeddings  
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, max_retries=3, timeout=30.0)  
        # Verificar a conexão aqui? Ping não existe em embeddings. Fazer chamada teste? Não.  
        logger.info(f'[Embedding Service] OpenAI client initialized for model {settings.EMBEDDING_MODEL}.')  
        return client  
    except Exception as e:  
        logger.exception(f'[Embedding Service] Failed to initialize OpenAI client: {e}')  
        return None

async def generate_embedding(text: str) -> Optional[List[float]]:  
    """  
    Gera um vetor de embedding para o texto usando o modelo configurado.  
    Valida a dimensão do vetor retornado contra as settings.  
    """  
    log = logger.bind(trace_id=trace_id_var.get(), service="EmbeddingService")  
    aclient_embedding = get_embedding_client()

    if not aclient_embedding:  
        log.error("OpenAI client for embeddings is unavailable.")  
        # Levantar erro aqui? Ou apenas retornar None? Levantar erro se for crítico.  
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Embedding service client not configured.")

    if not text or not isinstance(text, str):  
        log.warning("generate_embedding called with invalid or empty input text.")  
        return None # Não gerar embedding para texto vazio

    # Limpar e preparar texto (recomendação da OpenAI)  
    text_to_embed = text.strip().replace("n", " ")  
    if not text_to_embed:  
        log.warning("Text became empty after cleaning, cannot generate embedding.")  
        return None

    # TODO: Adicionar truncamento baseado em tokens se necessário para o modelo  
    # Ex: max_tokens = 8191 para text-embedding-ada-002  
    # Precisa de uma biblioteca de tokenização (como tiktoken) para fazer isso corretamente.  
    # if len(text_to_embed) > 8000 * 4: # Estimativa grosseira  
    #     log.warning(f"Input text truncated for embedding (length: {len(text_to_embed)})")  
    #     text_to_embed = text_to_embed[:32000] # Limite arbitrário

    model_to_use = settings.EMBEDDING_MODEL  
    expected_dimensions = settings.EMBEDDING_DIMENSIONS  
    log.info(f"Generating embedding (model: {model_to_use}, expected_dims: {expected_dimensions}, text_len: {len(text_to_embed)})")  
    log.trace(f"Text start: '{text_to_embed[:80]}...'")

    try:  
        # Construir argumentos da API  
        embedding_args = {"input": [text_to_embed], "model": model_to_use}  
        # Adicionar 'dimensions' SOMENTE se for um modelo V3 e quiser reduzir  
        # if settings.REQUESTED_EMBEDDING_DIMENSIONS and model_to_use.startswith("text-embedding-3"):  
        #    embedding_args["dimensions"] = settings.REQUESTED_EMBEDDING_DIMENSIONS  
        #    expected_dimensions = settings.REQUESTED_EMBEDDING_DIMENSIONS # Esperar dimensão reduzida

        # Chamar API  
        response = await aclient_embedding.embeddings.create(**embedding_args)

        # Validar resposta  
        if not response.data or not response.data[0].embedding:  
            log.error("OpenAI embedding response missing data or embedding vector.")  
            return None

        embedding = response.data[0].embedding  
        actual_dimensions = len(embedding)

        # Validação CRÍTICA da Dimensão  
        if actual_dimensions != expected_dimensions:  
             log.critical(f"CRITICAL EMBEDDING DIMENSION MISMATCH! Model '{model_to_use}' returned {actual_dimensions} dimensions, but system/DB is configured for {expected_dimensions}. Cannot use embedding.")  
             # Levantar erro aqui é importante para evitar salvar dados inválidos  
             raise ValueError(f"Embedding dimension mismatch: Expected {expected_dimensions}, got {actual_dimensions}")

        log.success(f"Embedding generated successfully. Dimension: {actual_dimensions}")  
        return embedding

    except OpenAIError as e:  
        # Logar detalhes do erro da API OpenAI  
        log.error(f"OpenAI API error during embedding: Status={e.status_code} Msg='{getattr(e, 'message', str(e))}' Type={getattr(e, 'type', 'Unknown')}", exc_info=True)  
        # Levantar erro para indicar falha na geração? Ou retornar None? Retornar None por enquanto.  
        return None  
    except ValueError as ve: # Capturar erro de dimensão  
        # Já logado, apenas re-propagar ou retornar None? Re-propagar é mais claro.  
        raise ve  
    except Exception as e:  
        log.exception(f"Unexpected error generating embedding: {e}")  
        # Levantar erro genérico? Ou retornar None? Retornar None.  
        return None
