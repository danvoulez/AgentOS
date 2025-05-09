*_(Fim do Arquivo: `agentos_core/app/tools/basic_actions.py`)*_

---

Com isso, finalizamos os serviços e ferramentas no `app/services/` e `app/tools/`. O próximo passo é gerar o código consolidado para os **WebSockets e Workers**."""),  
            ],  
        ),  
        types.Content(  
            role="user",  
            parts=[  
                types.Part.from_text(text="""continue"""),  
            ],  
        ),  
        types.Content(  
            role="model",  
            parts=[  
                types.Part.from_text(text="""Perfeito! Vamos gerar o código consolidado para os módulos **WebSocket (`app/websocket/`)** e **Worker (`app/worker/`)**.

---  
**Arquivo: `agentos_core/app/websocket/connection_manager.py`**  
---```python  
# agentos_core/app/websocket/connection_manager.py

from fastapi import WebSocket, WebSocketDisconnect, status as ws_status # Renomear status  
from typing import List, Dict, Set, Optional, Tuple, Any # Adicionar Any  
from loguru import logger  
import json  
import asyncio

class ConnectionManager:  
    """  
    Gerencia conexões WebSocket ativas, mapeando user_id para um conjunto de WebSockets.  
    Permite múltiplas conexões por usuário (ex: múltiplas abas/dispositivos).  
    """  
    def __init__(self):  
        # Dicionário para armazenar conexões: user_id -> {ws1, ws2, ...}  
        self.active_connections: Dict[str, Set[WebSocket]] = {}  
        # Lock assíncrono para proteger o acesso concorrente ao dicionário  
        self._lock = asyncio.Lock()  
        logger.info("ConnectionManager initialized.")

    async def connect(self, websocket: WebSocket, user_id: str):  
        """Aceita uma nova conexão WebSocket e a associa a um user_id."""  
        await websocket.accept()  
        client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "Unknown Client"  
        log = logger.bind(user_id=user_id, client=client_info)

        async with self._lock:  
            if user_id not in self.active_connections:  
                self.active_connections[user_id] = set()  
            self.active_connections[user_id].add(websocket)  
            # Contar conexões totais de forma segura  
            count = sum(len(s) for s in self.active_connections.values())

        log.info(f"WebSocket connected. User Cons: {len(self.active_connections.get(user_id, set()))} | Total Cons: {count}")

    async def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):  
        """Remove uma conexão WebSocket, encontrando o user_id se não fornecido."""  
        client_info = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "Unknown Client"  
        log = logger.bind(user_id=user_id or "N/A", client=client_info)  
        removed = False  
        disconnected_user = user_id # Manter track do usuário desconectado

        async with self._lock:  
            target_user_id = user_id  
            # Se user_id não foi fornecido, tentar encontrá-lo  
            if not target_user_id:  
                 for uid, ws_set in self.active_connections.items():  
                     if websocket in ws_set:  
                         target_user_id = uid  
                         log.debug(f"User ID '{uid}' found for disconnecting websocket.")  
                         break

            # Se encontramos ou tínhamos o user_id, remover a conexão específica  
            if target_user_id and target_user_id in self.active_connections:  
                if websocket in self.active_connections[target_user_id]:  
                    self.active_connections[target_user_id].remove(websocket)  
                    removed = True  
                    disconnected_user = target_user_id # Confirmar usuário  
                    # Se o usuário não tem mais conexões, remover a entrada do dicionário  
                    if not self.active_connections[target_user_id]:  
                        del self.active_connections[target_user_id]  
                        log.debug(f"Removed empty user entry for '{target_user_id}'.")  
                else:  
                     log.warning("Websocket not found in the specified user's connection set.")  
            elif target_user_id:  
                 log.warning(f"User ID '{target_user_id}' not found in active connections during disconnect.")  
            else:  
                 log.warning("Could not determine User ID for disconnecting websocket.")

            # Atualizar contagem total  
            count = sum(len(s) for s in self.active_connections.values())

        if removed:  
            log.info(f"WebSocket disconnected successfully. User: '{disconnected_user}' | Total Cons: {count}")  
        else:  
            log.debug(f"Attempted to disconnect WebSocket that was not found or already removed. User: '{disconnected_user or 'Unknown'}'")

    async def send_personal_message(self, message: Dict[str, Any], user_id: str):  
        """Envia uma mensagem JSON para todas as conexões de um usuário específico."""  
        log = logger.bind(websocket_target=user_id, message_type=message.get("type", "unknown"))  
        async with self._lock:  
            # Obter uma cópia da lista de conexões para evitar problemas de concorrência  
            connections = list(self.active_connections.get(user_id, set()))

        if not connections:  
             # Logar em debug se for comum, warning se for inesperado  
             log.debug(f"No active WebSocket connections found for user '{user_id}'. Personal message not sent.")  
             return

        log.info(f"Sending personal message to user '{user_id}' ({len(connections)} connection(s)).")  
        log.trace(f"Message Content: {message}") # Usar trace para conteúdo detalhado  
        message_json = json.dumps(message, default=str) # Serializar uma vez, tratar tipos não serializáveis

        # Enviar para todas as conexões do usuário em paralelo  
        send_tasks = [ws.send_text(message_json) for ws in connections]  
        results = await asyncio.gather(*send_tasks, return_exceptions=True)

        # Lidar com erros/desconexões durante o envio  
        disconnected_on_send: List[WebSocket] = []  
        for i, result in enumerate(results):  
            if isinstance(result, Exception):  
                websocket = connections[i]  
                log.warning(f"Send failed for client {websocket.client}: {result}. Scheduling disconnect.")  
                # Adicionar à lista para desconectar fora do loop principal de envio  
                disconnected_on_send.append(websocket)

        # Desconectar sockets que falharam  
        if disconnected_on_send:  
            log.warning(f"Disconnecting {len(disconnected_on_send)} sockets for user '{user_id}' due to send errors.")  
            # Chamar disconnect para cada um (o método disconnect é async)  
            disconnect_tasks = [self.disconnect(ws, user_id) for ws in disconnected_on_send]  
            await asyncio.gather(*disconnect_tasks, return_exceptions=True) # Logar erros de disconnect se houver

    async def broadcast(self, message: Dict[str, Any]):  
        """Envia uma mensagem JSON para TODAS as conexões ativas."""  
        log = logger.bind(websocket_target="broadcast", message_type=message.get("type", "unknown"))

        async with self._lock:  
            # Criar uma lista plana de todas as conexões e seus user_ids associados  
            all_connections_with_users: List[Tuple[WebSocket, str]] = []  
            for user_id, ws_set in self.active_connections.items():  
                for ws in ws_set:  
                    all_connections_with_users.append((ws, user_id))  
            count = len(all_connections_with_users)

        if count == 0:  
            log.debug("Broadcast skipped: No active connections.")  
            return

        log.info(f"Broadcasting message to {count} total connection(s).")  
        log.trace(f"Broadcast Content: {message}")  
        message_json = json.dumps(message, default=str)

        # Preparar tarefas de envio  
        send_tasks = [conn_tuple[0].send_text(message_json) for conn_tuple in all_connections_with_users]  
        results = await asyncio.gather(*send_tasks, return_exceptions=True)

        # Lidar com erros/desconexões durante o broadcast  
        disconnected_on_broadcast: List[Tuple[WebSocket, str]] = []  
        for i, result in enumerate(results):  
            if isinstance(result, Exception):  
                websocket, user_id = all_connections_with_users[i]  
                log.warning(f"Broadcast send failed for client {websocket.client} (User: {user_id}): {result}. Scheduling disconnect.")  
                disconnected_on_broadcast.append((websocket, user_id))

        # Desconectar sockets que falharam  
        if disconnected_on_broadcast:  
            log.warning(f"Disconnecting {len(disconnected_on_broadcast)} sockets due to broadcast send errors.")  
            disconnect_tasks = [self.disconnect(ws, uid) for ws, uid in disconnected_on_broadcast]  
            await asyncio.gather(*disconnect_tasks, return_exceptions=True) # Logar erros de disconnect se houver

# --- Singleton Instance ---  
# Criar uma única instância do manager para ser usada em toda a aplicação  
manager = ConnectionManager()
