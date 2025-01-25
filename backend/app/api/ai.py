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

    if AI_PROVIDER == "ollama":
        try:
            # We'll do a non-stream request, so we can parse "response" in one shot.
            resp = requests.post(
                f"{OLLLAMA_HOST}/api/generate",
                json={
                    "model": "hhao/qwen2.5-coder-tools:latest",          # or any valid model name
                    "prompt": req.prompt,
                    "stream": False,             # single JSON object returned
                    # "options": {"num_ctx": 64000}  # optional advanced param if needed
                },
                timeout=30
            )
            logger.debug(f"Ollama response status: {resp.status_code}")
            logger.debug(f"Ollama response body: {resp.text}")

            if resp.status_code != 200:
                raise HTTPException(500, f"Ollama generation failed: {resp.text}")

            data = resp.json()
            generated_text = data.get("response", "")
        except Exception as e:
            logger.exception("Error calling Ollama.")
            raise HTTPException(500, f"Ollama error: {str(e)}")

    else:  # "openai"
        openai.api_key = OPENAI_API_KEY
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": req.prompt}]
            )
            logger.debug(f"OpenAI completion: {completion}")
            generated_text = completion.choices[0].message.content
        except Exception as e:
            logger.exception("Error calling OpenAI.")
            raise HTTPException(500, f"OpenAI generation error: {str(e)}")

    logger.info("Code generation successful, returning generated_text.")
    return {"generated_code": generated_text}
