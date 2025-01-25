import logging
import requests
import openai
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.config import AI_PROVIDER, OLLLAMA_HOST, OPENAI_API_KEY
from app.core.security import require_role

logger = logging.getLogger(__name__)
router = APIRouter()

class CodeGenRequest(BaseModel):
    conversation_id: str
    prompt: str

@router.post("/generate")
async def generate_code(req: CodeGenRequest, user=Depends(require_role("user"))):
    logger.info("Received code generation request.")
    logger.debug(f"Prompt: {req.prompt}, Provider: {AI_PROVIDER}")

    generated_text = await _generate_text(req.prompt)
    logger.info("Code generation successful, returning generated_text.")
    return {"generated_code": generated_text}


async def _generate_text(prompt: str) -> str:
    """
    Internal helper to call either Ollama or OpenAI for a textual completion.
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
                "model": "hhao/qwen2.5-coder-tools:latest",  # Example default
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


# =====================
# NEW: call_ai_for_code
# =====================
async def call_ai_for_code(conversation_id: str, system_message: str = None) -> dict:
    """
    Retrieve a *full codebase* in dictionary form, e.g.:
    {
      "Dockerfile": "...contents...",
      "requirements.txt": "...contents...",
      "app/main.py": "...contents..."
    }
    If system_message is provided, we treat that as context (e.g. "Fix the code using these logs").
    This is where you'd carefully engineer your prompts for "Give me a comprehensive set of files."
    """
    try:
        base_prompt = f"You are an expert code generator. Return a JSON object mapping filenames to file contents for a complete application. No additional explanation."
        if system_message:
            base_prompt += f"\nSystem instructions:\n{system_message}"

        # For simplicity, just call the same model and parse JSON from the result.
        # In reality, you'd want robust error handling for invalid JSON, etc.
        raw_text = await _generate_text(base_prompt)

        # Basic parse: attempt to parse the raw_text as JSON.
        import json
        code_dict = {}
        try:
            code_dict = json.loads(raw_text)
        except json.JSONDecodeError:
            logger.warning("AI response was not valid JSON. Returning empty dict.")
            code_dict = {}

        # Ensure it's a dict of {filename: content}
        if not isinstance(code_dict, dict):
            code_dict = {}

        return code_dict

    except Exception as e:
        logger.exception("Error in call_ai_for_code")
        return {}
