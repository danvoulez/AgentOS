import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from typing import Optional

from app.config import settings
from app.utils.auth import TokenData, verify_jwt_and_get_claims
from app.websocket.connection_manager import manager as ws_connection_manager

logger = logging.getLogger(__name__)
router = APIRouter()

async def get_ws_user_from_jwt(token: str) -> Optional[TokenData]:
    if not token:
        logger.debug("WS Auth: No token provided.")
        return None
    try:
        claims = verify_jwt_and_get_claims(token)
        user_id_claim = claims.get("uid") or claims.get("sub")
        if not user_id_claim:
            logger.warning("WS Auth: JWT valid but missing 'uid' or 'sub' claim.")
            return None
        return TokenData(sub=claims.get("sub"), roles=claims.get("roles", []), uid=str(user_id_claim))
    except HTTPException as e:
        logger.warning(f"WS Auth: Invalid JWT - {e.detail}")
        return None
    except Exception as e:
        logger.error(f"WS Auth: Unexpected error validating JWT for WebSocket: {e}", exc_info=True)
        return None

@router.websocket("/updates")
async def websocket_updates_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT for WebSocket authentication (passed as query parameter 'token')")
):
    token_data: Optional[TokenData] = await get_ws_user_from_jwt(token)

    if not token_data or not token_data.sub:
        logger.warning("WebSocket connection rejected: Authentication failed or missing identifier.")
        await websocket.accept()
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed: Invalid or missing token")
        return

    connection_user_id = token_data.uid if token_data.uid else token_data.sub

    await ws_connection_manager.connect(websocket, connection_user_id)
    client_host = websocket.client.host if websocket.client else "unknown"
    client_port = websocket.client.port if websocket.client else "unknown"
    log_context = logger.bind(ws_user=connection_user_id, client_ip=f"{client_host}:{client_port}", trace_id=logger.extra.get("trace_id"))
    log_context.info(f"WebSocket connection established.")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=getattr(settings, "WEBSOCKET_IDLE_TIMEOUT_SECONDS", 60.0))
                log_context.debug(f"Received WS message: '{data}'")
                if data.lower() == "ping":
                    await websocket.send_text("pong")
                    log_context.debug("Sent pong in response to client ping.")
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("server_keepalive_ping")
                    log_context.trace(f"Sent server_keepalive_ping.")
                except (WebSocketDisconnect, RuntimeError):
                    raise WebSocketDisconnect(code=status.WS_1001_GOING_AWAY, reason="Keepalive send failed")
            except WebSocketDisconnect:
                raise
    except WebSocketDisconnect as e:
        log_context.info(f"WebSocket disconnected: Code {e.code}, Reason: '{e.reason or 'Client disconnected'}'")
    except Exception as e:
        log_context.exception(f"Unexpected error in WebSocket connection.")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_SERVER_ERROR)
        except:
            pass
    finally:
        await ws_connection_manager.disconnect(websocket, connection_user_id)
        log_context.info(f"WebSocket cleanup complete.")