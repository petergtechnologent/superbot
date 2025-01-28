# File: backend/app/core/prompt_manager.py

import re
import json
import logging
import requests

from app.core.config import AI_PROVIDER, OPENAI_API_KEY, AI_MODEL, OLLLAMA_HOST

logger = logging.getLogger(__name__)

# -------------------
# Prompt Templates
# -------------------
PROMPT_TEMPLATES = {
    "flex_spec": """You are an assistant that converts plain English microservice requests
into a structured JSON specification for a "Flex Spec."
Output only valid JSON with keys:
- service_name (string)
- port (number)
- endpoints (list of objects with 'path', 'method', 'description')

No extra text or code fences.
""",
    "code_generation": """
You are a code generator for Dockerized FastAPI apps.
Always ensure the Dockerfile includes:
  WORKDIR /app
  COPY . /app
  RUN pip install -r requirements.txt
  CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]

Return a strictly valid JSON dictionary mapping filenames -> file contents. 
For example:
{{
  "Dockerfile": "...",
  "requirements.txt": "...",
  "main.py": "..."
}}
No code fences, no extra disclaimers.
""",
    "fixing_code": """
You are an AI code fixer. We encountered errors when building/running the container.
Please return a strictly valid JSON dictionary (filename->content) with corrected code.
No extra disclaimers or code fences.
"""
}

# -------------------
# Prompt Builders
# -------------------
def build_flex_spec_prompt(user_text: str) -> str:
    """
    Return the system prompt for turning user text into a Flex Spec.
    """
    base = PROMPT_TEMPLATES["flex_spec"]
    final_prompt = f"{base}\nUser said: \"{user_text}\""
    return final_prompt

def build_code_generation_prompt(
    conversation_messages,
    user_prompt=None,
    port: int = 9000
) -> str:
    """
    Merges the conversation messages with a code generation system prompt
    that uses the specified port in the Docker instructions.
    """
    # Format the code_generation template with the port
    system_instructions = PROMPT_TEMPLATES["code_generation"].format(port=port)

    prompt_parts = []
    # Add top-level system instructions
    prompt_parts.append(f"System: {system_instructions.strip()}\n")

    # Add conversation history
    for m in conversation_messages:
        role = m["role"]
        content = m["content"]
        if role == "system":
            prompt_parts.append(f"System: {content}\n")
        elif role == "user":
            prompt_parts.append(f"User: {content}\n")
        elif role == "assistant":
            prompt_parts.append(f"Assistant: {content}\n")

    # Optionally add a final user prompt
    if user_prompt:
        prompt_parts.append(f"User: {user_prompt}\n")

    return "\n".join(prompt_parts).strip()

def build_fix_prompt(log_excerpt: str, known_fixes: str = "") -> str:
    """
    Build a prompt for requesting code fixes based on logs.
    """
    base = PROMPT_TEMPLATES["fixing_code"]
    if known_fixes:
        base += f"\nAdditionally, here's a known fix:\n{known_fixes}\n"
    final_prompt = f"{base}\nLogs:\n{log_excerpt}"
    return final_prompt.strip()

# -------------------
# JSON Parsing Helpers
# -------------------
def parse_json_safely(text: str) -> dict:
    text = strip_code_fences(text.strip())
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {}
    except json.JSONDecodeError:
        return {}

def strip_code_fences(text: str) -> str:
    # Remove triple backticks
    text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
    text = re.sub(r'```$', '', text.strip())
    return text.strip()

def normalize_code_snippet(parsed: dict) -> dict:
    """
    Enforce a dictionary {filename -> content} structure.
    """
    if not isinstance(parsed, dict):
        return {}

    # Handle function-call style outputs
    if "name" in parsed and "arguments" in parsed:
        args = parsed["arguments"]
        if "filename" in args and "content" in args:
            filename = args["filename"]
            content = args["content"]
            if isinstance(filename, str) and isinstance(content, str):
                return {filename: content}
        return {}

    # Otherwise, ensure all keys/values are string
    final_dict = {}
    for k, v in parsed.items():
        if isinstance(k, str) and isinstance(v, str):
            final_dict[k] = v
    return final_dict

# -------------------
# AI Provider Abstraction
# -------------------
async def ollama_generate(prompt: str) -> str:
    """
    Call Ollama server with the given prompt.
    """
    try:
        resp = requests.post(
            f"{OLLLAMA_HOST}/api/generate",
            json={"model": AI_MODEL, "prompt": prompt, "stream": False},
            timeout=60
        )
        if resp.status_code != 200:
            logger.error(f"Ollama call failed: {resp.status_code} {resp.text}")
            return ""
        data = resp.json()
        return data.get("response", "")
    except Exception as e:
        logger.exception("Error calling Ollama")
        return ""

async def openai_generate(prompt: str) -> str:
    """
    Call OpenAI with the given prompt.
    """
    import openai
    openai.api_key = OPENAI_API_KEY
    try:
        completion = openai.ChatCompletion.create(
            model=AI_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.exception("Error calling OpenAI")
        return ""

async def generate_text_from_prompt(prompt: str) -> str:
    """
    Decide which provider to call, returning raw text from the model.
    """
    if AI_PROVIDER == "ollama":
        return await ollama_generate(prompt)
    else:
        return await openai_generate(prompt)

# -------------------
# Code Generation (Multi-Attempt)
# -------------------
async def call_ai_for_code(
    conversation_messages,
    user_prompt=None,
    port=9000
) -> (dict, list):
    """
    1) Build the code generation prompt from conversation + user_prompt + port
    2) Attempt #1 parse
    3) If invalid, Attempt #2 fix
    Returns (code_dict, [raw1, raw2]) or ( {}, [raw1, raw2] )
    """
    # First attempt
    final_prompt_1 = build_code_generation_prompt(
        conversation_messages,
        user_prompt=user_prompt,
        port=port
    )
    raw1 = await generate_text_from_prompt(final_prompt_1)
    code_dict_1 = normalize_code_snippet(parse_json_safely(raw1))
    if code_dict_1:
        return (code_dict_1, [raw1])

    # Second attempt (try to fix)
    fix_prompt = f"""
You returned invalid JSON or non-filemap. Original:
{raw1}

Please strictly return valid JSON:
{{
  "Dockerfile": "...",
  "requirements.txt": "...",
  "main.py": "..."
}}
No code fences or other text.
"""
    final_prompt_2 = build_code_generation_prompt(
        conversation_messages,
        user_prompt=fix_prompt,
        port=port
    )
    raw2 = await generate_text_from_prompt(final_prompt_2)
    code_dict_2 = normalize_code_snippet(parse_json_safely(raw2))
    if code_dict_2:
        return (code_dict_2, [raw1, raw2])

    return ({}, [raw1, raw2])
