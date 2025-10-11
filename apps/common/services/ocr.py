# moved to apps/ocr/services
from apps.ocr.services import OCRServiceError, encode_file_to_base64  # noqa: F401

__all__ = ["OCRServiceError", "encode_file_to_base64"]
