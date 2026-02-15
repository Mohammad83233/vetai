"""
Voice transcription service using OpenAI Whisper.
Provides local speech-to-text for clinical voice notes.
"""

import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

# Whisper model will be lazy loaded
_whisper_model = None

# Common veterinary symptoms for extraction
SYMPTOM_KEYWORDS = [
    # General symptoms
    "vomiting", "diarrhea", "lethargy", "fever", "loss of appetite", "weight loss",
    "coughing", "sneezing", "nasal discharge", "eye discharge", "limping",
    "scratching", "itching", "hair loss", "redness", "swelling", "pain",
    "bleeding", "seizures", "tremors", "weakness", "collapse",
    # Digestive
    "not eating", "drinking more", "drinking less", "constipation", "bloating",
    # Respiratory
    "breathing difficulty", "wheezing", "panting", "gasping",
    # Urinary
    "frequent urination", "blood in urine", "straining to urinate", "accidents",
    # Skin
    "rash", "bumps", "scabs", "hot spots", "dry skin", "oily coat",
    # Eyes
    "cloudy eyes", "red eyes", "squinting", "tearing", "pawing at eyes",
    # Ears
    "ear scratching", "head shaking", "ear odor", "ear discharge",
    # Behavior
    "aggression", "hiding", "restlessness", "pacing", "circling",
    # Mobility
    "stiffness", "difficulty standing", "dragging legs", "reluctant to move"
]


def _load_whisper_model(model_size: str = "base"):
    """Lazy load Whisper model to avoid startup delay."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            print(f"Loading Whisper model ({model_size})...")
            _whisper_model = whisper.load_model(model_size)
            print("Whisper model loaded successfully")
        except Exception as e:
            print(f"Failed to load Whisper: {e}")
            _whisper_model = "unavailable"
    return _whisper_model if _whisper_model != "unavailable" else None


class VoiceService:
    """Voice transcription and symptom extraction service."""
    
    UPLOAD_DIR = Path("uploads/audio")
    ALLOWED_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.ogg', '.webm', '.flac'}
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    
    def __init__(self):
        self.upload_dir = self.UPLOAD_DIR
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_audio(
        self, 
        file_content: bytes, 
        filename: str
    ) -> Dict[str, Any]:
        """Save uploaded audio file and return metadata."""
        # Validate file extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise ValueError(f"Invalid audio type. Allowed: {self.ALLOWED_EXTENSIONS}")
        
        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Generate unique ID and path
        audio_id = str(uuid.uuid4())
        date_folder = datetime.now().strftime("%Y-%m-%d")
        save_dir = self.upload_dir / date_folder
        save_dir.mkdir(parents=True, exist_ok=True)
        
        audio_path = save_dir / f"{audio_id}{ext}"
        with open(audio_path, 'wb') as f:
            f.write(file_content)
        
        # Estimate duration (rough estimate based on file size)
        # More accurate duration requires audio parsing
        estimated_duration = len(file_content) / 16000  # Rough estimate
        
        return {
            "audio_id": audio_id,
            "audio_path": str(audio_path),
            "filename": filename,
            "file_size": len(file_content),
            "duration_seconds": estimated_duration,
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "uploaded"
        }
    
    async def transcribe(
        self, 
        audio_path: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """
        Transcribe audio using Whisper.
        Returns transcription text and extracted symptoms.
        """
        model = _load_whisper_model()
        
        if model is None:
            # Fallback: return demo transcription if Whisper unavailable
            return self._demo_transcription()
        
        # Check for FFmpeg (required by Whisper)
        import shutil
        if not shutil.which("ffmpeg"):
            print("WARNING: FFmpeg not found. Falling back to demo transcription.")
            return self._demo_transcription()
        
        try:
            # Transcribe with Whisper
            result = model.transcribe(
                audio_path,
                language=language,
                fp16=False  # Use FP32 for CPU compatibility
            )
            
            transcription = result.get("text", "").strip()
            
            # Extract symptoms from transcription
            extracted_symptoms = self._extract_symptoms(transcription)
            
            return {
                "transcription": transcription,
                "language": result.get("language", language),
                "extracted_symptoms": extracted_symptoms,
                "confidence": self._calculate_confidence(transcription, extracted_symptoms),
                "word_count": len(transcription.split()),
                "transcribed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()  # Print full error to console
            print(f"DEBUG: Transcription error: {e}")
            return {
                "transcription": "",
                "error": str(e),
                "extracted_symptoms": [],
                "confidence": 0.0,
                "transcribed_at": datetime.utcnow().isoformat()
            }
    
    def _extract_symptoms(self, text: str) -> List[str]:
        """Extract symptom keywords from transcribed text."""
        text_lower = text.lower()
        found_symptoms = []
        
        for symptom in SYMPTOM_KEYWORDS:
            if symptom in text_lower:
                found_symptoms.append(symptom)
        
        # Also look for common phrases
        phrase_mappings = {
            "throwing up": "vomiting",
            "threw up": "vomiting",
            "not eating": "loss of appetite",
            "won't eat": "loss of appetite",
            "runny nose": "nasal discharge",
            "runny eyes": "eye discharge",
            "can't walk": "difficulty standing",
            "trouble breathing": "breathing difficulty",
            "losing weight": "weight loss",
            "gained weight": "weight gain",
            "drinking a lot": "drinking more",
            "peeing a lot": "frequent urination",
            "scratching a lot": "itching",
            "losing hair": "hair loss",
            "red skin": "redness",
            "hot to touch": "fever"
        }
        
        for phrase, symptom in phrase_mappings.items():
            if phrase in text_lower and symptom not in found_symptoms:
                found_symptoms.append(symptom)
        
        return list(set(found_symptoms))
    
    def _calculate_confidence(self, text: str, symptoms: List[str]) -> float:
        """Calculate confidence score based on transcription quality."""
        if not text:
            return 0.0
        
        word_count = len(text.split())
        symptom_count = len(symptoms)
        
        # Base confidence on text length and symptom extraction
        base = min(0.5, word_count / 50)  # Up to 0.5 for longer text
        symptom_bonus = min(0.4, symptom_count * 0.1)  # Up to 0.4 for symptoms
        
        return min(0.95, base + symptom_bonus + 0.1)
    
    def _demo_transcription(self) -> Dict[str, Any]:
        """Return demo transcription when Whisper is unavailable."""
        demo_text = "The dog has been vomiting for two days and showing signs of lethargy. Also noticed some diarrhea and loss of appetite."
        
        return {
            "transcription": demo_text,
            "language": "en",
            "extracted_symptoms": ["vomiting", "lethargy", "diarrhea", "loss of appetite"],
            "confidence": 0.75,
            "word_count": len(demo_text.split()),
            "is_demo": True,
            "transcribed_at": datetime.utcnow().isoformat()
        }
    
    async def get_audio(self, audio_id: str) -> Optional[Dict[str, Any]]:
        """Get audio metadata by ID from database."""
        from ..database import Database
        
        audio_collection = Database.get_collection("audio")
        audio = await audio_collection.find_one({"audio_id": audio_id})
        
        if audio:
            audio["_id"] = str(audio["_id"])
            return audio
        return None
    
    async def delete_audio(self, audio_id: str) -> bool:
        """Delete audio file and database record."""
        from ..database import Database
        
        audio_collection = Database.get_collection("audio")
        audio = await audio_collection.find_one({"audio_id": audio_id})
        
        if not audio:
            return False
        
        # Delete file
        if "audio_path" in audio:
            try:
                os.remove(audio["audio_path"])
            except OSError:
                pass
        
        # Delete database record
        await audio_collection.delete_one({"audio_id": audio_id})
        return True


# Singleton instance
voice_service = VoiceService()
