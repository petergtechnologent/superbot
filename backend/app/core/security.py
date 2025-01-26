import logging
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.core.config import JWT_SECRET_KEY, JWT_ALGORITHM
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

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
    logger.debug(f"[decode_jwt_token] Attempting to decode token: {token}")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        exp = payload.get("exp")
        if exp is None or exp < datetime.utcnow().timestamp():
            logger.debug("[decode_jwt_token] Token is expired or missing exp.")
            return None
        logger.debug(f"[decode_jwt_token] Successfully decoded token payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("[decode_jwt_token] Token signature has expired.")
        return None
    except jwt.DecodeError:
        logger.debug("[decode_jwt_token] Token decode error. Invalid signature.")
        return None
    except Exception as e:
        logger.exception("[decode_jwt_token] Unexpected error decoding token.")
        return None


async def get_current_user(token: str = Depends(oauth2_scheme)):
    logger.debug(f"[get_current_user] Received token via OAuth2: {token}")
    payload = decode_jwt_token(token)
    if not payload:
        logger.debug("[get_current_user] Payload is null => invalid or expired token.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    logger.debug(f"[get_current_user] Decoded user payload: {payload}")
    return payload


def require_role(role: str):
    def role_decorator(user=Depends(get_current_user)):
        user_role = user.get("role")
        logger.debug(f"[require_role] Required: {role}, user has role: {user_role}")

        if role == "admin" and user_role != "admin":
            raise HTTPException(status_code=403, detail="Forbidden")
        elif role == "user" and user_role not in ("user", "admin"):
            # If we specifically need role="user", an admin is also accepted. If your logic differs, adjust here.
            raise HTTPException(status_code=403, detail="Forbidden")

        return user
    return role_decorator
