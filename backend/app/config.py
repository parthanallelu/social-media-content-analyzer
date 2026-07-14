from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # CORS — restricted to explicit Vercel origin (never wildcard in prod)
    allowed_origin: str = "http://localhost:5173"
    app_env: str = "development"

    # File constraints
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    accepted_extensions: List[str] = [".pdf", ".png", ".jpg", ".jpeg"]
    accepted_mime_types: List[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
    ]

    # Tesseract
    ocr_language: str = "eng"
    ocr_timeout_seconds: int = 60

    # App metadata
    app_name: str = "Social Media Content Analyzer API"
    app_version: str = "1.0.0"

    @field_validator("allowed_origin")
    @classmethod
    def validate_origin(cls, v: str) -> str:
        origins = [o.strip() for o in v.split(",") if o.strip()]
        for origin in origins:
            if not origin.startswith(("http://", "https://")):
                raise ValueError("Each origin in ALLOWED_ORIGIN must start with http:// or https://")
        return ",".join(origins)

    @property
    def cors_origins(self) -> List[str]:
        """Always include localhost for development; production adds Vercel origin(s)."""
        origins = ["http://localhost:5173", "http://localhost:3000"]
        if self.allowed_origin:
            for origin in self.allowed_origin.split(","):
                cleaned = origin.strip().rstrip("/")
                if cleaned and cleaned not in origins:
                    origins.append(cleaned)
        return origins


settings = Settings()
