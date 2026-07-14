import logging

from fastapi import APIRouter, File, UploadFile, HTTPException

from app.config import settings
from app.models.response_models import ExtractionResponse
from app.services import pdf_extractor, ocr_service
from app.utils.file_validator import validate_file
from app.utils.error_handlers import AppException, MissingFileError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/pdf", response_model=ExtractionResponse, summary="Extract text from a PDF")
async def upload_pdf(file: UploadFile = File(...)) -> ExtractionResponse:
    """
    Accept a PDF file and return structured text blocks preserving headings,
    paragraphs, and bullet points.

    - **Max size**: 10 MB
    - **Accepted types**: .pdf
    """
    if not file or not file.filename:
        raise MissingFileError()

    content = await file.read()
    validate_file(file, content)  # raises typed AppException on failure

    content_obj, metadata, page_count = pdf_extractor.extract_pdf(content, file.filename)

    return ExtractionResponse(
        filename=file.filename,
        file_type="pdf",
        page_count=page_count,
        content=content_obj,
        metadata=metadata,
    )


@router.post("/image", response_model=ExtractionResponse, summary="Extract text from an image via OCR")
async def upload_image(file: UploadFile = File(...)) -> ExtractionResponse:
    """
    Accept a PNG or JPEG image, run OpenCV preprocessing and pytesseract OCR,
    and return extracted text blocks.

    - **Max size**: 10 MB
    - **Accepted types**: .png, .jpg, .jpeg
    - **OCR language**: English
    - **Note**: OCR can take 10–30 seconds for complex images.
    """
    if not file or not file.filename:
        raise MissingFileError()

    content = await file.read()
    validate_file(file, content)  # raises typed AppException on failure

    content_obj, metadata = ocr_service.extract_image(content, file.filename)

    return ExtractionResponse(
        filename=file.filename,
        file_type="image",
        page_count=1,
        content=content_obj,
        metadata=metadata,
    )
