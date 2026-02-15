"""
Patient management service.
"""

from datetime import datetime
from typing import Optional, List
from bson import ObjectId

from ..database import Database
from ..models.patient import Patient, PatientCreate, PatientUpdate


class PatientService:
    """Patient management service."""
    
    @classmethod
    async def create_patient(cls, patient_data: PatientCreate) -> Patient:
        """Create a new patient record."""
        patients = Database.get_collection("patients")
        
        patient_doc = {
            "name": patient_data.name,
            "species": patient_data.species.value,
            "breed": patient_data.breed,
            "weight_kg": patient_data.weight_kg,
            "age_months": patient_data.age_months,
            "sex": patient_data.sex,
            "color": patient_data.color,
            "microchip_id": patient_data.microchip_id,
            "medical_history": patient_data.medical_history or [],
            "allergies": patient_data.allergies or [],
            "owner": patient_data.owner.model_dump(),
            "created_at": datetime.utcnow(),
            "updated_at": None
        }
        
        result = await patients.insert_one(patient_doc)
        patient_doc["_id"] = str(result.inserted_id)
        
        return Patient(**patient_doc)
    
    @classmethod
    async def get_patient(cls, patient_id: str) -> Optional[Patient]:
        """Get patient by ID."""
        patients = Database.get_collection("patients")
        
        try:
            patient = await patients.find_one({"_id": ObjectId(patient_id)})
        except:
            return None
            
        if not patient:
            return None
        
        patient["_id"] = str(patient["_id"])
        return Patient(**patient)
    
    @classmethod
    async def update_patient(cls, patient_id: str, updates: PatientUpdate) -> Optional[Patient]:
        """Update patient record."""
        patients = Database.get_collection("patients")
        
        update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
        if not update_data:
            return await cls.get_patient(patient_id)
        
        update_data["updated_at"] = datetime.utcnow()
        
        if "owner" in update_data:
            update_data["owner"] = update_data["owner"]
        
        result = await patients.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return None
        
        return await cls.get_patient(patient_id)
    
    @classmethod
    async def delete_patient(cls, patient_id: str) -> bool:
        """Delete patient record."""
        patients = Database.get_collection("patients")
        result = await patients.delete_one({"_id": ObjectId(patient_id)})
        return result.deleted_count > 0
    
    @classmethod
    async def search_patients(
        cls, 
        query: Optional[str] = None,
        species: Optional[str] = None,
        owner_phone: Optional[str] = None,
        limit: int = 50
    ) -> List[Patient]:
        """Search patients with filters."""
        patients = Database.get_collection("patients")
        
        filter_query = {}
        
        if query:
            filter_query["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"owner.name": {"$regex": query, "$options": "i"}}
            ]
        
        if species:
            filter_query["species"] = species
        
        if owner_phone:
            filter_query["owner.phone"] = owner_phone
        
        cursor = patients.find(filter_query).sort("created_at", -1).limit(limit)
        
        results = []
        async for patient in cursor:
            patient["_id"] = str(patient["_id"])
            results.append(Patient(**patient))
        
        return results
    
    @classmethod
    async def get_patient_history(cls, patient_id: str) -> List[dict]:
        """Get patient's clinical history."""
        records = Database.get_collection("clinical_records")
        
        cursor = records.find({"patient_id": patient_id}).sort("created_at", -1)
        
        history = []
        async for record in cursor:
            record["_id"] = str(record["_id"])
            history.append(record)
        
        return history
