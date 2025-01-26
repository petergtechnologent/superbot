import os
import shutil
import uuid
import asyncio
import logging
from datetime import datetime
from bson import ObjectId

from app.core.database import db
from app.api.ai import call_ai_for_code_with_raw

logger = logging.getLogger(__name__)

async def run_deployment_pipeline(deployment_id: str):
    """
    Main loop that coordinates AI code generation, build, fix, and final deploy.
    Iterates until success or max_iterations.
    """
    deployment = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if not deployment:
        logger.error(f"Deployment {deployment_id} not found in DB.")
        return

    conversation_id = deployment["conversation_id"]
    iteration = deployment.get("iteration", 0)
    max_iterations = deployment.get("max_iterations", 5)

    # Mark status as in_progress
    await update_deployment_field(deployment_id, {"status": "in_progress"})

    build_dir = f"/tmp/build_{deployment_id}_{uuid.uuid4().hex}"
    os.makedirs(build_dir, exist_ok=True)

    while iteration < max_iterations:
        iteration += 1
        await append_log(deployment_id, f"Iteration #{iteration} started.")
        await update_deployment_field(deployment_id, {"iteration": iteration})

        # 1) Get the user idea from the conversation doc
        conversation = await db["conversations"].find_one({"_id": ObjectId(conversation_id)})
        user_idea = ""
        if conversation and "messages" in conversation:
            # e.g., the first user message
            if conversation["messages"]:
                user_idea = conversation["messages"][0].get("content", "")

        # 2) Build a system_message that includes the user’s idea
        system_message = f"""
The user wants the following application:
{user_idea}

Please produce a COMPLETE codebase in valid JSON, including backend and frontend if relevant.
"""

        # 3) Call the AI to get code
        code_dict, raw_texts = await call_ai_for_code_with_raw(
            conversation_id,
            system_message=system_message
        )

        if not code_dict:
            # Log raw attempts so we see what the AI returned
            for i, raw_txt in enumerate(raw_texts, start=1):
                await append_log(deployment_id, f"Raw AI attempt #{i}:\n{raw_txt}")
            await append_log(deployment_id, "No code returned from AI. Aborting.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        # 4) Write code to ephemeral directory
        try:
            write_code_to_directory(code_dict, build_dir)
            await append_log(deployment_id, f"Code written to {build_dir}")
        except Exception as e:
            await append_log(deployment_id, f"Failed to write code to dir: {str(e)}")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        # 5) Attempt to build
        success, logs = await run_build_and_test(build_dir)
        await append_log(deployment_id, logs)

        if success:
            await append_log(deployment_id, "Build & test successful. Proceeding to final deploy.")
            deploy_success, deploy_logs = await run_final_deploy(build_dir)
            await append_log(deployment_id, deploy_logs)

            if deploy_success:
                await update_deployment_field(deployment_id, {"status": "success"})
                await append_log(deployment_id, "Deployment succeeded.")
            else:
                await update_deployment_field(deployment_id, {"status": "error"})
                await append_log(deployment_id, "Deployment failed.")
            break
        else:
            # If build/test fails, prompt the AI for a fix
            await append_log(deployment_id, "Build/test failed. Requesting AI fix...")

            fix_prompt = f"""
We attempted to build the code but got this error:
{logs}

Please fix the code. Return a valid JSON with updated files only.
"""
            fix_dict, fix_texts = await call_ai_for_code_with_raw(
                conversation_id,
                system_message=fix_prompt
            )
            if not fix_dict:
                for i, raw_txt in enumerate(fix_texts, start=1):
                    await append_log(deployment_id, f"Raw AI fix attempt #{i}:\n{raw_txt}")
                await append_log(deployment_id, "AI did not fix the error. Aborting.")
                await update_deployment_field(deployment_id, {"status": "error"})
                break

            # Overwrite or patch the code
            shutil.rmtree(build_dir, ignore_errors=True)
            os.makedirs(build_dir, exist_ok=True)
            write_code_to_directory(fix_dict, build_dir)
            await append_log(deployment_id, "Code updated with fix. Will re-attempt next iteration.")

    # Cleanup ephemeral dir
    shutil.rmtree(build_dir, ignore_errors=True)

    # If we never broke out with success or final error
    final = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if final and final["status"] not in ("success", "error"):
        await append_log(deployment_id, "Max iterations reached. Marking as error.")
        await update_deployment_field(deployment_id, {"status": "error"})

# ---------------
# HELPER FUNCTIONS
# ---------------
def write_code_to_directory(code_snippets: dict, build_dir: str):
    for filename, content in code_snippets.items():
        file_path = os.path.join(build_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

async def run_build_and_test(build_dir: str):
    cmd = f"docker build -t ephemeral-test-image {build_dir}"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode
    logs = stdout.decode() + "\n" + stderr.decode()
    return (rc == 0), f"Build Logs:\n{logs}"

async def run_final_deploy(build_dir: str):
    cmd = "docker run -d -p 8080:8080 ephemeral-test-image"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode
    logs = stdout.decode() + "\n" + stderr.decode()
    return (rc == 0), f"Deploy Logs:\n{logs}"

async def append_log(deployment_id: str, message: str):
    logger.info(f"[Deployment {deployment_id}] {message}")
    await db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)},
        {
            "$push": {"logs": message},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    # If you have a broadcast_log for websockets:
    # from app.api.ws import broadcast_log
    # await broadcast_log(deployment_id, message)

async def update_deployment_field(deployment_id: str, fields: dict):
    await db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)},
        {"$set": {**fields, "updated_at": datetime.utcnow()}}
    )
