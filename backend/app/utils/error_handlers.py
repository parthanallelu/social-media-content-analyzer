from enum import Enum
from typing import Optional
from fastapi import HTTPException


class ErrorCode(str, Enum):
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CORRUPTED_FILE = "CORRUPTED_FILE"
    MISSING_FILE = "MISSING_FILE"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    OCR_FAILED = "OCR_FAILED"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"
    EMPTY_CONTENT = "EMPTY_CONTENT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Human-readable default messages per error code
ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_FILE_TYPE: (
        "Unsupported file type. Please upload a PDF, PNG, JPG, or JPEG file."
    ),
    ErrorCode.FILE_TOO_LARGE: (
        "File exceeds the 10 MB limit. Please compress or trim the file before uploading."
    ),
    ErrorCode.CORRUPTED_FILE: (
        "This file appears to be corrupted or password-protected and could not be read."
    ),
    ErrorCode.MISSING_FILE: "No file was provided in the request.",
    ErrorCode.EXTRACTION_FAILED: (
        "Text extraction failed unexpectedly. Please try again or use a different file."
    ),
    ErrorCode.OCR_FAILED: (
        "Text could not be extracted from this image. "
        "Try uploading a higher-quality or higher-resolution scan."
    ),
    ErrorCode.ANALYSIS_FAILED: (
        "Engagement analysis failed. Your extracted text is still available."
    ),
    ErrorCode.EMPTY_CONTENT: "No text content was provided for analysis.",
    ErrorCode.INTERNAL_ERROR: "An unexpected server error occurred. Please try again.",
}


class AppException(HTTPException):
    """Base application exception that produces a structured JSON error body."""

    def __init__(
        self,
        error_code: ErrorCode,
        status_code: int = 500,
        detail: Optional[str] = None,
    ):
        self.error_code = error_code
        self.user_message = ERROR_MESSAGES.get(error_code, "An error occurred.")
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code.value,
                "message": self.user_message,
                "detail": detail,
            },
        )


class InvalidFileTypeError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ErrorCode.INVALID_FILE_TYPE, 400, detail)


class FileTooLargeError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ErrorCode.FILE_TOO_LARGE, 400, detail)


class CorruptedFileError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ErrorCode.CORRUPTED_FILE, 400, detail)


class MissingFileError(AppException):
    def __init__(self):
        super().__init__(ErrorCode.MISSING_FILE, 422)


class ExtractionFailedError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ErrorCode.EXTRACTION_FAILED, 500, detail)


class OCRFailedError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ErrorCode.OCR_FAILED, 500, detail)


class AnalysisFailedError(AppException):
    def __init__(self, detail: Optional[str] = None):
        super().__init__(ErrorCode.ANALYSIS_FAILED, 500, detail)


class EmptyContentError(AppException):
    def __init__(self):
        super().__init__(ErrorCode.EMPTY_CONTENT, 400)
