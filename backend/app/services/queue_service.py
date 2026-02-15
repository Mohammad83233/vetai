"""
Queue and token management service.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from bson import ObjectId

from ..config import get_settings
from ..database import Database
from ..models.queue import QueueToken, QueueTokenCreate, QueueStatus, QueueDisplay

settings = get_settings()


class QueueService:
    """Queue and token management service."""
    
    @classmethod
    async def _get_next_token_number(cls) -> str:
        """Generate next sequential token number (date-stamped to avoid collisions)."""
        tokens = Database.get_collection("tokens")
        
        today = datetime.utcnow()
        date_str = today.strftime("%Y%m%d")
        today_start = today.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find today's highest token number to derive next sequence
        prefix = f"{settings.TOKEN_PREFIX}-{date_str}-"
        latest = await tokens.find_one(
            {"token_number": {"$regex": f"^{prefix}"}},
            sort=[("token_number", -1)]
        )
        
        if latest:
            try:
                last_seq = int(latest["token_number"].split("-")[-1])
            except (ValueError, IndexError):
                last_seq = 0
        else:
            last_seq = 0
        
        # Format: VET-20260210-001, VET-20260210-002, etc.
        return f"{prefix}{last_seq + 1:03d}"
    
    @classmethod
    async def issue_token(
        cls, 
        token_data: QueueTokenCreate,
        issued_by: str
    ) -> QueueToken:
        """Issue a new queue token for a patient."""
        tokens = Database.get_collection("tokens")
        patients = Database.get_collection("patients")
        
        # Get patient info
        patient = await patients.find_one({"_id": ObjectId(token_data.patient_id)})
        if not patient:
            raise ValueError("Patient not found")
        
        # Generate token number
        token_number = await cls._get_next_token_number()
        
        # Calculate estimated wait time
        estimated_wait = await cls._calculate_wait_time(token_data.priority)
        
        token_doc = {
            "token_number": token_number,
            "patient_id": token_data.patient_id,
            "patient_name": patient.get("name"),
            "species": patient.get("species"),
            "owner_name": patient.get("owner", {}).get("name"),
            "status": QueueStatus.WAITING.value,
            "priority": token_data.priority,
            "notes": token_data.notes,
            "issued_at": datetime.utcnow(),
            "issued_by": issued_by,
            "called_at": None,
            "called_by": None,
            "completed_at": None,
            "estimated_wait_minutes": estimated_wait
        }
        
        result = await tokens.insert_one(token_doc)
        token_doc["_id"] = str(result.inserted_id)
        
        return QueueToken(**token_doc)
    
    @classmethod
    async def _calculate_wait_time(cls, priority: int) -> int:
        """Calculate estimated wait time in minutes."""
        tokens = Database.get_collection("tokens")
        
        # Count waiting patients
        waiting_count = await tokens.count_documents({
            "status": QueueStatus.WAITING.value
        })
        
        # Base time per patient (15 min) adjusted by priority
        base_time = 15
        priority_factor = max(0.5, 1 - (priority * 0.1))
        
        return int(waiting_count * base_time * priority_factor)
    
    @classmethod
    async def get_queue_display(cls) -> QueueDisplay:
        """Get current queue status for display."""
        tokens = Database.get_collection("tokens")
        
        # Get today's start
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get waiting tokens (sorted by priority desc, then by time)
        waiting_cursor = tokens.find({
            "status": QueueStatus.WAITING.value,
            "issued_at": {"$gte": today}
        }).sort([("priority", -1), ("issued_at", 1)])
        
        waiting_tokens = []
        async for token in waiting_cursor:
            token["_id"] = str(token["_id"])
            waiting_tokens.append(QueueToken(**token))
        
        # Get in-progress tokens
        in_progress_cursor = tokens.find({
            "status": {"$in": [QueueStatus.CALLED.value, QueueStatus.IN_PROGRESS.value]},
            "issued_at": {"$gte": today}
        }).sort("called_at", 1)
        
        in_progress_tokens = []
        async for token in in_progress_cursor:
            token["_id"] = str(token["_id"])
            in_progress_tokens.append(QueueToken(**token))
        
        # Calculate average wait time
        avg_wait = None
        completed_cursor = tokens.find({
            "status": QueueStatus.COMPLETED.value,
            "issued_at": {"$gte": today},
            "called_at": {"$ne": None}
        })
        
        wait_times = []
        async for token in completed_cursor:
            if token.get("called_at") and token.get("issued_at"):
                wait = (token["called_at"] - token["issued_at"]).total_seconds() / 60
                wait_times.append(wait)
        
        if wait_times:
            avg_wait = sum(wait_times) / len(wait_times)
        
        return QueueDisplay(
            waiting=waiting_tokens,
            in_progress=in_progress_tokens,
            total_waiting=len(waiting_tokens),
            average_wait_minutes=avg_wait,
            next_token=waiting_tokens[0].token_number if waiting_tokens else None
        )
    
    @classmethod
    async def call_next(cls, doctor_id: str, token_id: Optional[str] = None) -> Optional[QueueToken]:
        """Call the next patient or a specific token."""
        tokens = Database.get_collection("tokens")
        
        if token_id:
            # Call specific token
            filter_query = {"_id": ObjectId(token_id)}
        else:
            # Get next in queue (highest priority, earliest time)
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cursor = tokens.find({
                "status": QueueStatus.WAITING.value,
                "issued_at": {"$gte": today}
            }).sort([("priority", -1), ("issued_at", 1)]).limit(1)
            
            token = await cursor.to_list(length=1)
            if not token:
                return None
            filter_query = {"_id": token[0]["_id"]}
        
        # Update token status
        result = await tokens.find_one_and_update(
            filter_query,
            {
                "$set": {
                    "status": QueueStatus.CALLED.value,
                    "called_at": datetime.utcnow(),
                    "called_by": doctor_id
                }
            },
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            return QueueToken(**result)
        return None
    
    @classmethod
    async def update_token_status(
        cls, 
        token_id: str, 
        status: QueueStatus,
        notes: Optional[str] = None
    ) -> Optional[QueueToken]:
        """Update token status."""
        tokens = Database.get_collection("tokens")
        
        update_data = {"status": status.value}
        
        if status == QueueStatus.COMPLETED:
            update_data["completed_at"] = datetime.utcnow()
        
        if notes:
            update_data["notes"] = notes
        
        result = await tokens.find_one_and_update(
            {"_id": ObjectId(token_id)},
            {"$set": update_data},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            return QueueToken(**result)
        return None
    
    @classmethod
    async def get_token(cls, token_id: str) -> Optional[QueueToken]:
        """Get token by ID."""
        tokens = Database.get_collection("tokens")
        
        try:
            token = await tokens.find_one({"_id": ObjectId(token_id)})
        except:
            return None
        
        if token:
            token["_id"] = str(token["_id"])
            return QueueToken(**token)
        return None
    
    @classmethod
    async def get_token_by_number(cls, token_number: str) -> Optional[QueueToken]:
        """Get token by token number."""
        tokens = Database.get_collection("tokens")
        
        token = await tokens.find_one({"token_number": token_number})
        
        if token:
            token["_id"] = str(token["_id"])
            return QueueToken(**token)
        return None
    
    @classmethod
    async def get_doctor_active_tokens(cls, doctor_id: str) -> List[QueueToken]:
        """Get doctor's currently active tokens."""
        tokens = Database.get_collection("tokens")
        
        cursor = tokens.find({
            "called_by": doctor_id,
            "status": {"$in": [QueueStatus.CALLED.value, QueueStatus.IN_PROGRESS.value]}
        }).sort("called_at", -1)
        
        result = []
        async for token in cursor:
            token["_id"] = str(token["_id"])
            result.append(QueueToken(**token))
        
        return result
