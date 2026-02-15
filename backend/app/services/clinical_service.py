"""
Clinical records service.
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from ..database import Database
from ..models.clinical import ClinicalRecord, ClinicalRecordCreate


class ClinicalService:
    """Clinical records management service."""
    
    @classmethod
    async def create_record(
        cls, 
        record_data: ClinicalRecordCreate,
        doctor_id: str
    ) -> ClinicalRecord:
        """Create a new clinical record."""
        records = Database.get_collection("clinical_records")
        
        record_doc = {
            "patient_id": record_data.patient_id,
            "token_id": record_data.token_id,
            "doctor_id": doctor_id,
            "clinical_input": record_data.clinical_input.model_dump(),
            "extracted_features": None,
            "diagnosis_id": None,
            "treatment_id": None,
            "report_id": None,
            "status": "in_progress",
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        
        result = await records.insert_one(record_doc)
        record_doc["_id"] = str(result.inserted_id)
        
        return ClinicalRecord(**record_doc)
    
    @classmethod
    async def get_record(cls, record_id: str) -> Optional[ClinicalRecord]:
        """Get clinical record by ID."""
        records = Database.get_collection("clinical_records")
        
        try:
            record = await records.find_one({"_id": ObjectId(record_id)})
        except:
            return None
        
        if not record:
            return None
        
        record["_id"] = str(record["_id"])
        return ClinicalRecord(**record)
    
    @classmethod
    async def update_record(
        cls,
        record_id: str,
        updates: dict
    ) -> Optional[ClinicalRecord]:
        """Update clinical record."""
        records = Database.get_collection("clinical_records")
        
        updates["updated_at"] = datetime.utcnow()
        
        result = await records.find_one_and_update(
            {"_id": ObjectId(record_id)},
            {"$set": updates},
            return_document=True
        )
        
        if result:
            result["_id"] = str(result["_id"])
            return ClinicalRecord(**result)
        return None
    
    @classmethod
    async def link_diagnosis(cls, record_id: str, diagnosis_id: str) -> Optional[ClinicalRecord]:
        """Link diagnosis to clinical record."""
        return await cls.update_record(record_id, {"diagnosis_id": diagnosis_id})
    
    @classmethod
    async def link_treatment(cls, record_id: str, treatment_id: str) -> Optional[ClinicalRecord]:
        """Link treatment to clinical record."""
        return await cls.update_record(record_id, {"treatment_id": treatment_id})
    
    @classmethod
    async def link_report(cls, record_id: str, report_id: str) -> Optional[ClinicalRecord]:
        """Link SOAP report to clinical record."""
        return await cls.update_record(record_id, {"report_id": report_id})
    
    @classmethod
    async def get_patient_records(
        cls, 
        patient_id: str,
        limit: int = 50
    ) -> List[ClinicalRecord]:
        """Get all clinical records for a patient."""
        records = Database.get_collection("clinical_records")
        
        cursor = records.find({"patient_id": patient_id}).sort("created_at", -1).limit(limit)
        
        result = []
        async for record in cursor:
            record["_id"] = str(record["_id"])
            result.append(ClinicalRecord(**record))
        
        return result
    
    @classmethod
    async def get_doctor_records(
        cls,
        doctor_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ClinicalRecord]:
        """Get clinical records by doctor."""
        records = Database.get_collection("clinical_records")
        
        filter_query = {"doctor_id": doctor_id}
        if status:
            filter_query["status"] = status
        
        cursor = records.find(filter_query).sort("created_at", -1).limit(limit)
        
        result = []
        async for record in cursor:
            record["_id"] = str(record["_id"])
            result.append(ClinicalRecord(**record))
        
        return result
    
    @classmethod
    async def complete_record(cls, record_id: str) -> Optional[ClinicalRecord]:
        """Mark clinical record as completed."""
        return await cls.update_record(record_id, {"status": "completed"})
