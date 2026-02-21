
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import sys

# Add current directory to path to allow imports if needed, though here I am using direct connection
sys.path.append('.')

async def list_doctors():
    # Database connection parameters from config.py
    MONGODB_URL = "mongodb://localhost:27017"
    DATABASE_NAME = "vetai"
    
    print(f"Connecting to {MONGODB_URL}...")
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    print("Searching for doctors...")
    try:
        # Check connection first
        await client.admin.command('ping')
        
        # Get users collection
        users_collection = db["users"]
        
        # Find doctors
        cursor = users_collection.find({"role": "doctor"})
        doctors = await cursor.to_list(length=100)
        
        if not doctors:
            print("No doctors found.")
        else:
            print(f"\nFound {len(doctors)} doctor(s):")
            print("-" * 80)
            print(f"{'Name':<25} | {'Email':<30} | {'ID'}")
            print("-" * 80)
            for doc in doctors:
                print(f"{doc.get('full_name', 'N/A'):<25} | {doc.get('email', 'N/A'):<30} | {doc.get('_id')}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_doctors())
