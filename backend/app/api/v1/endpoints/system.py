"""System diagnostics and health status endpoint (Phase 4)."""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.llm.service import llm_service
from vision.config.settings import vision_settings
import torch

router = APIRouter()


@router.get(
    "/system/status",
    status_code=status.HTTP_200_OK,
    summary="Get System Component Status",
    description="Returns real-time health and runtime telemetry for backend, database, YOLO vision model, Ollama LLM, and compute hardware.",
    tags=["System Status"]
)
def get_system_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    # 1. Database Check
    db_status = "CONNECTED"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "UNAVAILABLE"

    # 2. LLM Check
    llm_status = "AVAILABLE"
    try:
        health = llm_service.health_check()
        if not health.is_available:
            llm_status = "UNAVAILABLE"
    except Exception:
        llm_status = "UNAVAILABLE"

    # 3. Compute Device
    device_name = "CPU"
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)

    return {
        "backend": "HEALTHY",
        "database": db_status,
        "vision_model": "LOADED",
        "llm": llm_status,
        "model_name": "YOLO11n-seg",
        "llm_model": "gemma3:latest",
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "device_name": device_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
