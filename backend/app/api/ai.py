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

# ------------------------------------------
# 1) Transform user text -> Flex Spec
# ------------------------------------------
class TransformSpecRequest(BaseModel):
    userIdea: str

@router.post("/transform_flex_spec")
async def transform_flex_spec(request: TransformSpecRequest, user=Depends(require_role("user"))):
    """
    Takes a freeform user idea (request.userIdea) and uses the LLM 
    to produce a structured Flex Spec with keys like:
    {
      "service_name": "...",
      "port": 9000,
      "endpoints": [
        {"path": "/...", "method": "GET", "description": "..."}
      ]
    }

    We then ensure there's a root GET '/' endpoint for health checks.
    """
    user_text = request.userIdea.strip()
    if not user_text:
        raise HTTPException(400, "Empty user idea.")

    system_prompt = f"""
You are an assistant that converts plain English microservice requests 
into a structured JSON specification for a "Flex Spec." 
Output only valid JSON with keys:
- service_name (string)
- port (number)
- endpoints (list of objects with 'path', 'method', 'description')

No extra text or code fences.

User said: "{user_text}"
Example minimal output:
{{
  "service_name": "my-service",
  "port": 9000,
  "endpoints": [
    {{
      "path": "/items",
      "method": "GET",
      "description": "Retrieve items"
    }}
  ]
}}
"""

    try:
        if AI_PROVIDER == "ollama":
            resp_text = await _ollama_generate_multiturn([
                {"role": "system", "content": system_prompt}
            ])
        else:
            resp_text = await _openai_generate_multiturn([
                {"role": "system", "content": system_prompt}
            ])
    except Exception as e:
        logger.exception("Error calling AI for transform_flex_spec.")
        raise HTTPException(500, f"AI error: {str(e)}")

    spec_dict = _parse_json_safely(resp_text)
    if not spec_dict:
        raise HTTPException(
            400,
            f"Could not parse a valid Flex Spec from AI response:\n{resp_text}"
        )

    # Make sure there's an endpoints list
    if "endpoints" not in spec_dict or not isinstance(spec_dict["endpoints"], list):
        spec_dict["endpoints"] = []

    # Check if there's already a root path '/'
    has_root = any(
        ep.get("path") == "/" for ep in spec_dict["endpoints"]
    )
    if not has_root:
        spec_dict["endpoints"].append({
            "path": "/",
            "method": "GET",
            "description": "Health/status endpoint returning { 'status': 'ok' }"
        })

    return spec_dict

# ------------------------------------------
# 2) Multi-turn Code Generation Endpoint
# ------------------------------------------
class CodeGenRequest(BaseModel):
    conversation_id: str
    prompt: str

@router.post("/generate")
async def generate_code(req: CodeGenRequest, user=Depends(require_role("user"))):
    """
    Multi-turn code generation route.
    It loads the conversation (which should include the Flex Spec),
    merges it with a final user prompt, and returns Dockerized FastAPI code.
    """
    logger.info("Received code generation request (multi-turn).")
    logger.debug(f"Provider={AI_PROVIDER}, Model={AI_MODEL}, conversation_id={req.conversation_id}")

    # 1) Load conversation from DB
    convo = await db["conversations"].find_one({"_id": ObjectId(req.conversation_id)})
    if not convo:
        raise HTTPException(404, "Conversation not found; cannot generate code.")

    conversation_messages = convo.get("messages", [])

    # 2) We'll add a 'system' message instructing the model to produce code with a root route
    system_msg = {
        "role": "system",
        "content": """
You are a code generator. The user's conversation above includes a Flex spec.
Produce a Dockerized FastAPI service. The spec always has a root path '/' 
for a health/status endpoint returning {"status":"ok"}.

Output code in JSON format, e.g.:
{
  "Dockerfile": "...",
  "requirements.txt": "...",
  "main.py": "...",
  ...
}
No code fences or extra text.
"""
    }

    # 3) We'll treat your final prompt as a "user" message
    final_user_msg = {"role": "user", "content": req.prompt}

    # 4) Merge it all and do a multi-turn parse
    code_dict, raw_attempts = await call_ai_for_code_with_raw(
        conversation_messages=conversation_messages,
        system_messages=[system_msg, final_user_msg]
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

# ------------------------------------------
# 3) Functions used by Orchestrator
# ------------------------------------------
async def call_ai_for_plan(conversation_messages, system_prompt: str) -> str:
    final_messages = [{"role": "system", "content": system_prompt}]
    final_messages.extend(conversation_messages)

    if AI_PROVIDER == "ollama":
        raw_plan = await _ollama_generate_multiturn(final_messages)
    else:
        raw_plan = await _openai_generate_multiturn(final_messages)

    return raw_plan.strip()


async def call_ai_for_code_with_raw(
    conversation_messages: List[Dict[str, str]],
    system_messages: List[Dict[str, str]]
) -> (dict, List[str]):
    final_messages = []
    final_messages.extend(conversation_messages)
    final_messages.extend(system_messages)

    # Attempt #1
    if AI_PROVIDER == "ollama":
        raw1 = await _ollama_generate_multiturn(final_messages)
    else:
        raw1 = await _openai_generate_multiturn(final_messages)

    code_dict_1 = _parse_json_safely(raw1)
    code_dict_1 = _normalize_code_snippet(code_dict_1)
    if code_dict_1:
        return (code_dict_1, [raw1])

    # Attempt #2
    fix_prompt = f"""
You returned invalid JSON for file mappings. Original:
{raw1}

Please strictly return valid JSON:
{{
  "Dockerfile": "...",
  "requirements.txt": "...",
  "main.py": "..."
}}
No code fences or other text.
"""
    attempt2 = list(final_messages) + [{"role": "user", "content": fix_prompt}]
    if AI_PROVIDER == "ollama":
        raw2 = await _ollama_generate_multiturn(attempt2)
    else:
        raw2 = await _openai_generate_multiturn(attempt2)

    code_dict_2 = _parse_json_safely(raw2)
    code_dict_2 = _normalize_code_snippet(code_dict_2)
    if code_dict_2:
        return (code_dict_2, [raw1, raw2])

    return ({}, [raw1, raw2])

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
    extra_hint = ""
    if known_fixes:
        extra_hint = f"\nAdditionally, here's a known fix:\n{known_fixes}\n"

    system_msg_for_logs = {
        "role": "system",
        "content": f"""
We encountered errors while building/running the container.
Here are up to 300 lines of logs:
{snippet}

Please fix these issues and return COMPLETE code in valid JSON 
(filename->content). No code fences.
{extra_hint}
"""
    }

    convo_obj = await db["conversations"].find_one({"_id": ObjectId(conversation_id)})
    if not convo_obj:
        await append_log(deployment_id, "Conversation not found; cannot fix code.")
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

    import json
    code_text = json.dumps(code_dict, indent=2)
    await add_message_to_conversation_internal(
        conversation_id,
        {"role": "assistant", "content": code_text}
    )

    await append_log(deployment_id, "AI returned a code fix. Will try again next iteration.")
    return True

# ------------------------------------------
# 4) Helper functions
# ------------------------------------------
ERROR_PATTERNS = {
    r"cannot import name 'url_quote' from 'werkzeug.urls'": """
Your logs suggest a Flask/Werkzeug mismatch. 
Pin them as:
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

def _normalize_code_snippet(parsed: dict) -> dict:
    if not isinstance(parsed, dict):
        return {}

    if "name" in parsed and "arguments" in parsed:
        args = parsed["arguments"]
        if "filename" in args and "content" in args:
            filename = args["filename"]
            content = args["content"]
            if isinstance(filename, str) and isinstance(content, str):
                return {filename: content}
        return {}

    final_dict = {}
    for k, v in parsed.items():
        if isinstance(k, str) and isinstance(v, str):
            final_dict[k] = v
    return final_dict

def _parse_json_safely(text: str) -> dict:
    text = _strip_code_fences(text.strip())
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except json.JSONDecodeError:
        return {}

def _strip_code_fences(text: str) -> str:
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
    text = re.sub(r'```$', '', text.strip())
    return text.strip()

# ------------------------------------------
# 5) Internal calls to Ollama/OpenAI
# ------------------------------------------
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
        logger.exception("Error calling Ollama (single-turn).")
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

async def _openai_generate_multiturn(messages: List[Dict[str, str]]) -> str:
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(model=AI_MODEL, messages=messages)
        return completion.choices[0].message.content
    except Exception as e:
        logger.exception("Error calling OpenAI (multi-turn).")
        raise HTTPException(500, f"OpenAI generation error: {str(e)}")
