# moved from apps/common/services/openbanking.py

import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)


class OpenBankingServiceError(APIException):
    status_code = 502
    default_detail = "OpenBanking service error"


class OpenBankingTimeoutError(OpenBankingServiceError):
    status_code = 504
    default_detail = "OpenBanking request timed out"


class OpenBankingUnauthorizedError(OpenBankingServiceError):
    status_code = 401
    default_detail = "OpenBanking authorization failed"


def _get_base_url() -> str:
    base_url = getattr(settings, "OPENBANKING_BASE_URL", "")
    if not base_url:
        raise OpenBankingServiceError("OPENBANKING_BASE_URL is not configured")
    return base_url.rstrip("/")


def _get_access_token() -> str:
    token = getattr(settings, "OPENBANKING_ACCESS_TOKEN", "")
    if not token:
        raise OpenBankingServiceError("OPENBANKING_ACCESS_TOKEN is not configured")
    return token


def get_headers() -> Dict[str, str]:
    token = _get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _request(path: str, params: Dict[str, Any], *, timeout: Optional[int] = None) -> Dict[str, Any]:
    base_url = _get_base_url()
    url = f"{base_url}{path}"
    timeout_value = timeout or getattr(settings, "OPENBANKING_TIMEOUT", 10)

    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=timeout_value)
    except requests.Timeout as exc:
        logger.warning("OpenBanking timeout for %s", url, exc_info=exc)
        raise OpenBankingTimeoutError() from exc
    except requests.RequestException as exc:
        logger.exception("OpenBanking request failed: %s", exc)
        raise OpenBankingServiceError(str(exc)) from exc

    if response.status_code == 401:
        raise OpenBankingUnauthorizedError(response.text or OpenBankingUnauthorizedError.default_detail)
    if response.status_code >= 500:
        raise OpenBankingServiceError("OpenBanking upstream unavailable")
    if response.status_code >= 400:
        detail = response.text or "OpenBanking request failed"
        raise OpenBankingServiceError(detail)

    try:
        return response.json()
    except ValueError as exc:
        logger.exception("Invalid JSON from OpenBanking: %s", response.text[:200])
        raise OpenBankingServiceError("Invalid response from OpenBanking") from exc


def fetch_balance(fintech_use_num: str, *, timeout: Optional[int] = None) -> Dict[str, Any]:
    if not fintech_use_num:
        raise OpenBankingServiceError("fintech_use_num is required for balance lookup")
    params = {
        "fintech_use_num": fintech_use_num,
        # TODO: Include bank_tran_id, tran_dtime, etc. as per production spec.
    }
    return _request("/v2.0/account/balance", params=params, timeout=timeout)


def fetch_transactions(
    fintech_use_num: str,
    from_date: str,
    to_date: str,
    *,
    sort: str = "time",
    page: int = 1,
    size: int = 100,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    if not fintech_use_num:
        raise OpenBankingServiceError("fintech_use_num is required for transaction lookup")
    params: Dict[str, Any] = {
        "fintech_use_num": fintech_use_num,
        "from_date": from_date,
        "to_date": to_date,
        "sort": sort,
        "page": page,
        "size": size,
        # TODO: Production request should include bank_tran_id, inquiry_type, inquiry_base_dtime, etc.
    }
    return _request("/v2.0/account/transaction_list", params=params, timeout=timeout)
