import time
import logging

from fastapi import APIRouter

from app.config import settings
from app.models.response_models import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint used by Render and pre-warm pings from the frontend.
    Returns immediately with 200 OK.
    """
    return HealthResponse(status="ok", version=settings.app_version)
