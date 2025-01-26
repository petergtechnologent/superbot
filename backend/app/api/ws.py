from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

# Store connected clients keyed by deployment_id
connected_clients: Dict[str, Set[WebSocket]] = {}

async def broadcast_log(deployment_id: str, message: str):
    """
    Send a log message to all WebSocket clients listening to this deployment_id.
    """
    if deployment_id not in connected_clients:
        return
    to_remove = []
    for ws in connected_clients[deployment_id]:
        try:
            await ws.send_text(message)
        except Exception as e:
            logger.debug(f"Error sending WS message: {e}")
            to_remove.append(ws)
    for ws in to_remove:
        connected_clients[deployment_id].remove(ws)

# Optionally, you can keep the websocket route here or in deployments.py
# If you keep it here, in `deployments.py` you'd do:
#   from app.api.ws import ws_router
# and include it in the main app.
