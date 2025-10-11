import json
import time
import uuid
from typing import Dict

import requests

from apps.ocr.services import OCRServiceError


def extract_text_clova(
    b64: str,
    *,
    api_url: str,
    secret: str,
    image_format: str = "jpg",
    timeout: int = 8,
) -> Dict[str, object]:
    if not api_url or not secret:
        raise OCRServiceError("Clova OCR configuration missing", status_code=500)

    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "X-OCR-SECRET": secret,
    }

    payload = {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "lang": "ko",
        "images": [
            {
                "name": "receipt",
                "format": (image_format or "jpg").lower(),
                "data": b64,
            }
        ],
    }

    try:
        response = requests.post(
            api_url, headers=headers, data=json.dumps(payload), timeout=timeout
        )
    except requests.Timeout as exc:
        raise OCRServiceError("Clova OCR request timed out", status_code=504) from exc
    except requests.RequestException as exc:
        raise OCRServiceError(f"Clova OCR request failed: {exc}") from exc

    if response.status_code >= 500:
        raise OCRServiceError("Clova OCR service unavailable", status_code=502)
    if response.status_code >= 400:
        raise OCRServiceError(
            response.text or "Clova OCR request rejected", status_code=400
        )

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise OCRServiceError(
            "Invalid response from Clova OCR", status_code=502
        ) from exc

    text_lines = _collect_lines(data)
    text = "\n".join(text_lines).strip()

    return {"text": text, "raw": data, "lines": text_lines}


def _collect_lines(payload: Dict[str, object]) -> list[str]:
    images = payload.get("images", []) if isinstance(payload, dict) else []
    if not images:
        return []

    fields = images[0].get("fields", []) if isinstance(images[0], dict) else []
    if not isinstance(fields, list):
        return []

    lines = []
    current = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        text = field.get("inferText")
        if not text:
            continue
        current.append(text)
        if field.get("lineBreak"):
            lines.append(" ".join(current))
            current = []
    if current:
        lines.append(" ".join(current))
    return lines


def _pick_merchant(lines):
    for line in lines:
        normalized = line.strip()
        if not normalized:
            continue
        lower = normalized.lower()
        if any(
            keyword in lower
            for keyword in ["승인", "금액", "카드", "거래", "현금", "합계", "원"]
        ):
            continue
        if any(ch.isdigit() for ch in normalized):
            continue
        return normalized
    return None


def parse_receipt(text: str) -> Dict[str, object]:
    if not text:
        return {
            "date": None,
            "amount": None,
            "merchant": None,
            "pay_method": None,
            "approval_no": None,
        }

    lines = [line.strip() for line in text.splitlines()]
    blob = " ".join(lines)

    import re

    date_match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", blob)
    date_value = None
    if date_match:
        y, m, d = date_match.groups()
        date_value = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    amount_value = None
    amount_candidates = re.findall(
        r"(?:(?:KRW|₩|원)\s*)?([0-9]{1,3}(?:[,\s][0-9]{3})+|[0-9]+)(?=\s*(?:원|KRW|₩|$))",
        blob,
    )
    if amount_candidates:
        cleaned = amount_candidates[-1].replace(",", "").replace(" ", "")
        try:
            amount_value = int(cleaned)
        except ValueError:
            amount_value = None

    method_value = None
    for keyword in [
        "카드",
        "현금",
        "계좌이체",
        "간편결제",
        "신용",
        "체크",
        "카카오페이",
        "네이버페이",
    ]:
        if keyword in blob:
            method_value = keyword
            break

    approval_value = None
    approval_match = re.search(
        r"(승인.?번호|approval\s*no\.?)[^0-9a-zA-Z]*([0-9A-Z-]{4,})",
        blob,
        flags=re.IGNORECASE,
    )
    if approval_match:
        approval_value = approval_match.group(2)

    merchant_value = _pick_merchant(lines)

    return {
        "date": date_value,
        "amount": amount_value,
        "merchant": merchant_value,
        "pay_method": method_value,
        "approval_no": approval_value,
    }
