# moved from apps/common/services/ocr.py

import json
from typing import BinaryIO

import requests


KAKAO_OCR_ENDPOINT = "https://dapi.kakao.com/v2/vision/text/ocr"


class OCRServiceError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def extract_text_from_image(fileobj: BinaryIO, api_key: str, timeout: int = 10) -> str:
    if not api_key:
        raise OCRServiceError("Kakao REST API key not configured", status_code=500)

    filename = getattr(fileobj, "name", "receipt.jpg") or "receipt.jpg"
    content_type = getattr(fileobj, "content_type", "application/octet-stream")

    if hasattr(fileobj, "seek"):
        fileobj.seek(0)
    content = fileobj.read()
    if hasattr(fileobj, "seek"):
        fileobj.seek(0)
    if not content:
        raise OCRServiceError("Empty image content", status_code=400)

    files = {
        "image": (filename, content, content_type),
    }
    headers = {
        "Authorization": f"KakaoAK {api_key}",
    }

    try:
        response = requests.post(KAKAO_OCR_ENDPOINT, headers=headers, files=files, timeout=timeout)
    except requests.Timeout as exc:
        raise OCRServiceError("Kakao OCR request timed out", status_code=504) from exc
    except requests.RequestException as exc:
        raise OCRServiceError(f"Kakao OCR request failed: {exc}") from exc

    if response.status_code >= 500:
        raise OCRServiceError("Kakao OCR service unavailable", status_code=502)
    if response.status_code >= 400:
        message = response.text or f"Kakao OCR error {response.status_code}"
        raise OCRServiceError(message, status_code=400)

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        raise OCRServiceError("Invalid response from Kakao OCR", status_code=502) from exc

    result_blocks = payload.get("result", []) if isinstance(payload, dict) else []
    lines = []
    for block in result_blocks:
        words = block.get("recognition_words") if isinstance(block, dict) else None
        if isinstance(words, list) and words:
            lines.append(" ".join(str(word) for word in words if word))

    text = "\n".join(line for line in lines if line).strip()
    return text
