import os
import shutil
import subprocess
import uuid
import asyncio
import logging
from datetime import datetime
from bson import ObjectId
from app.core.database import db
from app.api.ai import call_ai_for_code  # We'll add this helper in ai.py
logger = logging.getLogger(__name__)

async def run_deployment_pipeline(deployment_id: str):
    """
    Main loop that coordinates AI code generation, build, fix, and final deploy.
    Iterates until success or max_iterations.
    """
    # 1) Retrieve deployment doc
    deployment = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if not deployment:
        logger.error(f"Deployment {deployment_id} not found in DB.")
        return

    conversation_id = deployment["conversation_id"]
    iteration = deployment.get("iteration", 0)
    max_iterations = deployment.get("max_iterations", 5)

    # 2) Mark status as in_progress
    await update_deployment_field(deployment_id, {"status": "in_progress"})

    # 3) Create an ephemeral directory for building code
    build_dir = f"/tmp/build_{deployment_id}_{uuid.uuid4().hex}"
    os.makedirs(build_dir, exist_ok=True)

    # 4) Start iteration loop
    while iteration < max_iterations:
        iteration += 1
        await append_log(deployment_id, f"Iteration #{iteration} started.")
        await update_deployment_field(deployment_id, {"iteration": iteration})

        # A) Retrieve or fix code
        code_snippets = await get_code_for_iteration(conversation_id, deployment_id, iteration)
        if not code_snippets:
            await append_log(deployment_id, "No code returned from AI. Aborting.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        # B) Write code to ephemeral directory
        try:
            write_code_to_directory(code_snippets, build_dir)
            await append_log(deployment_id, f"Code written to {build_dir}")
        except Exception as e:
            await append_log(deployment_id, f"Failed to write code to dir: {str(e)}")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        # C) Attempt to build (and optionally test)
        success, logs = await run_build_and_test(build_dir)
        await append_log(deployment_id, logs)

        if success:
            # Deployment pipeline succeeded in building
            await append_log(deployment_id, "Build & test successful. Proceeding to final deploy.")
            deploy_success, deploy_logs = await run_final_deploy(build_dir, deployment_id)
            await append_log(deployment_id, deploy_logs)

            if deploy_success:
                await update_deployment_field(deployment_id, {"status": "success"})
                await append_log(deployment_id, "Deployment succeeded.")
            else:
                await update_deployment_field(deployment_id, {"status": "error"})
                await append_log(deployment_id, "Deployment failed.")
            break
        else:
            # Build/test failed => re-prompt AI with logs
            await append_log(deployment_id, "Build/test failed. Requesting AI fix...")
            success_fix = await get_ai_fix_for_logs(logs, conversation_id, deployment_id)
            if not success_fix:
                await append_log(deployment_id, "AI did not fix the error. Aborting.")
                await update_deployment_field(deployment_id, {"status": "error"})
                break

    # Cleanup ephemeral directory
    shutil.rmtree(build_dir, ignore_errors=True)

    # If we exceeded max_iterations
    final_deployment = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if final_deployment and final_deployment["status"] not in ("success", "error"):
        await append_log(deployment_id, "Max iterations reached. Marking as error.")
        await update_deployment_field(deployment_id, {"status": "error"})


async def get_code_for_iteration(conversation_id: str, deployment_id: str, iteration: int):
    """
    Request code from the AI for the initial or subsequent iteration.
    For simplicity, we assume you have a special AI function call
    that returns a dictionary of all needed files.
    """
    try:
        # We pass the conversation ID and iteration if we want to handle context specially
        code = await call_ai_for_code(conversation_id)
        return code
    except Exception as e:
        logger.exception("Error retrieving code from AI.")
        return None


async def get_ai_fix_for_logs(error_logs: str, conversation_id: str, deployment_id: str):
    """
    Prompt the AI with the build/test error logs, ask for an updated code base.
    """
    fix_prompt = f"""
We attempted to build and/or test the application, but failed with the following logs:

{error_logs}

Please fix the code accordingly. Return the entire updated code base.
"""
    try:
        updated_code = await call_ai_for_code(conversation_id, system_message=fix_prompt)
        return True if updated_code else False
    except Exception as e:
        logger.exception("Error retrieving fix from AI.")
        return False


def write_code_to_directory(code_snippets, build_dir: str):
    """
    Suppose code_snippets is a dict:
      {
        "Dockerfile": "...contents...",
        "requirements.txt": "...contents...",
        "src/app.py": "...contents..."
      }
    We'll write each file into the ephemeral directory.
    """
    for filename, content in code_snippets.items():
        file_path = os.path.join(build_dir, filename)
        # Make sure subdirectories exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


async def run_build_and_test(build_dir: str):
    """
    Example function to run a Docker build (or local build).
    Returns (success, logs).
    """
    # Command to build Docker image (named ephemeral-test-image)
    cmd = f"docker build -t ephemeral-test-image {build_dir}"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode
    logs = stdout.decode() + "\n" + stderr.decode()

    success = (rc == 0)
    return success, f"Build Logs:\n{logs}"


async def run_final_deploy(build_dir: str, deployment_id: str):
    """
    Simple example: run a container locally.
    For production, push to k8s or call Docker Compose, etc.
    """
    cmd = "docker run -d -p 8080:8080 ephemeral-test-image"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode
    logs = stdout.decode() + "\n" + stderr.decode()

    success = (rc == 0)
    return success, f"Deploy Logs:\n{logs}"


async def update_deployment_field(deployment_id, fields: dict):
    await db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)},
        {"$set": {**fields, "updated_at": datetime.utcnow()}}
    )


async def append_log(deployment_id, new_log: str):
    """
    Writes log text to the DB and optionally broadcasts
    it to any connected WebSocket clients.
    """
    logger.info(f"[Deployment {deployment_id}] {new_log}")
    await db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)},
        {
            "$push": {"logs": new_log},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    # If you want real-time WS broadcasting:
    from app.api.deployments import broadcast_log
    await broadcast_log(deployment_id, new_log)
