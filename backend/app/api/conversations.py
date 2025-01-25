from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime
from bson import ObjectId
from app.core.database import db
from app.core.security import require_role

router = APIRouter()

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ConversationCreate(BaseModel):
    messages: List[Message]

@router.post("/")
async def create_conversation(payload: ConversationCreate, user=Depends(require_role("user"))):
    conv_doc = {
        "user_id": user["user_id"],
        "messages": [m.dict() for m in payload.messages],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = await db["conversations"].insert_one(conv_doc)
    return {"conversation_id": str(result.inserted_id)}

@router.get("/")
async def list_conversations(user=Depends(require_role("user"))):
    # Return all conversations for this user (or admin sees all)
    query = {}
    if user["role"] != "admin":
        query["user_id"] = user["user_id"]
    cursor = db["conversations"].find(query).sort("created_at", -1)
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results

@router.get("/{conv_id}")
async def get_conversation(conv_id: str, user=Depends(require_role("user"))):
    conversation = await db["conversations"].find_one({"_id": ObjectId(conv_id)})
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    if user["role"] != "admin" and conversation.get("user_id") != user["user_id"]:
        raise HTTPException(403, "Forbidden")
    conversation["_id"] = str(conversation["_id"])
    return conversation
