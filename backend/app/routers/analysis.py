import logging

from fastapi import APIRouter

from app.models.response_models import AnalysisRequest, AnalysisResponse
from app.services.analysis_service import analyze_content

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post("/", response_model=AnalysisResponse, summary="Run rule-based engagement analysis")
async def analyze(request: AnalysisRequest) -> AnalysisResponse:
    """
    Accepts extracted text blocks and an optional platform context, then
    returns rule-based engagement suggestions and a score breakdown.

    This endpoint is **optional** and completely decoupled from the core
    upload/extraction pipeline.

    Supported platforms: `instagram`, `linkedin`, `twitter`, `general` (default).
    """
    platform = request.context.get("platform", "general")
    return analyze_content(request.blocks, platform)
