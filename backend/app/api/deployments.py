from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from typing import Dict, Set
import asyncio

from app.core.database import db
from app.core.security import require_role
from app.api.orchestrator import run_deployment_pipeline

router = APIRouter()

# --------------------------------------------------------------------------------
# In-memory registry of WS connections: deployment_id -> set of websockets
# --------------------------------------------------------------------------------
connected_clients: Dict[str, Set[WebSocket]] = {}


# ---------------------------
# Model for starting a deploy
# ---------------------------
class DeploymentStartRequest(BaseModel):
    conversation_id: str
    app_name: str = "my-app"
    max_iterations: int = 5


@router.post("/start")
async def start_deployment(
    req: DeploymentStartRequest,
    background_tasks: BackgroundTasks,
    user=Depends(require_role("user"))
):
    """
    Creates a deployment record and spawns the orchestrator in background.
    """
    deployment_doc = {
        "conversation_id": req.conversation_id,
        "status": "pending",
        "iteration": 0,
        "max_iterations": req.max_iterations,
        "logs": [],
        "app_name": req.app_name,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = await db["deployments"].insert_one(deployment_doc)
    deployment_id = str(result.inserted_id)

    # Kick off background job
    background_tasks.add_task(run_deployment_pipeline, deployment_id)

    return {"deployment_id": deployment_id, "status": "started"}


@router.get("/{deployment_id}/status")
async def get_deployment_status(deployment_id: str, user=Depends(require_role("user"))):
    """
    Returns the current status and logs of a deployment.
    For advanced role checks, ensure only the owner or admin can view.
    """
    doc = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if not doc:
        return {"error": "Deployment not found"}

    # If user role != admin, you might check if user["user_id"] is the same as the conversation's owner, etc.

    return {
        "deployment_id": deployment_id,
        "status": doc["status"],
        "logs": doc["logs"],
        "iteration": doc.get("iteration"),
        "max_iterations": doc.get("max_iterations")
    }


# -------------------------------------------
# WebSocket endpoint to stream logs in real time
# -------------------------------------------
@router.websocket("/logs/ws/{deployment_id}")
async def deployment_logs_ws(websocket: WebSocket, deployment_id: str):
    await websocket.accept()

    if deployment_id not in connected_clients:
        connected_clients[deployment_id] = set()
    connected_clients[deployment_id].add(websocket)

    try:
        while True:
            # Keep the connection open; no data is expected from client
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients[deployment_id].remove(websocket)


# -------------------------------------------
# Helper function to broadcast logs
# -------------------------------------------
async def broadcast_log(deployment_id: str, message: str):
    if deployment_id not in connected_clients:
        return
    to_remove = []
    for ws in connected_clients[deployment_id]:
        try:
            await ws.send_text(message)
        except:
            to_remove.append(ws)
    # Clean up dead connections
    for ws in to_remove:
        connected_clients[deployment_id].remove(ws)
