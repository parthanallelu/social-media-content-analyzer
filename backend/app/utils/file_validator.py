import os
from pathlib import Path
from fastapi import UploadFile

from app.config import settings
from app.utils.error_handlers import (
    InvalidFileTypeError,
    FileTooLargeError,
    MissingFileError,
)

# Mapping of accepted extensions to expected MIME types
EXTENSION_MIME_MAP: dict[str, list[str]] = {
    ".pdf": ["application/pdf"],
    ".png": ["image/png"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
}


def validate_file(file: UploadFile, content: bytes) -> str:
    """
    Validates an uploaded file for presence, size, extension, and MIME type.

    Returns the detected file category: "pdf" or "image".
    Raises AppException subclasses on any validation failure.
    """
    if file is None or not file.filename:
        raise MissingFileError()

    # --- Size check ---
    size = len(content)
    if size > settings.max_file_size:
        raise FileTooLargeError(
            detail=f"File size {size} bytes exceeds limit of {settings.max_file_size} bytes."
        )

    # --- Extension check ---
    ext = Path(file.filename).suffix.lower()
    if ext not in EXTENSION_MIME_MAP:
        raise InvalidFileTypeError(
            detail=f"Extension '{ext}' is not allowed. Accepted: {settings.accepted_extensions}"
        )

    # --- MIME type check (from Content-Type header) ---
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    expected_mimes = EXTENSION_MIME_MAP[ext]
    if content_type and content_type not in expected_mimes:
        raise InvalidFileTypeError(
            detail=f"MIME type '{content_type}' does not match extension '{ext}'."
        )

    # --- Magic bytes check (defense-in-depth) ---
    _validate_magic_bytes(content, ext)

    return "pdf" if ext == ".pdf" else "image"


def _validate_magic_bytes(content: bytes, ext: str) -> None:
    """
    Validates file header bytes against known signatures.
    This catches renamed files (e.g., a .exe renamed to .pdf).
    """
    header = content[:8]

    if ext == ".pdf":
        if not header.startswith(b"%PDF"):
            raise InvalidFileTypeError(
                detail="File header does not match PDF format (missing %PDF signature)."
            )
    elif ext == ".png":
        PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
        if not header.startswith(PNG_MAGIC):
            raise InvalidFileTypeError(
                detail="File header does not match PNG format."
            )
    elif ext in (".jpg", ".jpeg"):
        JPEG_MAGIC = (b"\xff\xd8\xff",)
        if not any(header.startswith(m) for m in JPEG_MAGIC):
            raise InvalidFileTypeError(
                detail="File header does not match JPEG format."
            )
