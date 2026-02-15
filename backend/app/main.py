"""
VetAI - AI-Enabled Veterinary Clinical Decision Support System

Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import traceback

from .config import get_settings
from .database import Database
from .routers import (
    auth_router,
    patients_router,
    queue_router,
    clinical_router,
    diagnosis_router,
    treatment_router,
    reports_router,
    images_router,
    voice_router
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    await Database.connect()
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    yield
    
    # Shutdown
    await Database.disconnect()
    print("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


# Trace Middleware
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    print(f"DEBUG: INCOMING {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: OUTGOING {request.method} {request.url.path} -> {response.status_code}")
    return response


# Global error handler with CORS headers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    from fastapi.responses import JSONResponse
    error_detail = str(exc)
    print(f"ERROR: {request.method} {request.url.path}: {error_detail}")
    
    response = JSONResponse(
        status_code=500,
        content={"detail": error_detail}
    )
    # Force CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse
    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
    # Force CORS headers
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# Mount static files for uploads
if os.path.exists(settings.UPLOAD_DIR):
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include routers
app.include_router(auth_router)
app.include_router(patients_router)
app.include_router(queue_router)
app.include_router(clinical_router)
app.include_router(diagnosis_router)
app.include_router(treatment_router)
app.include_router(reports_router)
app.include_router(images_router)
app.include_router(voice_router)


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy",
        "docs": "/docs"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected" if Database.client else "disconnected",
        "version": settings.APP_VERSION
    }


# Entry point for running directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
