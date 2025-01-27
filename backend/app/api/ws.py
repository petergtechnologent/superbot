from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

ws_router = APIRouter()
connected_clients: Dict[str, Set[WebSocket]] = {}

@ws_router.websocket("/deployments/logs/ws/{deployment_id}")
async def deployment_logs_ws(websocket: WebSocket, deployment_id: str):
    """
    This route is optional if you want a separate file for WS. 
    Otherwise, you can keep it in deployments.py 
    """
    await websocket.accept()
    if deployment_id not in connected_clients:
        connected_clients[deployment_id] = set()
    connected_clients[deployment_id].add(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients[deployment_id].remove(websocket)
        if not connected_clients[deployment_id]:
            del connected_clients[deployment_id]

async def broadcast_log(deployment_id: str, message: str):
    """
    Called by orchestrator's append_log
    """
    if deployment_id not in connected_clients:
        return
    dead_sockets = []
    for ws in connected_clients[deployment_id]:
        try:
            await ws.send_text(message)
        except:
            dead_sockets.append(ws)
    for ds in dead_sockets:
        connected_clients[deployment_id].remove(ds)
    if not connected_clients[deployment_id]:
        del connected_clients[deployment_id]
