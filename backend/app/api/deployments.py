from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Set
from datetime import datetime
from bson import ObjectId

from app.core.database import db
from app.core.security import require_role
from app.api.orchestrator import run_deployment_pipeline
from app.api.ws import connected_clients  # So we can manage them

router = APIRouter()

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
    # Insert deployment record
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

    background_tasks.add_task(run_deployment_pipeline, deployment_id)
    return {"deployment_id": deployment_id, "status": "started"}

@router.get("/{deployment_id}/status")
async def get_deployment_status(deployment_id: str, user=Depends(require_role("user"))):
    doc = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if not doc:
        return {"error": "Deployment not found"}
    return {
        "deployment_id": deployment_id,
        "status": doc["status"],
        "logs": doc["logs"],
        "iteration": doc.get("iteration"),
        "max_iterations": doc.get("max_iterations")
    }

@router.websocket("/logs/ws/{deployment_id}")
async def deployment_logs_ws(websocket: WebSocket, deployment_id: str):
    await websocket.accept()

    if deployment_id not in connected_clients:
        connected_clients[deployment_id] = set()
    connected_clients[deployment_id].add(websocket)

    try:
        while True:
            await websocket.receive_text()  # or ignore
    except WebSocketDisconnect:
        connected_clients[deployment_id].remove(websocket)
