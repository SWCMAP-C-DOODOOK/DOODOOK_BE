import json

import requests


TOKEN_URL = "https://kauth.kakao.com/oauth/token"
USER_ME_URL = "https://kapi.kakao.com/v2/user/me"


class KakaoServiceError(Exception):
    pass


def exchange_code_for_token(
    code: str,
    *,
    client_id: str,
    redirect_uri: str,
    timeout: int = 10,
) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code": code,
    }

    try:
        response = requests.post(
            TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise KakaoServiceError("Kakao token exchange timed out") from exc
    except requests.HTTPError as exc:
        detail = _extract_detail(response)
        raise KakaoServiceError(f"Kakao token exchange failed: {detail}") from exc
    except requests.RequestException as exc:
        raise KakaoServiceError(f"Kakao token exchange error: {exc}") from exc


def fetch_user_me(access_token: str, *, timeout: int = 10) -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    try:
        response = requests.get(USER_ME_URL, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.Timeout as exc:
        raise KakaoServiceError("Kakao user info request timed out") from exc
    except requests.HTTPError as exc:
        detail = _extract_detail(response)
        raise KakaoServiceError(f"Kakao user info request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise KakaoServiceError(f"Kakao user info error: {exc}") from exc


def _extract_detail(response: requests.Response) -> str:
    try:
        return json.dumps(response.json())
    except ValueError:
        return response.text or ""
