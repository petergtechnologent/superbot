from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_pass: str, hashed_pass: str) -> bool:
    return pwd_context.verify(plain_pass, hashed_pass)

def create_jwt_token(data: dict, expires_delta: int = 3600):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload if payload.get("exp") >= datetime.utcnow().timestamp() else None
    except:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return payload

def require_role(role: str):
    def role_decorator(user=Depends(get_current_user)):
        if user.get("role") != role:
            if role == "admin" and user.get("role") != "admin":
                raise HTTPException(status_code=403, detail="Forbidden")
            elif role == "user" and user.get("role") not in ("user", "admin"):
                raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return role_decorator
