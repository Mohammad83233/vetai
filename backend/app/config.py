"""
Application configuration using Pydantic Settings.
Loads from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = "VetAI Clinical Decision Support"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "vetai"
    
    # JWT Authentication
    SECRET_KEY: str = "vetai-secret-key-change-in-production-2024"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Token System
    TOKEN_PREFIX: str = "VET"
    TOKENS_PER_DAY_RESET: bool = True
    
    # AI Models
    WHISPER_MODEL: str = "base"  # tiny, base, small, medium, large
    NLP_MODEL: str = "en_core_web_sm"
    
    # File Upload
    MAX_IMAGE_SIZE_MB: int = 10
    MAX_AUDIO_SIZE_MB: int = 50
    UPLOAD_DIR: str = "./uploads"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
