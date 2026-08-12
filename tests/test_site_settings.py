"""
Offline unit tests for the site-settings decision rule
(app/services/site_settings_service.py::registration_allowed).

The DB-bound parts (lazy insert of the singleton row, the admin PATCH) need a
database and are covered by manual verification; the rule that decides whether a
sign-up may proceed is pure and belongs here.
"""

from app.services.site_settings_service import registration_allowed


def test_open_registration_allows_anyone():
    assert registration_allowed(True, user_count=0) is True
    assert registration_allowed(True, user_count=57) is True


def test_closed_registration_refuses_new_users():
    assert registration_allowed(False, user_count=1) is False
    assert registration_allowed(False, user_count=57) is False


def test_closed_registration_still_allows_the_bootstrap_admin():
    # An empty deployment must be able to create its first (admin) account even
    # if the switch is off, or nobody could ever turn it back on.
    assert registration_allowed(False, user_count=0) is True
