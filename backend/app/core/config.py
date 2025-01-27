# File: backend/app/core/config.py

import os
from dotenv import load_dotenv

load_dotenv()  # If using a .env file

# ------------------
# Database settings
# ------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "app_generator")

# ------------------
# AI provider settings
# ------------------
AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()  # "ollama" or "openai"
# Example: "gpt-4", "gpt-3.5-turbo", or your custom name "gpt-4o"
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")

# Ollama
OLLLAMA_HOST = os.getenv("OLLLAMA_HOST", "http://10.60.4.77:11434")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# For example, if you want to try GPT-4:
# AI_PROVIDER=openai
# AI_MODEL=gpt-4
# OPENAI_API_KEY=<your key>

# ------------------
# JWT Auth
# ------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = "HS256"

# ------------------
# Dev Mode
# ------------------
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
