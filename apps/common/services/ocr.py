# moved to apps/ocr/services.py
from apps.ocr.services import OCRServiceError, extract_text_from_image  # noqa: F401


__all__ = ["OCRServiceError", "extract_text_from_image"]
