# File: backend/app/api/orchestrator.py

import os
import shutil
import uuid
import asyncio
import logging
import requests
from datetime import datetime
from bson import ObjectId

from app.core.database import db
from app.api.ai import (
    call_ai_for_code_with_raw,
    fix_code_with_logs
)
from app.api.conversations import add_message_to_conversation_internal

logger = logging.getLogger(__name__)

async def run_deployment_pipeline(deployment_id: str):
    """
    Orchestrates the deployment pipeline:
      1. Generate or fix code
      2. Docker build ephemeral-test-image
      3. Docker run ephemeral container
      4. Health check
      5. If trouble_mode=False and container fails, remove it and attempt fix.
         Otherwise, keep container on success or if trouble_mode=True on failure.
      6. Repeat until success or max_iterations
    """
    logger.debug(f"[Orchestrator] Starting pipeline for deployment {deployment_id}")
    deployment = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if not deployment:
        logger.error(f"[Orchestrator] Deployment {deployment_id} not found in DB.")
        return

    conversation_id = deployment["conversation_id"]
    iteration = deployment.get("iteration", 0)
    max_iterations = deployment.get("max_iterations", 5)
    target_port = deployment.get("port_number", 9000)
    trouble_mode = deployment.get("trouble_mode", False)

    await update_deployment_field(deployment_id, {"status": "in_progress"})

    build_dir = f"/tmp/build_{deployment_id}_{uuid.uuid4().hex}"
    os.makedirs(build_dir, exist_ok=True)

    last_code_snippets = None
    last_logs = ""

    while iteration < max_iterations:
        iteration += 1
        await append_log(deployment_id, f"Iteration #{iteration} started.")
        await update_deployment_field(deployment_id, {"iteration": iteration})

        # 1) Load conversation doc
        conversation = await db["conversations"].find_one({"_id": ObjectId(conversation_id)})
        if not conversation:
            await append_log(deployment_id, "Conversation doc not found. Aborting orchestrator.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        conversation_messages = conversation.get("messages", [])

        # 2) Multi-turn code generation
        system_msg = {
            "role": "system",
            "content": f"""
You must produce a Python FastAPI app that listens on 0.0.0.0:{target_port}.
Return JSON mapping filenames->file contents. The Dockerfile must run:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{target_port}"].
"""
        }
        code_dict, raw_attempts = await call_ai_for_code_with_raw(
            conversation_messages=conversation_messages,
            system_messages=[system_msg]
        )
        if not code_dict:
            for i, txt in enumerate(raw_attempts, start=1):
                await append_log(deployment_id, f"Raw AI attempt #{i}:\n{txt}")
            await append_log(deployment_id, "No code returned from AI. Aborting.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        if code_dict == last_code_snippets:
            await append_log(deployment_id, "AI returned identical code. Aborting to avoid loop.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break
        last_code_snippets = code_dict

        # Save the code as an assistant message
        import json
        code_text = json.dumps(code_dict, indent=2)
        await add_message_to_conversation_internal(
            conversation_id, {"role": "assistant", "content": code_text}
        )

        # 3) Docker build ephemeral-test-image
        try:
            write_code_to_directory(code_dict, build_dir)
            await append_log(deployment_id, f"Code written to {build_dir}")
        except Exception as e:
            await append_log(deployment_id, f"Error writing code: {str(e)}")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        build_ok, build_logs = await docker_build(build_dir)
        await append_log(deployment_id, build_logs)
        last_logs = build_logs

        if not build_ok:
            # Attempt fix
            fix_ok = await fix_code_with_logs(deployment_id, conversation_id, build_logs)
            if not fix_ok:
                break
            continue

        # 4) Docker run ephemeral container & check
        run_ok, run_logs, container_id = await docker_run_server_check_host(
            deployment_id=deployment_id,
            port=target_port,
            trouble_mode=trouble_mode
        )
        await append_log(deployment_id, run_logs)
        last_logs = run_logs

        if run_ok:
            # Mark container as running in DB so user can stop it later
            await update_deployment_field(deployment_id, {"container_id": container_id})
            await append_log(deployment_id, f"Service is accessible on port {target_port}. SUCCESS!")
            await update_deployment_field(deployment_id, {"status": "success"})
            break
        else:
            if trouble_mode:
                # user wants to keep container even if it fails
                await append_log(
                    deployment_id,
                    f"Trouble mode is ON: Container {container_id} left running for debugging."
                )
                await update_deployment_field(deployment_id, {"status": "error"})
                break
            else:
                fix_ok = await fix_code_with_logs(deployment_id, conversation_id, run_logs)
                if not fix_ok:
                    break
                continue

    shutil.rmtree(build_dir, ignore_errors=True)

    final_doc = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if final_doc and final_doc["status"] not in ("success", "error"):
        await append_log(deployment_id, "Max iterations reached. Marking as error.")
        await update_deployment_field(deployment_id, {"status": "error"})


async def docker_build(build_dir: str):
    cmd = f"docker build -t ephemeral-test-image {build_dir}"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode
    logs = stdout.decode() + "\n" + stderr.decode()
    return (rc == 0), f"Build Logs:\n{logs}"

async def docker_run_server_check_host(deployment_id: str, port: int, trouble_mode: bool):
    """
    1) Create a container name = ephemeral-test-container-{deployment_id}.
    2) Run ephemeral-test-image in the same Docker network as 'backend',
       with '-p {port}:{port}' so it's accessible at localhost:{port}.
    3) Wait ~12s, then call http://{container_name}:{port}/
    4) If container fails or times out, remove it unless trouble_mode=True.
    5) Return (run_ok, logs, container_id).
    """
    container_name = f"ephemeral-test-container-{deployment_id}"

    # First remove any old container with the same name
    rm_old = f"docker rm -f {container_name}"
    await asyncio.create_subprocess_shell(rm_old)

    run_cmd = (
        f"docker run -d --name {container_name} "
        f"--network=superbot_default "
        f"-p {port}:{port} "
        "ephemeral-test-image"
    )

    proc = await asyncio.create_subprocess_shell(
        run_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    new_container_id = stdout.decode().strip()
    error_text = stderr.decode().strip()
    if not new_container_id:
        return (False, f"Container run error:\n{error_text}", "")

    # Grab initial logs
    initial_logs = await _grab_container_logs(new_container_id)

    # Wait 12 seconds for the server to (hopefully) come up
    await asyncio.sleep(12)

    # Check if container is still running
    inspect_cmd = f"docker inspect --format='{{{{.State.Running}}}}' {new_container_id}"
    proc_inspect = await asyncio.create_subprocess_shell(
        inspect_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    inspect_out, _ = await proc_inspect.communicate()
    is_running = inspect_out.decode().strip().lower()

    final_logs = await _grab_container_logs(new_container_id)
    logs_combined = f"Immediate Logs:\n{initial_logs}\n\nFinal Logs:\n{final_logs}"

    if is_running != "true":
        msg = f"Container exited unexpectedly.\n{logs_combined}"
        if not trouble_mode:
            # remove it if it failed
            rm_cmd = f"docker rm -f {new_container_id}"
            await asyncio.create_subprocess_shell(rm_cmd)
        return (False, msg, new_container_id)

    # Attempt HTTP GET from inside the Docker network
    try:
        url = f"http://{container_name}:{port}/"
        resp = requests.get(url, timeout=4)
        if resp.status_code == 200:
            # Container stays running on success
            return (True, f"HTTP 200 OK on {url}\n{logs_combined}", new_container_id)
        else:
            msg = f"Service returned {resp.status_code} at {url}\n{logs_combined}"
            if not trouble_mode:
                rm_cmd = f"docker rm -f {new_container_id}"
                await asyncio.create_subprocess_shell(rm_cmd)
            return (False, msg, new_container_id)
    except Exception as e:
        msg = f"Error calling {url}: {str(e)}\n{logs_combined}"
        if not trouble_mode:
            rm_cmd = f"docker rm -f {new_container_id}"
            await asyncio.create_subprocess_shell(rm_cmd)
        return (False, msg, new_container_id)

async def _grab_container_logs(container_id: str) -> str:
    logs_cmd = f"docker logs {container_id}"
    proc_logs = await asyncio.create_subprocess_shell(
        logs_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    logs_out, logs_err = await proc_logs.communicate()
    combined = logs_out.decode(errors="replace") + logs_err.decode(errors="replace")
    return combined.strip()

def write_code_to_directory(code_snippets: dict, build_dir: str):
    import shutil
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)
    for filename, content in code_snippets.items():
        file_path = os.path.join(build_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

async def append_log(deployment_id: str, new_log: str):
    logger.info(f"[Deployment {deployment_id}] {new_log}")
    from app.api.ws import broadcast_log
    await db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)},
        {
            "$push": {"logs": new_log},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    await broadcast_log(deployment_id, new_log)

async def update_deployment_field(deployment_id: str, fields: dict):
    from datetime import datetime
    from bson import ObjectId
    await db["deployments"].update_one(
        {"_id": ObjectId(deployment_id)},
        {"$set": {**fields, "updated_at": datetime.utcnow()}}
    )
