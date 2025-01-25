from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel
from datetime import datetime
from app.core.database import db
from app.core.security import require_role

router = APIRouter()

class DeployRequest(BaseModel):
    conversation_id: str
    environment: str  # e.g. "docker-compose", "k8s", etc.

@router.post("/")
async def trigger_deployment(deploy_req: DeployRequest, user=Depends(require_role("user"))):
    # Insert a doc in "deployments" to track status
    deployment_doc = {
        "conversation_id": deploy_req.conversation_id,
        "environment": deploy_req.environment,
        "status": "pending",
        "created_at": datetime.utcnow(),
        "logs": []
    }
    result = await db["deployments"].insert_one(deployment_doc)
    return {"deployment_id": str(result.inserted_id)}

@router.websocket("/logs/ws")
async def deployment_logs_ws(websocket: WebSocket):
    await websocket.accept()
    try:
        import asyncio
        for i in range(5):
            await asyncio.sleep(1)
            await websocket.send_text(f"Log line #{i+1}")
        await websocket.close()
    except WebSocketDisconnect:
        pass
