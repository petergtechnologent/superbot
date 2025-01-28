# File: backend/app/api/ai.py

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json

from bson import ObjectId
from typing import Any

from app.core.security import require_role
from app.core.database import db
from app.api.conversations import add_message_to_conversation_internal

# Import from prompt_manager
from app.core.prompt_manager import (
    build_flex_spec_prompt,
    parse_json_safely,
    call_ai_for_code,
    generate_text_from_prompt,
    build_fix_prompt,
    normalize_code_snippet
)

logger = logging.getLogger(__name__)
router = APIRouter()

class TransformSpecRequest(BaseModel):
    userIdea: str

@router.post("/transform_flex_spec")
async def transform_flex_spec(request: TransformSpecRequest, user=Depends(require_role("user"))):
    user_text = request.userIdea.strip()
    if not user_text:
        raise HTTPException(400, "Empty user idea.")

    system_prompt = build_flex_spec_prompt(user_text)
    raw_response = await generate_text_from_prompt(system_prompt)
    spec_dict = parse_json_safely(raw_response)

    if not spec_dict:
        raise HTTPException(
            400,
            f"Could not parse a valid Flex Spec from AI response:\n{raw_response}"
        )

    if "endpoints" not in spec_dict or not isinstance(spec_dict["endpoints"], list):
        spec_dict["endpoints"] = []
    has_root = any(ep.get("path") == "/" for ep in spec_dict["endpoints"])
    if not has_root:
        spec_dict["endpoints"].append({
            "path": "/",
            "method": "GET",
            "description": "Health/status endpoint returning { 'status': 'ok' }"
        })

    return spec_dict

class CodeGenRequest(BaseModel):
    conversation_id: str
    prompt: str

@router.post("/generate")
async def generate_code(req: CodeGenRequest, user=Depends(require_role("user"))):
    logger.info("Received code generation request (multi-turn).")

    convo = await db["conversations"].find_one({"_id": ObjectId(req.conversation_id)})
    if not convo:
        raise HTTPException(404, "Conversation not found; cannot generate code.")

    conversation_messages = convo.get("messages", [])

    # Default to 9000 if not found in conversation
    port = 9000
    for msg in reversed(conversation_messages):
        if msg["role"] == "user":
            try:
                user_content = json.loads(msg["content"])
                if isinstance(user_content, dict) and "port" in user_content:
                    port = user_content["port"]
                    break
            except:
                pass

    code_dict, raw_attempts = await call_ai_for_code(
        conversation_messages=conversation_messages,
        user_prompt=req.prompt,
        port=port
    )

    if not code_dict:
        combined_tries = "\n\n---\n\n".join(raw_attempts)
        return {
            "generated_code": (
                "Could not parse a valid code snippet from the AI.\n"
                f"Raw attempts:\n{combined_tries}"
            )
        }

    generated_text = json.dumps(code_dict, indent=2)
    logger.info("Multi-turn code generation succeeded. Returning JSON code.")
    return {"generated_code": generated_text}

async def fix_code_with_logs(deployment_id: str, conversation_id: str, raw_logs: str):
    from app.api.orchestrator import append_log, update_deployment_field

    lines = raw_logs.splitlines()
    highlights = []
    for i, line in enumerate(lines[:300], start=1):
        if any(err_word in line.lower() for err_word in ("traceback", "error", "syntaxerror")):
            highlights.append(f"[ERROR] {line}")
        else:
            highlights.append(line)

    snippet = "\n".join(highlights)
    known_fixes = diagnose_common_errors(raw_logs)
    fix_prompt = build_fix_prompt(snippet, known_fixes)

    convo_obj = await db["conversations"].find_one({"_id": ObjectId(conversation_id)})
    if not convo_obj:
        await append_log(deployment_id, "Conversation not found; cannot fix code.")
        await update_deployment_field(deployment_id, {"status": "error"})
        return False

    raw_fix_text = await generate_text_from_prompt(fix_prompt)
    code_dict = normalize_code_snippet(parse_json_safely(raw_fix_text))

    if not code_dict:
        await append_log(deployment_id, f"Raw AI fix attempt:\n{raw_fix_text}")
        await append_log(deployment_id, "AI did not fix the error. Aborting.")
        await update_deployment_field(deployment_id, {"status": "error"})
        return False

    import json
    code_text = json.dumps(code_dict, indent=2)
    await add_message_to_conversation_internal(
        conversation_id,
        {"role": "assistant", "content": code_text}
    )

    await append_log(deployment_id, "AI returned a code fix. Will try again next iteration.")
    return True

import re

ERROR_PATTERNS = {
    r"cannot import name 'url_quote' from 'werkzeug.urls'": """
Your logs suggest a Flask/Werkzeug mismatch.
Try pinning in requirements.txt:
Flask==2.2.3
Werkzeug==2.2.3
"""
}

def diagnose_common_errors(log_text: str) -> str:
    for pattern, fix_text in ERROR_PATTERNS.items():
        if re.search(pattern, log_text, flags=re.IGNORECASE):
            return fix_text.strip()
    return ""
