import motor.motor_asyncio
from app.core.config import MONGO_URI, DATABASE_NAME

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[DATABASE_NAME]
