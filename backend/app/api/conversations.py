# File: backend/app/api/conversations.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime
from bson import ObjectId
from app.core.database import db
from app.core.security import require_role

router = APIRouter()

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ConversationCreate(BaseModel):
    messages: List[Message]

async def add_message_to_conversation_internal(conv_id: str, new_message: dict):
    """
    INTERNAL HELPER:
      Appends a message to the conversation doc in Mongo,
      converting conv_id from str -> ObjectId for the query.
    """
    await db["conversations"].update_one(
        {"_id": ObjectId(conv_id)},
        {
            "$push": {"messages": new_message},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )

@router.post("/")
async def create_conversation(payload: ConversationCreate, user=Depends(require_role("user"))):
    """
    Create a NEW conversation doc with the given messages (usually 1 message from user).
    Returns: {"conversation_id": "..."} as a string.
    """
    conv_doc = {
        "user_id": user["user_id"],
        "messages": [m.dict() for m in payload.messages],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    result = await db["conversations"].insert_one(conv_doc)
    return {"conversation_id": str(result.inserted_id)}

@router.patch("/{conv_id}/append-message")
async def append_message_to_conversation(
    conv_id: str,
    message: Message,
    user=Depends(require_role("user"))
):
    """
    An API route to append a message. Typically not used by the orchestrator;
    the orchestrator calls add_message_to_conversation_internal directly.
    """
    conv_obj = await db["conversations"].find_one({"_id": ObjectId(conv_id)})
    if not conv_obj:
        raise HTTPException(404, "Conversation not found")

    # If not admin, ensure it belongs to the requesting user
    if user["role"] != "admin" and conv_obj.get("user_id") != user["user_id"]:
        raise HTTPException(403, "Forbidden")

    await add_message_to_conversation_internal(conv_id, message.dict())
    return {"status": "ok", "message": "Message appended."}

@router.get("/")
async def list_conversations(user=Depends(require_role("user"))):
    """
    Return all conversations for this user (or all if user is admin).
    """
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
    """
    Return a single conversation doc by ID.
    """
    conversation = await db["conversations"].find_one({"_id": ObjectId(conv_id)})
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    if user["role"] != "admin" and conversation.get("user_id") != user["user_id"]:
        raise HTTPException(403, "Forbidden")
    conversation["_id"] = str(conversation["_id"])
    return conversation
