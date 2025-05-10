import typer
import asyncio
import json
import httpx
from typing import Optional
from typing_extensions import Annotated
from datetime import datetime, timezone
import websockets
from loguru import logger
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import settings
from app.utils.auth import create_access_token

app_cli = typer.Typer(help="LogLine V2 Developer Tools CLI")

def get_admin_token_for_cli() -> str:
    if not settings.JWT_SECRET: raise ValueError("JWT_SECRET not set for devtools.")
    payload = {
        "sub": "devtools_admin@example.com",
        "uid": "devtools_admin_id_001",
        "roles": ["admin", "staff", "system"]
    }
    return create_access_token(payload)

@app_cli.command("send-log")
def send_log_event(
    log_type: Annotated[str, typer.Option(prompt="LogEvent Type (e.g., test_manual_log)")],
    author: Annotated[str, typer.Option(prompt="Author (e.g., user:devtools_cli)")],
    witness: Annotated[str, typer.Option(prompt="Witness (e.g., system:devtools_script)")],
    data_json: Annotated[str, typer.Option(prompt="Data JSON (e.g., {\"key\":\"value\"})")] = "{}",
    channel: Annotated[str, typer.Option()] = "devtools_cli",
    origin: Annotated[str, typer.Option()] = "SendLogCommand",
):
    logger.info(f"Preparing to send LogEvent: Type='{log_type}' Author='{author}'")
    try:
        parsed_data = json.loads(data_json)
    except json.JSONDecodeError:
        logger.error("Invalid JSON provided for 'data'.")
        raise typer.Exit(code=1)
    editor_payload = {
        "type": log_type, "author": author, "witness": witness,
        "data": parsed_data, "channel": channel, "origin": origin,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "meta": {"source_script": "devtools.py"}
    }
    api_url = f"http://localhost:{settings.API_PORT_FOR_TESTS or 8001}{settings.API_V1_STR}/admin/force_log_event"
    admin_token = get_admin_token_for_cli()
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    try:
        with httpx.Client() as client:
            response = client.post(api_url, json=editor_payload, headers=headers, timeout=10)
            response.raise_for_status()
        logger.success(f"LogEvent sent successfully! Response: {response.json()}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to send LogEvent. Status: {e.response.status_code}, Response: {e.response.text}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")

@app_cli.command("ws-listen")
async def listen_to_websockets(
    token: Annotated[Optional[str], typer.Option(help="JWT access token. If not provided, uses default admin token.")] = None
):
    if not token:
        token = get_admin_token_for_cli()
    ws_url = f"ws://localhost:{settings.API_PORT_FOR_TESTS or 8001}/ws/updates?token={token}"
    logger.info(f"Connecting to WebSocket: {ws_url}")
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.success("Connected to WebSocket. Waiting for messages...")
            while True:
                message = await websocket.recv()
                try:
                    parsed_message = json.loads(message)
                    logger.info(f"WS MSG RX: {json.dumps(parsed_message, indent=2)}")
                except json.JSONDecodeError:
                    logger.info(f"WS MSG RX (raw): {message}")
    except websockets.exceptions.ConnectionClosed as e:
        logger.warning(f"WebSocket connection closed: {e.reason} (Code: {e.code})")
    except ConnectionRefusedError:
        logger.error("WebSocket connection refused. Is the server running and WS endpoint correct?")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

def _run_async(func, *args, **kwargs): asyncio.run(func(*args, **kwargs))

@app_cli.command("ws-listen-run")
def ws_listen_run_wrapper(token: Annotated[Optional[str], typer.Option()] = None):
    asyncio.run(listen_to_websockets(token))

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<level>{message}</level>", colorize=True)
    app_cli()