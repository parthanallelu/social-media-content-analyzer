import logging
import logging.config

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.middleware.logging_middleware import LoggingMiddleware
from app.routers import health, upload, analysis
from app.utils.error_handlers import AppException

# ── Logging configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── App instantiation ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Stateless API for extracting structured text from PDFs and images, "
        "with optional rule-based engagement analysis."
    ),
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
)

# ── CORS — explicit origins only, never wildcard ──────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,   # ["http://localhost:5173", "https://<vercel-url>"]
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"],
)

# ── Request logging ───────────────────────────────────────────────────────────
app.add_middleware(LoggingMiddleware)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(analysis.router)

# ── Global exception handlers ─────────────────────────────────────────────────
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Converts all typed AppException subclasses into a consistent JSON error body.
    Stack traces are never exposed in the response.
    """
    logger.warning(
        "AppException: code=%s status=%d path=%s",
        exc.error_code.value,
        exc.status_code,
        request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for any unhandled exceptions — returns 500 with a safe generic message."""
    logger.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected server error occurred. Please try again.",
            "detail": None,
        },
    )


logger.info("App '%s' v%s starting — CORS origins: %s", settings.app_name, settings.app_version, settings.cors_origins)
