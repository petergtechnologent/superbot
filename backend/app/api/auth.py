# File: backend/app/api/auth.py

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.security import hash_password, verify_password, create_jwt_token
from app.core.database import db
from app.models.user import UserInDB

logger = logging.getLogger(__name__)
router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    """
    Simple local login for an existing user record in the DB.
    """
    user_doc = await db["users"].find_one({"email": request.email})
    if not user_doc:
        logger.debug("No user found with email: %s", request.email)
        raise HTTPException(status_code=400, detail="Invalid credentials")

    user = UserInDB(**user_doc, id=str(user_doc["_id"]))
    if not verify_password(request.password, user.hashed_password):
        logger.debug("Password mismatch for user: %s", request.email)
        raise HTTPException(status_code=400, detail="Invalid credentials")

    token = create_jwt_token({
        "user_id": user.id,
        "role": user.role,
        "email": user.email
    })
    logger.info("User %s logged in successfully", request.email)
    return {"access_token": token, "token_type": "bearer"}
