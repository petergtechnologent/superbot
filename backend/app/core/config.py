import os
from dotenv import load_dotenv

load_dotenv()  # If using a .env file

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "app_generator")

AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")  # or "openai"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLLAMA_HOST = os.getenv("OLLLAMA_HOST", "http://10.60.4.77:11434")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "15"))

# JWT Settings (for local auth)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = "HS256"

# Rate limiting settings (if used in the future)
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "3600"))  # in seconds
