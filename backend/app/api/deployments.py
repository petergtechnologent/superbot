# File: backend/app/api/deployments.py

from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from bson import ObjectId

from app.core.database import db
from app.core.security import require_role
from app.api.orchestrator import run_deployment_pipeline

router = APIRouter()

class DeploymentStartRequest(BaseModel):
    conversation_id: str
    app_name: Optional[str] = "my-app"
    max_iterations: int = 5  # default 5
    app_type: str = "script"  # "script" or "server"

@router.post("/start")
async def start_deployment(req: DeploymentStartRequest,
                           background_tasks: BackgroundTasks,
                           user=Depends(require_role("user"))):
    """
    Creates a deployment record, spawns orchestrator in background.
    The user can specify max_iterations, plus "script" vs "server".
    """
    deployment_doc = {
        "conversation_id": req.conversation_id,
        "status": "pending",
        "iteration": 0,
        "max_iterations": req.max_iterations,
        "logs": [],
        "app_name": req.app_name,
        "app_type": req.app_type,
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
        "max_iterations": doc.get("max_iterations"),
        "app_type": doc.get("app_type")
    }
