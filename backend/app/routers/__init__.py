"""Routers package for VetAI API."""

from .auth import router as auth_router
from .patients import router as patients_router
from .queue import router as queue_router
from .clinical import router as clinical_router
from .diagnosis import router as diagnosis_router
from .treatment import router as treatment_router
from .reports import router as reports_router
from .images import router as images_router
from .voice import router as voice_router

__all__ = [
    "auth_router",
    "patients_router",
    "queue_router",
    "clinical_router",
    "diagnosis_router",
    "treatment_router",
    "reports_router",
    "images_router",
    "voice_router"
]
