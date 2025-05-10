import logging
from typing import Dict, List, Set, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.lock = asyncio.Lock()
        logger.info("WebSocket ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        logger.info(f"WebSocket connected for user: {user_id}. User connections: {len(self.active_connections.get(user_id, set()))}, Total distinct users: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        async with self.lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                logger.info(f"WebSocket disconnected for user: {user_id}. Remaining users: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):
        log = logger.bind(target_user_id=user_id, message_type=message.get("type"))
        connections_to_send: List[WebSocket] = []
        async with self.lock:
            connections_to_send = list(self.active_connections.get(user_id, set()))

        if not connections_to_send:
            log.debug("No active WebSocket connections found for user to send personal message.")
            return

        log.debug(f"Sending personal message to {len(connections_to_send)} connections for user.")
        for connection in connections_to_send:
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError) as e:
                log.warning(f"Error sending to user {user_id} (conn likely closed): {type(e).__name__}. Will be cleaned up.")
            except Exception as e:
                log.error(f"Failed to send personal message to a connection for user {user_id}: {e}", exc_info=True)

    async def broadcast(self, message: Dict[str, Any], exclude_user_ids: Optional[List[str]] = None):
        log = logger.bind(broadcast_message_type=message.get("type"), trace_id=logger.extra.get("trace_id"))
        log.info("Broadcasting message to active WebSocket connections...")
        all_websockets_to_send: List[WebSocket] = []
        async with self.lock:
            for user_id, connections_set in self.active_connections.items():
                if exclude_user_ids and user_id in exclude_user_ids:
                    continue
                all_websockets_to_send.extend(list(connections_set))

        if not all_websockets_to_send:
            log.debug("No active connections to broadcast to.")
            return
        log.debug(f"Broadcasting to {len(all_websockets_to_send)} total WebSocket connections.")

        send_tasks = [ws.send_json(message) for ws in all_websockets_to_send]
        results = await asyncio.gather(*send_tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, (WebSocketDisconnect, RuntimeError)):
                log.warning(f"Error during broadcast (conn likely closed, index {i}): {type(result).__name__}")
            elif isinstance(result, Exception):
                log.error(f"Unexpected error during broadcast (index {i}): {result}", exc_info=True)
        log.info("Broadcast attempt finished.")

manager = ConnectionManager()