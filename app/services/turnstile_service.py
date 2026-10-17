"""
Cloudflare Turnstile (CAPTCHA) verification for the public auth forms.

The browser renders the widget with ``TURNSTILE_SITE_KEY`` and sends the token it
gets along with the login / sign-up request; the backend checks that token with
Cloudflare's siteverify API before touching the account. The browser never talks
to siteverify itself.

Enforced only when ``TURNSTILE_SECRET`` is set, so local dev and the offline
test suite run without it. Once enforced, it fails closed: a missing token, a
network error, a wrong action or an unlisted hostname are all refused.
"""

import logging
from typing import Iterable, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

# Widget actions, one per protected surface. The frontend passes the same value
# as the widget's ``action`` and siteverify echoes it back.
ACTION_LOGIN = "login"
ACTION_SIGNUP = "signup"

# Turnstile tokens are at most 2048 characters.
MAX_TOKEN_LENGTH = 2048


def turnstile_enabled() -> bool:
    return bool(settings.TURNSTILE_SECRET)


def expected_hostnames() -> set[str]:
    return {
        h.strip() for h in (settings.TURNSTILE_HOSTNAMES or "").split(",") if h.strip()
    }


def is_plausible_token(token: Optional[str]) -> bool:
    return isinstance(token, str) and 0 < len(token) <= MAX_TOKEN_LENGTH


def result_ok(result: dict, action: str, hostnames: Iterable[str]) -> bool:
    """Pure rule: does a siteverify response pass for this surface?"""
    allowed = set(hostnames)
    return (
        bool(allowed)
        and result.get("success") is True
        and result.get("action") == action
        and result.get("hostname") in allowed
    )


async def verify_token(
    token: Optional[str], action: str, remote_ip: Optional[str] = None
) -> bool:
    """Check ``token`` with siteverify. Returns False on any failure."""
    hostnames = expected_hostnames()
    if not is_plausible_token(token) or not hostnames:
        return False
    data = {"secret": settings.TURNSTILE_SECRET, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(SITEVERIFY_URL, data=data)
        resp.raise_for_status()
        result = resp.json()
    except Exception as exc:  # noqa: BLE001 — any failure means "not verified"
        logger.warning("Turnstile siteverify failed: %s", type(exc).__name__)
        return False
    ok = result_ok(result, action, hostnames)
    if not ok:
        logger.info(
            "Turnstile rejected: success=%s action=%s hostname=%s errors=%s",
            result.get("success"),
            result.get("action"),
            result.get("hostname"),
            result.get("error-codes"),
        )
    return ok
