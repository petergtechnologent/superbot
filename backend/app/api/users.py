from fastapi import APIRouter, HTTPException, Depends
from app.core.security import hash_password, require_role
from app.core.database import db
from app.models.user import UserCreate, UserInDB

router = APIRouter()

@router.post("/", dependencies=[Depends(require_role("admin"))])
async def create_user(user: UserCreate):
    existing = await db["users"].find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    hashed_pass = hash_password(user.password)
    new_user = {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "hashed_password": hashed_pass
    }
    result = await db["users"].insert_one(new_user)
    return {"id": str(result.inserted_id), "email": user.email}

@router.get("/me")
async def get_current_user(user=Depends(require_role("user"))):
    return {"user_id": user["user_id"], "email": user["email"], "role": user["role"]}
