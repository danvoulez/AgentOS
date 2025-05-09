# agentos_core/app/api/endpoints/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status as http_status  
from loguru import logger  
import uuid  
from typing import Annotated  
import hmac # Para API Key

# Manager, Security, Config  
from app.websocket.connection_manager import manager as ws_manager  
from app.core.security import settings, CredentialsException  
from app.core.logging_config import trace_id_var  
# Importar JWT decode se usar token (mas API Key é mais simples para WS)  
from jose import jwt, JWTError

router = APIRouter()

# --- Dependência de Autenticação WebSocket (API Key) ---  
async def verify_ws_api_key(  
    websocket: WebSocket,  
    apiKey: str | None = Query(None, alias="apiKey", description="Static API key for WS authentication")  
) -> str:  
    """Verifica API Key passada como query param."""  
    log = logger.bind(websocket_client=f"{websocket.client.host}:{websocket.client.port}", service="WSAuth")  
    expected_api_key = settings.API_KEY

    if not expected_api_key: # Segurança: não permitir conectar se a chave esperada não estiver configurada  
        log.critical("Static API_KEY for WebSocket authentication is not configured in the backend!")  
        raise WebSocketDisconnect(code=http_status.WS_1011_INTERNAL_ERROR, reason="Server configuration error")

    # Usar compare_digest para segurança contra timing attacks  
    if not apiKey or not hmac.compare_digest(apiKey, expected_api_key):  
        log.warning("WebSocket connection rejected: Invalid or missing API Key.")  
        raise WebSocketDisconnect(code=http_status.WS_1008_POLICY_VIOLATION, reason="Invalid API Key")

    # Identificador para o usuário conectado via API Key  
    # Pode ser um ID fixo ou derivado da chave (mas não a chave inteira)  
    user_id = f"api_key_user:{expected_api_key[:5]}...{expected_api_key[-3:]}"  
    log.info(f"WebSocket authenticated via API Key. Assigned ID: {user_id}")  
    return user_id

# --- Endpoint WebSocket ---  
@router.websocket("/updates", name="websocket_updates")  
async def websocket_endpoint(  
    websocket: WebSocket,  
    # Usar a dependência de autenticação API Key  
    user_id: str = Depends(verify_ws_api_key)  
):  
    """  
    Endpoint WebSocket para atualizações em tempo real.  
    Requer autenticação via `?apiKey=...` query parameter.  
    """  
    # Gerar/Obter Trace ID para logs desta conexão  
    trace_id = trace_id_var.get() or f"ws_{uuid.uuid4().hex[:8]}"  
    log = logger.bind(trace_id=trace_id, websocket_client=f"{websocket.client.host}:{websocket.client.port}", user=user_id)

    # Conectar ao manager após autenticação bem-sucedida  
    await ws_manager.connect(websocket, user_id=user_id)  
    connection_active = True

    try:  
        # Enviar mensagem de boas-vindas/status  
        await ws_manager.send_personal_message(  
            {"type": "connection_status", "status": "connected", "user_id": user_id},  
            user_id  
        )

        # Loop principal: manter conexão e ouvir mensagens do cliente (ex: ping)  
        while connection_active:  
            try:  
                data = await websocket.receive_text()  
                log.debug(f"Received message: {data}")  
                # Responder a pings para keep-alive  
                if data.strip().lower() == 'ping':  
                    await websocket.send_text('pong')  
                    log.debug("Sent pong response.")  
                # Processar outros comandos do cliente se necessário  
                # else: ...

            except WebSocketDisconnect as e:  
                 log.info(f"WebSocket disconnected cleanly (code: {e.code}, reason: '{e.reason}').")  
                 connection_active = False # Sair do loop  
                 # O bloco finally cuidará da desconexão do manager

            except Exception as loop_err:  
                 # Erros inesperados durante a comunicação  
                 log.exception(f"Error during WebSocket receive/process loop: {loop_err}")  
                 # Tentar fechar com código de erro antes de sair do loop  
                 await websocket.close(code=http_status.WS_1011_INTERNAL_ERROR)  
                 connection_active = False # Sair do loop

    except Exception as conn_err:  
        # Erros durante a fase de conexão inicial (raro após Depends bem-sucedido)  
        log.exception(f"Unhandled WebSocket error during connection phase: {conn_err}")  
    finally:  
        # Garantir que a desconexão do manager seja chamada sempre  
        log.debug("Executing WebSocket finally block...")  
        await ws_manager.disconnect(websocket, user_id=user_id)  
        log.info("WebSocket cleanup complete.")
