# File: backend/app/api/orchestrator.py

import os
import shutil
import uuid
import asyncio
import logging
import random
import requests
from datetime import datetime
from bson import ObjectId

from app.core.database import db
from app.api.ai import (
    call_ai_for_plan,
    call_ai_for_code_with_raw,
    fix_code_with_logs
)
from app.api.conversations import add_message_to_conversation_internal

logger = logging.getLogger(__name__)

async def run_deployment_pipeline(deployment_id: str):
    """
    Orchestrates:
      1. Generate or fix code
      2. Docker build
      3. Docker run
      4. If container fails, feed logs to AI to fix code
      5. Repeat until success or max_iterations
    """
    logger.debug(f"[Orchestrator] Starting pipeline for deployment {deployment_id}")
    deployment = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if not deployment:
        logger.error(f"[Orchestrator] Deployment {deployment_id} not found in DB.")
        return

    conversation_id = deployment["conversation_id"]
    iteration = deployment.get("iteration", 0)
    max_iterations = deployment.get("max_iterations", 5)
    app_type = deployment.get("app_type", "script")

    await update_deployment_field(deployment_id, {"status": "in_progress"})

    build_dir = f"/tmp/build_{deployment_id}_{uuid.uuid4().hex}"
    os.makedirs(build_dir, exist_ok=True)
    last_code_snippets = None
    last_logs = ""

    while iteration < max_iterations:
        iteration += 1
        await append_log(deployment_id, f"Iteration #{iteration} started.")
        await update_deployment_field(deployment_id, {"iteration": iteration})

        # -------------------------------
        # (A) Load conversation doc
        # -------------------------------
        conversation = await db["conversations"].find_one({"_id": ObjectId(conversation_id)})
        if not conversation:
            await append_log(deployment_id, "Conversation doc not found. Aborting orchestrator.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        conversation_messages = conversation.get("messages", [])

        # -------------------------------
        # (A0) Plan Step
        # Pass last iteration logs to help the AI revise
        # -------------------------------
        plan_prompt = f"""
You are the planning assistant. 
Here are logs from the previous iteration (if any):
{last_logs[:3000]}  <-- truncated for safety

If there's a syntax error or container crash, fix it. Provide a bullet-list plan.
"""

        plan_text = await call_ai_for_plan(conversation_messages, plan_prompt)
        if plan_text:
            await append_log(deployment_id, f"AI Plan (Iteration {iteration}):\n{plan_text}")
            await add_message_to_conversation_internal(
                conversation_id,
                {"role": "assistant", "content": plan_text}
            )

        # -------------------------------
        # (B) Generate or fix code (Multi-turn)
        # -------------------------------
        system_msg = _build_system_msg_for_app_type(app_type)
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

        # Avoid infinite loop if code is repeated
        if code_dict == last_code_snippets:
            await append_log(deployment_id, "AI returned the same code as last iteration. Aborting.")
            await update_deployment_field(deployment_id, {"status": "error"})
            break
        last_code_snippets = code_dict

        # Save code as an assistant message
        import json
        code_text = json.dumps(code_dict, indent=2)
        await add_message_to_conversation_internal(
            conversation_id, {"role": "assistant", "content": code_text}
        )

        # -------------------------------
        # (C) Docker Build
        # -------------------------------
        try:
            write_code_to_directory(code_dict, build_dir)
            await append_log(deployment_id, f"Code written to {build_dir}")
        except Exception as e:
            await append_log(deployment_id, f"Error writing code: {str(e)}")
            await update_deployment_field(deployment_id, {"status": "error"})
            break

        build_ok, build_logs = await docker_build(build_dir)
        await append_log(deployment_id, build_logs)
        last_logs = build_logs  # let plan step see build logs next iteration

        if not build_ok:
            # Attempt fix
            fix_ok = await fix_code_with_logs(deployment_id, conversation_id, build_logs)
            if not fix_ok:
                break
            continue

        # -------------------------------
        # (D) Docker Run
        # -------------------------------
        if app_type == "script":
            run_ok, run_logs = await docker_run_script_check()
        else:
            run_ok, run_logs = await docker_run_server_check_host()

        # We always append the run logs
        await append_log(deployment_id, run_logs)
        # let next iteration see them
        last_logs = run_logs

        if not run_ok:
            fix_ok = await fix_code_with_logs(deployment_id, conversation_id, run_logs)
            if not fix_ok:
                break
            continue

        # If container is healthy => success
        await append_log(deployment_id, "Deployment succeeded.")
        await update_deployment_field(deployment_id, {"status": "success"})
        break

    shutil.rmtree(build_dir, ignore_errors=True)

    final_doc = await db["deployments"].find_one({"_id": ObjectId(deployment_id)})
    if final_doc and final_doc["status"] not in ("success", "error"):
        await append_log(deployment_id, "Max iterations reached. Marking as error.")
        await update_deployment_field(deployment_id, {"status": "error"})


def _build_system_msg_for_app_type(app_type: str):
    """
    Returns a system message dict depending on whether we're building a script or server.
    """
    if app_type == "script":
        content = """
You must produce a Python script that exits code 0 upon completion.
Include Dockerfile + requirements.txt if needed.
No extra text, only valid JSON filenames->contents.
"""
    else:
        content = """
You must produce a Python-based web server that listens on 0.0.0.0:5000 indefinitely.
Pin Flask (e.g., Flask==2.2.3). Return valid JSON mapping filenames->contents. 
No extra text or code fences.
"""

    return {"role": "system", "content": content}


async def docker_build(build_dir: str):
    cmd = f"docker build -t ephemeral-test-image {build_dir}"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    rc = proc.returncode
    logs = stdout.decode() + "\n" + stderr.decode()
    return (rc == 0), f"Build Logs:\n{logs}"


async def docker_run_script_check():
    """
    1) Start the container in detached mode
    2) Immediately fetch logs
    3) Sleep 6s, check if running
    4) If still running => fail (script shouldn't keep running)
    5) If not running => check exit code & final logs
    """
    run_cmd = "docker run -d --name ephemeral-test-container ephemeral-test-image"
    proc = await asyncio.create_subprocess_shell(
        run_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    container_id = stdout.decode().strip()
    error_text = stderr.decode().strip()

    if not container_id:
        # If container didn't start, we have no ID => see error_text
        return False, f"Container run error:\n{error_text}"

    # Force fetch logs immediately in case the container already exited with a syntax error
    initial_logs = await _grab_container_logs(container_id)

    # Sleep 6 seconds
    await asyncio.sleep(6)

    # Inspect to see if still running
    inspect_cmd = f"docker inspect --format='{{{{.State.Running}}}}' {container_id}"
    proc_inspect = await asyncio.create_subprocess_shell(
        inspect_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    inspect_out, _ = await proc_inspect.communicate()
    is_running = inspect_out.decode().strip()

    # Grab final logs
    final_logs = await _grab_container_logs(container_id)
    logs_combined = f"Immediate Logs:\n{initial_logs}\n\nFinal Logs:\n{final_logs}"

    # Remove the container
    rm_cmd = f"docker rm -f {container_id}"
    await asyncio.create_subprocess_shell(rm_cmd)

    if is_running.lower() == "true":
        # If it's still running => fail (script should have exited)
        return False, f"Script is still running after 6s.\n{logs_combined}"

    # If not running => check exit code
    ec_cmd = f"docker inspect --format='{{{{.State.ExitCode}}}}' {container_id}"
    proc_ec = await asyncio.create_subprocess_shell(
        ec_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    ec_out, _ = await proc_ec.communicate()
    exit_code = ec_out.decode().strip()

    if exit_code == "0":
        return True, f"Container exited code 0.\n{logs_combined}"
    else:
        return False, f"Container exited code {exit_code}.\n{logs_combined}"


async def docker_run_server_check_host():
    """
    1) Start container in detached mode, random host port
    2) Immediately fetch logs
    3) Sleep 12s, see if it's running
    4) If not running => gather logs & fail
    5) If running => do an HTTP GET => success or fail
    """
    host_port = random.randint(20000, 30000)
    run_cmd = f"docker run -d --name ephemeral-test-container -p {host_port}:5000 ephemeral-test-image"
    proc = await asyncio.create_subprocess_shell(
        run_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    container_id = stdout.decode().strip()
    error_text = stderr.decode().strip()

    if not container_id:
        return False, f"Container run error:\n{error_text}"

    # Immediately fetch logs in case of early exit
    initial_logs = await _grab_container_logs(container_id)

    # Sleep 12 seconds
    await asyncio.sleep(12)

    # Check if running
    inspect_cmd = f"docker inspect --format='{{{{.State.Running}}}}' {container_id}"
    proc_inspect = await asyncio.create_subprocess_shell(
        inspect_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    inspect_out, _ = await proc_inspect.communicate()
    is_running = inspect_out.decode().strip()

    # Grab final logs
    final_logs = await _grab_container_logs(container_id)
    logs_combined = f"Immediate Logs:\n{initial_logs}\n\nFinal Logs:\n{final_logs}"

    if is_running.lower() != "true":
        # Container has exited => fail
        rm_cmd = f"docker rm -f {container_id}"
        await asyncio.create_subprocess_shell(rm_cmd)
        return False, f"Container exited unexpectedly.\n{logs_combined}"

    # If still running => do an HTTP GET
    try:
        resp = requests.get(f"http://127.0.0.1:{host_port}", timeout=4)
        if resp.status_code == 200:
            msg = f"Received HTTP 200 from container on port {host_port}\n{logs_combined}"
            # Cleanup container
            rm_cmd = f"docker rm -f {container_id}"
            await asyncio.create_subprocess_shell(rm_cmd)
            return True, msg
        else:
            # It's running but returned non-200
            rm_cmd = f"docker rm -f {container_id}"
            await asyncio.create_subprocess_shell(rm_cmd)
            return False, f"Health check failed: {resp.status_code}\n{logs_combined}"
    except Exception as e:
        # Possibly connection refused or something else
        rm_cmd = f"docker rm -f {container_id}"
        await asyncio.create_subprocess_shell(rm_cmd)
        return False, f"Error making HTTP request: {str(e)}\n{logs_combined}"


async def _grab_container_logs(container_id: str) -> str:
    """
    Helper function to always grab entire container logs, 
    even if the container exited immediately.
    """
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
    from datetime import datetime
    from bson import ObjectId
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
