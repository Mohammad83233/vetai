"""
Authentication service with JWT token management.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from bson import ObjectId

from ..config import get_settings
from ..database import Database
from ..models.user import UserCreate, UserInDB, User, Token, TokenData, UserRole

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication and user management service."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            role: str = payload.get("role")
            if user_id is None:
                return None
            return TokenData(user_id=user_id, email=email, role=UserRole(role))
        except JWTError:
            return None
    
    @classmethod
    async def get_user_by_email(cls, email: str) -> Optional[dict]:
        """Get user by email from database."""
        users = Database.get_collection("users")
        user = await users.find_one({"email": email.lower()})
        return user
    
    @classmethod
    async def get_user_by_id(cls, user_id: str) -> Optional[dict]:
        """Get user by ID from database."""
        users = Database.get_collection("users")
        user = await users.find_one({"_id": ObjectId(user_id)})
        if user:
            user["_id"] = str(user["_id"])
        return user
    
    @classmethod
    async def create_user(cls, user_data: UserCreate) -> User:
        """Create a new user."""
        users = Database.get_collection("users")
        
        # Check if user exists
        existing = await cls.get_user_by_email(user_data.email)
        if existing:
            raise ValueError("User with this email already exists")
        
        # Create user document
        user_doc = {
            "email": user_data.email.lower(),
            "full_name": user_data.full_name,
            "role": user_data.role.value,
            "hashed_password": cls.get_password_hash(user_data.password),
            "is_active": True,
            "created_at": datetime.utcnow()
        }
        
        result = await users.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        
        return User(
            _id=user_doc["_id"],
            email=user_doc["email"],
            full_name=user_doc["full_name"],
            role=UserRole(user_doc["role"]),
            is_active=user_doc["is_active"],
            created_at=user_doc["created_at"]
        )
    
    @classmethod
    async def authenticate_user(cls, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await cls.get_user_by_email(email)
        if not user:
            return None
        if not cls.verify_password(password, user["hashed_password"]):
            return None
        
        return User(
            _id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=UserRole(user["role"]),
            is_active=user.get("is_active", True),
            created_at=user["created_at"]
        )
    
    @classmethod
    async def login(cls, email: str, password: str) -> Optional[Token]:
        """Login user and return access token."""
        user = await cls.authenticate_user(email, password)
        if not user:
            return None
        
        access_token = cls.create_access_token(
            data={
                "sub": user.id,
                "email": user.email,
                "role": user.role.value
            }
        )
        
        return Token(access_token=access_token, user=user)
    
    @classmethod
    async def get_current_user(cls, token: str) -> Optional[User]:
        """Get current user from token."""
        token_data = cls.decode_token(token)
        if not token_data:
            return None
        
        user = await cls.get_user_by_id(token_data.user_id)
        if not user:
            return None
        
        return User(
            _id=user["_id"],
            email=user["email"],
            full_name=user["full_name"],
            role=UserRole(user["role"]),
            is_active=user.get("is_active", True),
            created_at=user["created_at"]
        )
