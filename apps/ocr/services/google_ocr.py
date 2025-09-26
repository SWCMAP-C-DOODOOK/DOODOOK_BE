import json
import re
from typing import Dict

import requests

from apps.ocr.services import OCRServiceError

VISION_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"


def extract_text_base64(b64: str, *, api_key: str, timeout: int = 8) -> Dict[str, object]:
    if not api_key:
        raise OCRServiceError("Google Vision API key not configured", status_code=500)

    url = f"{VISION_ENDPOINT}?key={api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": b64},
                "features": [{"type": "TEXT_DETECTION"}],
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=timeout)
    except requests.Timeout as exc:
        raise OCRServiceError("Google Vision request timed out", status_code=504) from exc
    except requests.RequestException as exc:
        raise OCRServiceError(f"Google Vision request failed: {exc}") from exc

    if response.status_code >= 500:
        raise OCRServiceError("Google Vision service unavailable", status_code=502)
    if response.status_code >= 400:
        raise OCRServiceError(response.text or "Google Vision request rejected", status_code=400)

    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        raise OCRServiceError("Invalid response from Google Vision", status_code=502) from exc

    text = ""
    try:
        responses = data.get("responses", [])
        if responses:
            text = responses[0].get("fullTextAnnotation", {}).get("text", "")
    except AttributeError:
        text = ""

    return {"text": text or "", "raw": data}


def _pick_merchant(lines):
    for line in lines:
        normalized = line.strip()
        if not normalized:
            continue
        lower = normalized.lower()
        if any(keyword in lower for keyword in ["승인", "금액", "카드", "거래", "현금", "합계", "원"]):
            continue
        if re.search(r"\d", normalized):
            continue
        return normalized
    return None


def parse_receipt(text: str) -> Dict[str, object]:
    if not text:
        return {"date": None, "amount": None, "merchant": None, "pay_method": None, "approval_no": None}

    lines = [line.strip() for line in text.splitlines()]
    blob = " ".join(lines)

    date_match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", blob)
    date_value = None
    if date_match:
        y, m, d = date_match.groups()
        date_value = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

    amount_value = None
    amount_candidates = re.findall(r"(?:(?:KRW|₩|원)\s*)?([0-9]{1,3}(?:[,\s][0-9]{3})+|[0-9]+)(?=\s*(?:원|KRW|₩|$))", blob)
    if amount_candidates:
        cleaned = amount_candidates[-1].replace(",", "").replace(" ", "")
        try:
            amount_value = int(cleaned)
        except ValueError:
            amount_value = None

    method_value = None
    for keyword in ["카드", "현금", "계좌이체", "간편결제", "신용", "체크", "카카오페이", "네이버페이"]:
        if keyword in blob:
            method_value = keyword
            break

    approval_value = None
    approval_match = re.search(r"(승인.?번호|approval\s*no\.?)[^0-9a-zA-Z]*([0-9A-Z-]{4,})", blob, flags=re.IGNORECASE)
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
