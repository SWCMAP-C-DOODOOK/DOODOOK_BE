# moved from apps/common/services/openbanking.py
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from django.conf import settings
from django.core.cache import cache
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
SESSION: Optional[Session] = None

TOKEN_CACHE_KEY = "openbanking:token"
TOKEN_LOCK_KEY = "openbanking:token:lock"
TOKEN_LOCK_TIMEOUT = 10
SANDBOX_TOKEN = "SANDBOX-DEMO-TOKEN"


class OpenBankingServiceError(APIException):
    status_code = 502
    default_detail = "OpenBanking service error"


class OpenBankingTimeoutError(OpenBankingServiceError):
    status_code = 504
    default_detail = "OpenBanking request timed out"


class OpenBankingUnauthorizedError(OpenBankingServiceError):
    status_code = 401
    default_detail = "OpenBanking authorization failed"


class OpenBankingRateLimitError(OpenBankingServiceError):
    status_code = 429
    default_detail = "OpenBanking rate limit exceeded"


class OpenBankingUpstreamError(OpenBankingServiceError):
    status_code = 502
    default_detail = "OpenBanking upstream unavailable"


def mask_fintech(fintech_use_num: str) -> str:
    if not fintech_use_num:
        return ""
    masked_len = max(len(fintech_use_num) - 4, 0)
    return ("*" * masked_len) + fintech_use_num[-4:]


def get_config() -> Dict[str, Any]:
    base_url = getattr(settings, "OPENBANKING_BASE_URL", "https://testapi.openbanking.or.kr").rstrip("/")
    token_path = getattr(settings, "OPENBANKING_TOKEN_PATH", "/oauth/2.0/token") or "/oauth/2.0/token"
    if not token_path.startswith("/"):
        token_path = f"/{token_path}"

    timeout = int(getattr(settings, "OPENBANKING_TIMEOUT", 6) or 6)
    timeout = max(timeout, 4)
    retries = int(getattr(settings, "OPENBANKING_RETRIES", 2) or 0)
    rate_limit = int(getattr(settings, "OPENBANKING_RL", 5) or 0)

    return {
        "base_url": base_url,
        "token_path": token_path,
        "token_url": f"{base_url}{token_path}",
        "timeout": timeout,
        "retries": max(retries, 0),
        "rate_limit": max(rate_limit, 0),
        "sandbox": getattr(settings, "OPENBANKING_SANDBOX", True),
        "scope": getattr(settings, "OPENBANKING_SCOPE", "oob") or "oob",
        "client_id": getattr(settings, "OPENBANKING_CLIENT_ID", ""),
        "client_secret": getattr(settings, "OPENBANKING_CLIENT_SECRET", ""),
        "debug_token": getattr(settings, "OPENBANKING_ACCESS_TOKEN", ""),
    }


def _load_fixture(name: str) -> Dict[str, Any]:
    fixture_path = FIXTURE_DIR / name
    if not fixture_path.exists():
        raise OpenBankingServiceError(f"Fixture {name} is missing for sandbox mode")
    with fixture_path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _enforce_rate_limit(fintech_use_num: str, limit: int) -> None:
    if limit <= 0:
        return
    bucket_key = f"openbanking:rl:{fintech_use_num}:{int(time.time())}"
    added = cache.add(bucket_key, 1, timeout=1)
    if added:
        return
    try:
        current = cache.incr(bucket_key)
    except ValueError:
        cache.set(bucket_key, 1, timeout=1)
        current = 1
    if current > limit:
        logger.warning("OpenBanking rate limit exceeded for %s", mask_fintech(fintech_use_num))
        raise OpenBankingRateLimitError(OpenBankingRateLimitError.default_detail)


def _build_session(retries: int) -> Session:
    global SESSION
    if SESSION is not None:
        return SESSION

    retry_strategy = Retry(
        total=retries,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "POST"),
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = Session()
    session.headers.update({"User-Agent": "DOODOOK-OpenBanking-Demo/1.0"})
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    SESSION = session
    return SESSION


def _issue_access_token(config: Dict[str, Any]) -> Tuple[str, int]:
    client_id = config.get("client_id") or ""
    client_secret = config.get("client_secret") or ""
    if not client_id or not client_secret:
        raise OpenBankingServiceError("OPENBANKING_CLIENT_ID/SECRET are not configured")

    session = _build_session(config["retries"])
    data = {
        "grant_type": "client_credentials",
        "scope": config.get("scope", "oob"),
        "client_id": client_id,
        "client_secret": client_secret,
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    try:
        response = session.post(
            config["token_url"],
            data=data,
            headers=headers,
            timeout=(2, config["timeout"]),
        )
    except requests.Timeout as exc:
        logger.warning("OpenBanking token request timeout")
        raise OpenBankingTimeoutError() from exc
    except requests.RequestException as exc:
        logger.exception("OpenBanking token request error: %s", exc)
        raise OpenBankingServiceError(str(exc)) from exc

    if response.status_code == 401:
        raise OpenBankingUnauthorizedError(response.text or OpenBankingUnauthorizedError.default_detail)
    if response.status_code >= 500:
        raise OpenBankingUpstreamError(response.text or OpenBankingUpstreamError.default_detail)
    if response.status_code >= 400:
        raise OpenBankingServiceError(response.text or "OpenBanking token request failed")

    try:
        payload = response.json()
    except ValueError as exc:
        logger.exception("Invalid token JSON response: %s", response.text[:200])
        raise OpenBankingServiceError("Invalid token response from OpenBanking") from exc

    token = payload.get("access_token")
    expires_in = payload.get("expires_in")
    if not token or not expires_in:
        raise OpenBankingServiceError("Token response is missing access_token or expires_in")

    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError) as exc:
        raise OpenBankingServiceError("expires_in must be an integer") from exc

    return token, expires_in


def get_access_token(force_refresh: bool = False) -> str:
    config = get_config()

    if config["sandbox"]:
        debug_token = config.get("debug_token")
        return debug_token or SANDBOX_TOKEN

    debug_token = config.get("debug_token")
    if debug_token and not force_refresh:
        return debug_token

    if not force_refresh:
        cached = cache.get(TOKEN_CACHE_KEY)
        if cached:
            return cached

    attempts = 0
    acquired = False
    while attempts < 3:
        acquired = cache.add(TOKEN_LOCK_KEY, 1, timeout=TOKEN_LOCK_TIMEOUT)
        if acquired:
            break
        time.sleep(0.3)
        token = cache.get(TOKEN_CACHE_KEY)
        if token:
            return token
        attempts += 1

    if not acquired:
        raise OpenBankingServiceError("Unable to acquire OpenBanking token lock")

    try:
        if not force_refresh:
            cached = cache.get(TOKEN_CACHE_KEY)
            if cached:
                return cached

        token, expires_in = _issue_access_token(config)
        ttl = max(expires_in - 60, 60)
        cache.set(TOKEN_CACHE_KEY, token, timeout=ttl)
        logger.info("Issued OpenBanking access token (ttl=%s)", ttl)
        return token
    finally:
        cache.delete(TOKEN_LOCK_KEY)


def _headers(token: str) -> Dict[str, str]:
    request_id = uuid.uuid4().hex
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Request-ID": request_id,
        "api_tran_id": request_id[:20],
    }


def _http(path: str, params: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    session = _build_session(config["retries"])
    token = get_access_token()
    url = f"{config['base_url']}{path}"
    try:
        response = session.get(
            url,
            headers=_headers(token),
            params=params,
            timeout=(2, config["timeout"]),
        )
    except requests.Timeout as exc:
        logger.warning("OpenBanking timeout fintech=%s", mask_fintech(params.get("fintech_use_num", "")))
        raise OpenBankingTimeoutError() from exc
    except requests.RequestException as exc:
        logger.exception("OpenBanking request error fintech=%s", mask_fintech(params.get("fintech_use_num", "")))
        raise OpenBankingServiceError(str(exc)) from exc

    if response.status_code == 401:
        raise OpenBankingUnauthorizedError(response.text or OpenBankingUnauthorizedError.default_detail)
    if response.status_code == 429:
        raise OpenBankingRateLimitError(response.text or OpenBankingRateLimitError.default_detail)
    if response.status_code >= 500:
        raise OpenBankingUpstreamError(response.text or OpenBankingUpstreamError.default_detail)
    if response.status_code >= 400:
        raise OpenBankingServiceError(response.text or "OpenBanking request failed")

    try:
        return response.json()
    except ValueError as exc:
        logger.exception("Invalid JSON from OpenBanking fintech=%s", mask_fintech(params.get("fintech_use_num", "")))
        raise OpenBankingServiceError("Invalid response from OpenBanking") from exc


def _normalize_balance(fintech_use_num: str, data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "fintech_use_num": fintech_use_num,
        "account": {"alias": None, "bank_name": None},
        "balance": data.get("balance_amt") or data.get("balance") or data.get("balanceAmount"),
        "currency": data.get("currency") or data.get("currency_code", "KRW"),
        "raw": data,
    }


def _normalize_transaction_items(items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    ordered: List[Dict[str, Any]] = []
    for item in items:
        tran_id = (
            item.get("tran_id")
            or item.get("tranId")
            or item.get("bank_tran_id")
            or uuid.uuid4().hex
        )
        normalized = {
            "tran_id": tran_id,
            "time": item.get("time") or item.get("tran_time") or item.get("tranDtime"),
            "summary": item.get("summary") or item.get("description") or item.get("print_content"),
            "amount": item.get("amount") or item.get("tran_amt") or item.get("tranAmount"),
            "balance": item.get("balance") or item.get("balance_amt") or item.get("after_balance_amt"),
            "inout": item.get("inout") or item.get("inout_type") or item.get("tran_type"),
        }
        if tran_id in seen:
            continue
        seen[tran_id] = normalized
        ordered.append(normalized)
    return ordered


def _normalize_transactions(
    fintech_use_num: str,
    data: Dict[str, Any],
    *,
    from_date: str,
    to_date: str,
    sort: str,
    page: int,
    size: int,
) -> Dict[str, Any]:
    items = data.get("list") or data.get("res_list") or data.get("resList") or []
    normalized_list = _normalize_transaction_items(items)
    return {
        "fintech_use_num": fintech_use_num,
        "list": normalized_list,
        "range": {"from": from_date, "to": to_date},
        "sort": sort,
        "page": page,
        "size": size,
        "raw": data,
    }


def fetch_balance(fintech_use_num: str) -> Dict[str, Any]:
    fintech = fintech_use_num.strip()
    if not fintech:
        raise OpenBankingServiceError("fintech_use_num is required for balance lookup")

    config = get_config()
    _enforce_rate_limit(fintech, config["rate_limit"])
    logger.info("OpenBanking balance fintech=%s sandbox=%s", mask_fintech(fintech), config["sandbox"])

    if config["sandbox"]:
        stub = _load_fixture("demo_balance.json")
        stub.setdefault("balance_amt", stub.get("balance"))
        return _normalize_balance(fintech, stub)

    params = {
        "fintech_use_num": fintech,
    }
    response = _http("/v2.0/account/balance", params, config)
    return _normalize_balance(fintech, response)


def fetch_transactions(
    fintech_use_num: str,
    from_date: str,
    to_date: str,
    *,
    sort: str = "time",
    page: int = 1,
    size: int = 100,
) -> Dict[str, Any]:
    fintech = fintech_use_num.strip()
    if not fintech:
        raise OpenBankingServiceError("fintech_use_num is required for transaction lookup")

    config = get_config()
    _enforce_rate_limit(fintech, config["rate_limit"])
    logger.info("OpenBanking transactions fintech=%s sandbox=%s", mask_fintech(fintech), config["sandbox"])

    if config["sandbox"]:
        stub = _load_fixture("demo_transactions.json")
        stub_list = stub.get("list", [])
        filtered: List[Dict[str, Any]] = []
        for item in stub_list:
            item_time = item.get("time") or item.get("tran_time")
            if not item_time:
                filtered.append(item)
                continue
            date_part = item_time.split("T")[0]
            if from_date <= date_part <= to_date:
                filtered.append(item)
        stub_copy = dict(stub)
        stub_copy["list"] = filtered
        return _normalize_transactions(
            fintech,
            stub_copy,
            from_date=from_date,
            to_date=to_date,
            sort=sort,
            page=page,
            size=size,
        )

    params = {
        "fintech_use_num": fintech,
        "from_date": from_date.replace("-", ""),
        "to_date": to_date.replace("-", ""),
        "sort": sort,
        "page": page,
        "size": size,
    }
    response = _http("/v2.0/account/transaction_list", params, config)
    return _normalize_transactions(
        fintech,
        response,
        from_date=from_date,
        to_date=to_date,
        sort=sort,
        page=page,
        size=size,
    )
