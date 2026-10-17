"""
Offline unit tests for the Turnstile (CAPTCHA) rules in
app/services/turnstile_service.py. The siteverify HTTP call itself is not hit.
"""

import asyncio

from app.services import turnstile_service as svc

HOSTS = {"app.example.com"}
GOOD = {"success": True, "action": "login", "hostname": "app.example.com"}


def test_valid_result_passes():
    assert svc.result_ok(GOOD, "login", HOSTS)


def test_unsuccessful_result_fails():
    assert not svc.result_ok({**GOOD, "success": False}, "login", HOSTS)
    # Truthy-but-not-True must not pass.
    assert not svc.result_ok({**GOOD, "success": "true"}, "login", HOSTS)


def test_token_for_another_surface_fails():
    # A login token must not unlock sign-up, and vice versa.
    assert not svc.result_ok(GOOD, "signup", HOSTS)


def test_unlisted_hostname_fails():
    assert not svc.result_ok({**GOOD, "hostname": "evil.example.com"}, "login", HOSTS)


def test_empty_allowlist_fails_closed():
    assert not svc.result_ok(GOOD, "login", set())


def test_token_shape():
    assert svc.is_plausible_token("abc")
    assert not svc.is_plausible_token("")
    assert not svc.is_plausible_token(None)
    assert not svc.is_plausible_token("x" * 2049)


def test_missing_token_is_refused_without_a_network_call():
    assert asyncio.run(svc.verify_token(None, "login")) is False
