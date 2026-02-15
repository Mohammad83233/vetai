"""
User and authentication models.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system."""
    ADMIN = "admin"
    DOCTOR = "doctor"
    STAFF = "staff"


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.STAFF


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """User login model."""
    email: EmailStr
    password: str


class User(UserBase):
    """User response model (no password)."""
    id: str = Field(..., alias="_id")
    is_active: bool = True
    created_at: datetime
    
    class Config:
        populate_by_name = True


class UserInDB(UserBase):
    """User model as stored in database."""
    id: Optional[str] = Field(None, alias="_id")
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    user: User


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
