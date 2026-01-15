"""
Health Check API Endpoints
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "vibber-ai-agent"
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for Kubernetes"""
    # In production, this would check DB connections, etc.
    return {
        "ready": True,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check for Kubernetes"""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
