import logging
import requests
import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import json
import re  # <--- for regex to strip fences

from app.core.config import AI_PROVIDER, OLLLAMA_HOST, OPENAI_API_KEY
from app.core.security import require_role

logger = logging.getLogger(__name__)
router = APIRouter()

class CodeGenRequest(BaseModel):
    conversation_id: str
    prompt: str

@router.post("/generate")
async def generate_code(req: CodeGenRequest, user=Depends(require_role("user"))):
    """
    Endpoint for single snippet generation (not the full code orchestrator approach).
    """
    logger.info("Received code generation request.")
    logger.debug(f"Prompt: {req.prompt}, Provider: {AI_PROVIDER}")

    generated_text = await _generate_text(req.prompt)
    logger.info("Code generation successful, returning generated_text.")
    return {"generated_code": generated_text}

# -------------------------------------------------------------------
# Internal helper to generate text from either Ollama or OpenAI
# -------------------------------------------------------------------
async def _generate_text(prompt: str) -> str:
    """
    Calls Ollama or OpenAI to get a textual completion.
    """
    if AI_PROVIDER == "ollama":
        return await _ollama_generate(prompt)
    else:
        return await _openai_generate(prompt)

async def _ollama_generate(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{OLLLAMA_HOST}/api/generate",
            json={
                "model": "hhao/qwen2.5-coder-tools:latest",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        if resp.status_code != 200:
            raise HTTPException(500, f"Ollama generation failed: {resp.text}")
        data = resp.json()
        return data.get("response", "")
    except Exception as e:
        logger.exception("Error calling Ollama.")
        raise HTTPException(500, f"Ollama error: {str(e)}")

async def _openai_generate(prompt: str) -> str:
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.exception("Error calling OpenAI.")
        raise HTTPException(500, f"OpenAI generation error: {str(e)}")

# -------------------------------------------------------------------
# Two-attempt approach:
# call_ai_for_code_with_raw returns (code_dict, [raw_text_1, raw_text_2])
# -------------------------------------------------------------------
async def call_ai_for_code_with_raw(conversation_id: str, system_message: str = None) -> tuple[dict, list[str]]:
    """
    1) Attempt #1: strict instructions to return valid JSON for a complete codebase.
    2) Attempt #2: if #1 fails, feed the invalid text back to the AI 
       and ask it to correct it to valid JSON.

    Returns (code_dict, [raw_text_1, raw_text_2]).
    If both fail, code_dict = {}.
    """
    strict_instructions = """
You are an expert code generator.
Return a valid JSON object that maps filenames to file contents for a complete application.
No code fences, no markdown, no extra text.

Example of the format:
{
  "Dockerfile": "...",
  "requirements.txt": "...",
  "app/main.py": "...",
  "frontend/pages/index.js": "...",
  "frontend/package.json": "...",
  ...
}

Include as many files as necessary. If you have incomplete info, make a best guess.
"""
    if system_message:
        combined_prompt = f"{strict_instructions}\nAdditional instructions:\n{system_message}"
    else:
        combined_prompt = strict_instructions

    # ----- Attempt #1 -----
    raw1 = await _generate_text(combined_prompt)
    logger.debug(f"[call_ai_for_code_with_raw] Attempt #1 raw AI text:\n{raw1}")
    code_dict_1 = _parse_json_safely(raw1)
    if code_dict_1:
        return code_dict_1, [raw1]

    # ----- Attempt #2 -----
    fix_prompt_2 = f"""
You returned invalid JSON previously. Here is what you gave:

{raw1}

Please correct it to valid JSON that maps filenames to file contents.
No extra text, no code fences.
Example:
{{
  "Dockerfile": "...",
  "app/main.py": "...",
  ...
}}
"""
    raw2 = await _generate_text(fix_prompt_2)
    logger.debug(f"[call_ai_for_code_with_raw] Attempt #2 raw AI text:\n{raw2}")
    code_dict_2 = _parse_json_safely(raw2)
    if code_dict_2:
        return code_dict_2, [raw1, raw2]

    # If both attempts failed, return empty
    return {}, [raw1, raw2]

# ---------------------
# NEW CODE: Strip code fences
# ---------------------
def _strip_code_fences(text: str) -> str:
    """
    Remove ```json ...``` or ``` ...``` fences from the AI output.
    We'll strip any leading/trailing triple backticks or code fence lines.
    """

    # 1. Trim whitespace
    stripped = text.strip()

    # 2. If it starts with ``` or ```json, remove that line
    #    Use regex to remove lines like ```json or ``` or ```` or maybe ```lang
    stripped = re.sub(r'^```[a-zA-Z]*\n?', '', stripped)  # remove ```json or ```py, etc. at start
    # If there's a trailing ```
    stripped = re.sub(r'```$', '', stripped.strip())

    # Alternatively, we can remove anything from the first ``` to the matching ```
    # But let's do a simpler approach for now.

    return stripped.strip()

def _parse_json_safely(text: str) -> dict:
    """
    Attempts to parse text as JSON. Returns {} if it fails.
    We first remove any code fences, then json.loads the remainder.
    """
    # Remove code fences
    cleaned = _strip_code_fences(text)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except json.JSONDecodeError:
        return {}