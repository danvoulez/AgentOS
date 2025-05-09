# agentos_core/app/services/whatsapp_service.py

from app.core.config import settings  
from loguru import logger  
import httpx  
from typing import Optional, Tuple, Dict, Any # Adicionar Dict, Any  
from app.core.logging_config import trace_id_var  
import json # Para log de erro

# --- Constantes ---  
META_GRAPH_API_VERSION = "v19.0" # Usar versão atual da API Graph  
META_GRAPH_API_BASE_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"

# --- HTTP Client (Recomendado: Criar um cliente reutilizável) ---  
# Pode ser instanciado globalmente ou via dependência FastAPI  
# Por simplicidade, vamos instanciar em cada chamada por enquanto, mas NÃO é ideal para produção.  
# def get_httpx_client() -> httpx.AsyncClient:  
#     return httpx.AsyncClient(timeout=25.0, http2=True) # Timeout razoável

async def send_whatsapp_text_message(  
    recipient_wa_id: str,  
    message_text: str  
    ) -> Tuple[bool, Optional[str]]:  
    """  
    Envia uma mensagem de texto via Meta Graph API (WhatsApp).

    Retorna (True, wami) em sucesso, (False, None) em falha.  
    """  
    log = logger.bind(trace_id=trace_id_var.get(), service="WhatsAppService", recipient=recipient_wa_id)

    # 1. Validação de Configuração e Input  
    if not all([settings.META_ACCESS_TOKEN, settings.META_PHONE_NUMBER_ID]):  
        log.critical("WhatsApp API credentials (Token, Phone ID) missing. Cannot send message.")  
        return False, None # Falha crítica  
    if not recipient_wa_id or not message_text:  
         log.error("Attempted to send WhatsApp message with missing recipient or text.")  
         return False, None

    # 2. Preparar Request  
    api_url = f"{META_GRAPH_API_BASE_URL}/{settings.META_PHONE_NUMBER_ID}/messages"  
    headers = {  
        "Authorization": f"Bearer {settings.META_ACCESS_TOKEN}",  
        "Content-Type": "application/json"  
    }  
    payload = {  
        "messaging_product": "whatsapp",  
        "to": recipient_wa_id, # Número sem '+' ou outros caracteres não numéricos  
        "type": "text",  
        # Não incluir preview_url para evitar problemas com links  
        "text": {"preview_url": False, "body": message_text}  
    }

    log.info("Attempting to send WhatsApp text message via Meta API...")  
    log.debug(f"Target URL: {api_url}")  
    # Evitar logar payload completo por padrão devido ao conteúdo da mensagem  
    # log.trace(f"Request Payload: {payload}")

    # 3. Executar Chamada API  
    try:  
        # Usar cliente HTTPX gerenciado seria melhor  
        async with httpx.AsyncClient(timeout=25.0, http2=True) as client:  
            response = await client.post(api_url, headers=headers, json=payload)

        log.debug(f"Meta API Response Status Code: {response.status_code}")  
        # Tentar ler corpo da resposta, mesmo em erro, para log  
        response_data: Dict[str, Any] = {}  
        response_text_snippet: str = ""  
        try:  
            response_data = response.json()  
            log.trace(f"Meta API Raw Response Body: {response_data}")  
        except json.JSONDecodeError:  
            response_text_snippet = response.text[:500] # Pegar início se não for JSON  
            log.error(f"Meta API returned non-JSON response (Status: {response.status_code}): {response_text_snippet}")  
            # Se não for 2xx e não for JSON, considerar falha  
            if not (200 <= response.status_code < 300):  
                 return False, None

        # 4. Processar Resposta  
        if 200 <= response.status_code < 300:  
            # Sucesso (mensagem aceita pela API da Meta)  
            # WAMI (WhatsApp Message ID) é a confirmação principal  
            wami = response_data.get("messages", [{}])[0].get("id")  
            if wami:  
                 log.success(f"WhatsApp message accepted by Meta API. WAMI: {wami}")  
                 return True, wami  
            else:  
                 # Código 2xx mas sem WAMI? Incomum. Logar e tratar como sucesso parcial.  
                 log.warning(f"WhatsApp message API call returned 2xx status but no WAMI found in response.")  
                 return True, None  
        else:  
            # Erro reportado pela API Meta  
            error_info = response_data.get("error", {})  
            error_message = error_info.get("message", response_text_snippet or "Unknown API error")  
            error_type = error_info.get("type", "API Error")  
            error_code = error_info.get("code", response.status_code) # Usar code do erro se disponível  
            fbtrace_id = error_info.get("fbtrace_id", "N/A")  
            log.error(f"Failed to send WhatsApp message. Status={response.status_code}, Code={error_code}, Type='{error_type}', Message='{error_message}', FBTrace={fbtrace_id}")  
            return False, None

    # Capturar erros de HTTPX (rede, timeout, etc.)  
    except httpx.TimeoutException:  
        log.error("Timeout error sending WhatsApp message to Meta API.")  
        return False, None  
    except httpx.RequestError as e:  
        log.error(f"HTTP request error sending WhatsApp message: {e}", exc_info=True)  
        return False, None  
    # Capturar outros erros inesperados  
    except Exception as e:  
        log.exception(f"Unexpected error sending WhatsApp message: {e}")  
        return False, None

# --- Placeholder para outras funções de serviço WhatsApp ---  
# async def get_media_url(media_id: str) -> Optional[str]: ...  
# async def download_media(media_url: str) -> Optional[bytes]: ...  
# async def mark_message_as_read(wami: str): ...
