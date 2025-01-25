from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str  # "admin" or "user"

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    hashed_password: str
    id: str
