"""
MongoDB async database connection using Motor.
Provides database instance and collection access.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from .config import get_settings

settings = get_settings()


class Database:
    """MongoDB database connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        cls.client = AsyncIOMotorClient(settings.MONGODB_URL)
        cls.db = cls.client[settings.DATABASE_NAME]
        
        # Verify connection
        await cls.client.admin.command('ping')
        print(f"Connected to MongoDB: {settings.DATABASE_NAME}")
        
        # Create indexes
        await cls._create_indexes()
    
    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB."""
        if cls.client:
            cls.client.close()
            print("Disconnected from MongoDB")
    
    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for performance."""
        if cls.db is None:
            return
        
        # Users collection indexes
        await cls.db.users.create_index("email", unique=True)
        
        # Tokens collection indexes
        await cls.db.tokens.create_index("token_number", unique=True)
        await cls.db.tokens.create_index("status")
        await cls.db.tokens.create_index("issued_at")
        
        # Patients collection indexes
        await cls.db.patients.create_index("owner_phone")
        
        # Clinical records indexes
        await cls.db.clinical_records.create_index("patient_id")
        await cls.db.clinical_records.create_index("doctor_id")
        await cls.db.clinical_records.create_index("created_at")
        
        print("Database indexes created")
    
    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name."""
        if cls.db is None:
            raise RuntimeError("Database not connected")
        return cls.db[name]


# Convenience function for dependency injection
async def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency for database access."""
    if Database.db is None:
        await Database.connect()
    return Database.db
