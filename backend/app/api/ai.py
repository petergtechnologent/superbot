# File: backend/app/api/ai.py

import logging
import requests
import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import re
from typing import List, Dict, Any

from bson import ObjectId
from app.core.config import AI_PROVIDER, OLLLAMA_HOST, OPENAI_API_KEY, AI_MODEL
from app.core.security import require_role
from app.core.database import db
from app.api.conversations import add_message_to_conversation_internal

logger = logging.getLogger(__name__)
router = APIRouter()

DOCKER_TOOL_DOC = """
Tool: DockerBuilder
Purpose: Build and run Docker containers with generated code.
Constraints:
1. Dockerfile is required for building an image (named ephemeral-test-image).
2. We can run the container via 'docker run'.
3. For scripts, the container should exit with code 0. For servers, it runs indefinitely on port 5000.
4. Return only code in JSON, mapping filenames->string contents. No extra text or code fences.
"""

class CodeGenRequest(BaseModel):
    conversation_id: str
    prompt: str

@router.post("/generate")
async def generate_code(req: CodeGenRequest, user=Depends(require_role("user"))):
    """
    One-off code snippet generation route for the initial user prompt only.
    The orchestrator code handles multi-turn logic with logs/fixes.
    """
    logger.info("Received code generation request.")
    logger.debug(f"Prompt: {req.prompt}, Provider: {AI_PROVIDER}, Model: {AI_MODEL}")

    generated_text = await _generate_text_single(req.prompt)
    logger.info("Code generation successful, returning generated_text.")
    return {"generated_code": generated_text}

# -------------------------------------------------------------------
# call_ai_for_plan
# Accepts a custom system_prompt for logs, etc.
# -------------------------------------------------------------------
async def call_ai_for_plan(
    conversation_messages: List[Dict[str, str]],
    system_prompt: str
) -> str:
    plan_prompt = system_prompt + f"\n\nRemember the Docker usage info:\n{DOCKER_TOOL_DOC}\n"

    final_messages = [{"role": "system", "content": plan_prompt}]
    final_messages.extend(conversation_messages)

    if AI_PROVIDER == "ollama":
        raw_plan = await _ollama_generate_multiturn(final_messages)
    else:
        raw_plan = await _openai_generate_multiturn(final_messages)

    return raw_plan.strip()

# -------------------------------------------------------------------
# Single-turn
# -------------------------------------------------------------------
async def _generate_text_single(prompt: str) -> str:
    if AI_PROVIDER == "ollama":
        return await _ollama_generate(prompt)
    elif AI_PROVIDER == "openai":
        return await _openai_generate_single(prompt)
    else:
        raise HTTPException(500, f"Unknown AI_PROVIDER: {AI_PROVIDER}")

async def _ollama_generate(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{OLLLAMA_HOST}/api/generate",
            json={"model": AI_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        if resp.status_code != 200:
            raise HTTPException(500, f"Ollama generation failed: {resp.text}")
        data = resp.json()
        return data.get("response", "")
    except Exception as e:
        logger.exception("Error calling Ollama.")
        raise HTTPException(500, f"Ollama error: {str(e)}")

async def _openai_generate_single(prompt: str) -> str:
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.exception("Error calling OpenAI (single-turn).")
        raise HTTPException(500, f"OpenAI generation error: {str(e)}")

# -------------------------------------------------------------------
# Multi-turn approach for Orchestrator
# -------------------------------------------------------------------
async def call_ai_for_code_with_raw(
    conversation_messages: List[Dict[str, str]],
    system_messages: List[Dict[str, str]]
) -> (dict, List[str]):
    strict_instructions = f"""
You are an expert code generator.
Return valid JSON mapping filenames to file contents.
No code fences, no markdown, no extra text.

If you want to create a file, do it by returning e.g.:
{{
  "app.py": "...",
  "Dockerfile": "...",
  "requirements.txt": "..."
}}
No "create_file" blocks, no advanced JSON nesting.

Also, always remember:
1. If building a Python web server, pin Flask==2.2.3 and Werkzeug==2.2.3 to avoid import issues with url_quote.
2. The container must not exit if it's a server. For scripts, container should exit 0.
{DOCKER_TOOL_DOC}
"""

    final_messages = []
    final_messages.append({"role": "system", "content": strict_instructions})
    final_messages.extend(conversation_messages)
    final_messages.extend(system_messages)

    if AI_PROVIDER == "ollama":
        raw1 = await _ollama_generate_multiturn(final_messages)
    else:
        raw1 = await _openai_generate_multiturn(final_messages)

    code_dict_1 = _parse_json_safely(raw1)
    if code_dict_1:
        # Force normalization to "filename -> str" in case AI nested or used create_file
        code_dict_1 = _normalize_code_snippet(code_dict_1)
        if code_dict_1:
            return (code_dict_1, [raw1])

    # Attempt #2 if first fails or parse was empty
    fix_prompt_2 = f"""
You returned something that was not valid JSON mapping filenames to strings:
{raw1}

Please correct it to valid JSON. Example:
{{
  "Dockerfile": "...",
  "requirements.txt": "...",
  "app.py": "..."
}}
Nothing else. No code fences, no 'create_file', no extra keys.
"""
    attempt2 = list(final_messages) + [{"role": "user", "content": fix_prompt_2}]
    if AI_PROVIDER == "ollama":
        raw2 = await _ollama_generate_multiturn(attempt2)
    else:
        raw2 = await _openai_generate_multiturn(attempt2)

    code_dict_2 = _parse_json_safely(raw2)
    if code_dict_2:
        code_dict_2 = _normalize_code_snippet(code_dict_2)
        if code_dict_2:
            return (code_dict_2, [raw1, raw2])

    return ({}, [raw1, raw2])

async def _openai_generate_multiturn(messages: List[Dict[str, str]]) -> str:
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(model=AI_MODEL, messages=messages)
        return completion.choices[0].message.content
    except Exception as e:
        logger.exception("Error calling OpenAI (multi-turn).")
        raise HTTPException(500, f"OpenAI generation error: {str(e)}")

async def _ollama_generate_multiturn(messages: List[Dict[str, str]]) -> str:
    prompt_parts = []
    for m in messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            prompt_parts.append(f"System: {content}\n")
        elif role == "user":
            prompt_parts.append(f"User: {content}\n")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}\n")

    big_prompt = "\n".join(prompt_parts).strip()

    try:
        resp = requests.post(
            f"{OLLLAMA_HOST}/api/generate",
            json={"model": AI_MODEL, "prompt": big_prompt, "stream": False},
            timeout=60
        )
        if resp.status_code != 200:
            raise HTTPException(500, f"Ollama multi-turn generation failed: {resp.text}")
        data = resp.json()
        return data.get("response", "")
    except Exception as e:
        logger.exception("Error calling Ollama (multi-turn).")
        raise HTTPException(500, f"Ollama multi-turn error: {str(e)}")

# -------------------------------------------------------------------
# Normalization Helpers
# -------------------------------------------------------------------
def _normalize_code_snippet(parsed: dict) -> dict:
    """
    If the AI returned something like:
    {
      "name": "create_file",
      "arguments": {
        "filename": "app.py",
        "content": "..."
      }
    }
    We convert it to {"app.py": "..."}
    If it returned nested structures, we attempt to flatten them.
    We only keep "filename":"content" pairs that are strings.
    """
    # If top-level is "name":"create_file", convert it
    # Otherwise, keep as is, but ensure everything is str -> str
    if "name" in parsed and "arguments" in parsed:
        # e.g. { "name": "create_file", "arguments": { "filename": "app.py", "content": "..."} }
        args = parsed["arguments"]
        if "filename" in args and "content" in args:
            filename = args["filename"]
            content = args["content"]
            if isinstance(filename, str) and isinstance(content, str):
                return {filename: content}
            else:
                return {}
        else:
            return {}
    else:
        # Attempt to filter out any non-string keys or values
        final_dict = {}
        for k, v in parsed.items():
            if isinstance(k, str) and isinstance(v, str):
                final_dict[k] = v
        return final_dict if final_dict else {}

def _parse_json_safely(text: str) -> dict:
    text = _strip_code_fences(text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except json.JSONDecodeError:
        return {}

def _strip_code_fences(text: str) -> str:
    text = text.strip()
    # remove leading or trailing triple backticks
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
    text = re.sub(r'```$', '', text.strip())
    return text.strip()

# -------------------------------------------------------------------
# Known error pattern => recommended fix
# We specifically fix the "url_quote" problem by pinning Flask==2.2.3, Werkzeug==2.2.3
# -------------------------------------------------------------------
ERROR_PATTERNS = {
    r"cannot import name 'url_quote' from 'werkzeug.urls'": """
Your logs suggest a Flask/Werkzeug mismatch. Pin them as:
requirements.txt:
Flask==2.2.3
Werkzeug==2.2.3
"""
}

def diagnose_common_errors(log_text: str) -> str:
    for pattern, fix_text in ERROR_PATTERNS.items():
        if re.search(pattern, log_text, flags=re.IGNORECASE):
            return fix_text.strip()
    return ""

# -------------------------------------------------------------------
# fix_code_with_logs
# -------------------------------------------------------------------
async def fix_code_with_logs(deployment_id: str, conversation_id: str, raw_logs: str):
    from app.api.orchestrator import append_log, update_deployment_field

    lines = raw_logs.splitlines()
    # let's keep up to 300 lines
    highlights = []
    for i, line in enumerate(lines[:300], start=1):
        if ("traceback" in line.lower() or 
            "error" in line.lower() or 
            "syntaxerror" in line.lower()):
            highlights.append(f"[ERROR] {line}")
        else:
            highlights.append(line)

    snippet = "\n".join(highlights)

    known_fixes = diagnose_common_errors(raw_logs)
    extra_hint = ""
    if known_fixes:
        extra_hint = f"\nAdditionally, here is a hint:\n{known_fixes}\n"

    system_msg_for_logs = {
        "role": "system",
        "content": f"""
We encountered errors while building/running the code.
Here are up to 300 lines of logs (with highlights):
{snippet}

Please fix these issues and return a COMPLETE codebase in valid JSON, 
mapping filenames to file contents. No extra text or code fences.
{extra_hint}
"""
    }

    convo_obj = await db["conversations"].find_one({"_id": ObjectId(conversation_id)})
    if not convo_obj:
        await append_log(deployment_id, f"Could not find conversation {conversation_id} for fix_code_with_logs!")
        await update_deployment_field(deployment_id, {"status": "error"})
        return False

    conversation_messages = convo_obj.get("messages", [])

    code_dict, raw_attempts = await call_ai_for_code_with_raw(
        conversation_messages=conversation_messages,
        system_messages=[system_msg_for_logs]
    )
    if not code_dict:
        for i, txt in enumerate(raw_attempts, start=1):
            await append_log(deployment_id, f"Raw AI fix attempt #{i}:\n{txt}")
        await append_log(deployment_id, "AI did not fix the error. Aborting.")
        await update_deployment_field(deployment_id, {"status": "error"})
        return False

    # code_dict is guaranteed to be str->str after normalization
    import json
    code_text = json.dumps(code_dict, indent=2)
    await add_message_to_conversation_internal(
        conversation_id,
        {"role": "assistant", "content": code_text}
    )

    await append_log(deployment_id, "AI returned a code fix. Will try again next iteration.")
    return True
