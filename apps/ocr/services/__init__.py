# moved from apps/common/services/ocr.py
import base64
from typing import BinaryIO


class OCRServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def encode_file_to_base64(fileobj: BinaryIO) -> str:
    if hasattr(fileobj, "seek"):
        fileobj.seek(0)
    content = fileobj.read()
    if hasattr(fileobj, "seek"):
        fileobj.seek(0)
    if not content:
        raise OCRServiceError("Empty image content", status_code=400)
    return base64.b64encode(content).decode()
