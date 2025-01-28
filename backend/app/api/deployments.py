# File: backend/app/api/deployments.py

from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
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
    app_name: Optional[str] = "flex-fastapi-app"
    max_iterations: int = 5
    port_number: int = 9000
    trouble_mode: bool = False

@router.post("/start")
async def start_deployment(
    req: DeploymentStartRequest,
    background_tasks: BackgroundTasks,
    user=Depends(require_role("user"))
):
    """
    Creates a deployment record, spawns the orchestrator in background.
    trouble_mode: leave container running if it fails (for debugging).
    Containers also remain running on success by default.
    """
    deployment_doc = {
        "conversation_id": req.conversation_id,
        "status": "pending",
        "iteration": 0,
        "max_iterations": req.max_iterations,
        "logs": [],
        "app_name": req.app_name,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "port_number": req.port_number,
        "trouble_mode": req.trouble_mode,
        "container_id": None,
        "user_id": user["user_id"]
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
    # If not admin, ensure user is owner
    if user["role"] != "admin" and doc.get("user_id") != user["user_id"]:
        raise HTTPException(403, "Forbidden")

    return {
        "deployment_id": deployment_id,
        "status": doc["status"],
        "logs": doc["logs"],
        "iteration": doc.get("iteration"),
        "max_iterations": doc.get("max_iterations"),
        "port_number": doc.get("port_number"),
        "trouble_mode": doc.get("trouble_mode", False),
        "container_id": doc.get("container_id"),
    }

@router.get("/running-services")
async def list_running_services(user=Depends(require_role("user"))):
    """
    Return a list of deployments where status=success and container_id != None.
    If user is 'admin', show all. Otherwise, show only their own.
    """
    query = {"status": "success", "container_id": {"$ne": None}}
    if user["role"] != "admin":
        query["user_id"] = user["user_id"]

    cursor = db["deployments"].find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc.pop("logs", None)
        results.append(doc)

    return results

class StopServiceRequest(BaseModel):
    deployment_id: str

@router.post("/stop")
async def stop_running_service(req: StopServiceRequest, user=Depends(require_role("user"))):
    """
    Takes a deployment_id that has status=success, container_id != None,
    calls 'docker rm -f {container_id}', sets status='stopped', container_id=None.
    """
    dep = await db["deployments"].find_one({"_id": ObjectId(req.deployment_id)})
    if not dep:
        raise HTTPException(404, "Deployment not found.")
    if dep.get("status") != "success" or not dep.get("container_id"):
        raise HTTPException(400, "Service is not running.")
    # if user is normal user, must match user_id
    if user["role"] != "admin" and dep.get("user_id") != user["user_id"]:
        raise HTTPException(403, "Forbidden.")

    container_id = dep["container_id"]
    # Attempt to remove
    import subprocess

    try:
        subprocess.run(["docker", "rm", "-f", container_id], check=False)
    except Exception as e:
        raise HTTPException(500, f"Error removing container: {str(e)}")

    # update DB
    await db["deployments"].update_one(
        {"_id": ObjectId(req.deployment_id)},
        {"$set": {"status": "stopped", "container_id": None, "updated_at": datetime.utcnow()}}
    )
    return {"message": "Service stopped.", "deployment_id": req.deployment_id}
