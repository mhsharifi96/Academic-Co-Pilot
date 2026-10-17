"""
Offline unit tests for the balance top-up rules
(app/services/topup_service.py). The DB-bound endpoints are covered by manual
verification; the amounts, networks, status transitions and email text are pure.
"""

from app.models.billing import (
    STATUS_AWAITING_PAYMENT,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PAID,
    STATUS_PENDING,
    STATUS_REJECTED,
    TopUpRequest,
)
from app.services import topup_service as svc


def test_only_fixed_amounts_are_allowed():
    for amount in (5, 10, 20, 30):
        assert svc.is_valid_amount(amount)
        assert svc.is_valid_amount(float(amount))
    for amount in (0, 1, 7.5, 15, 50, -5):
        assert not svc.is_valid_amount(amount)


def test_networks():
    assert svc.is_valid_network("USDT_TRC20")
    assert svc.is_valid_network("BTC")
    assert not svc.is_valid_network("DOGE")
    assert not svc.is_valid_network("")


def test_happy_path_transitions():
    assert svc.can_transition(STATUS_PENDING, STATUS_AWAITING_PAYMENT)
    assert svc.can_transition(STATUS_AWAITING_PAYMENT, STATUS_PAID)
    assert svc.can_transition(STATUS_PAID, STATUS_COMPLETED)


def test_user_cannot_mark_paid_before_payment_details_are_sent():
    assert not svc.can_transition(STATUS_PENDING, STATUS_PAID)


def test_admin_may_resend_email_and_confirm_without_user_report():
    assert svc.can_transition(STATUS_AWAITING_PAYMENT, STATUS_AWAITING_PAYMENT)
    assert svc.can_transition(STATUS_AWAITING_PAYMENT, STATUS_COMPLETED)


def test_user_cannot_cancel_after_reporting_payment():
    assert svc.can_transition(STATUS_PENDING, STATUS_CANCELLED)
    assert svc.can_transition(STATUS_AWAITING_PAYMENT, STATUS_CANCELLED)
    assert not svc.can_transition(STATUS_PAID, STATUS_CANCELLED)


def test_final_statuses_are_terminal():
    # A completed request must never be confirmed (and credited) twice.
    for final in (STATUS_COMPLETED, STATUS_REJECTED, STATUS_CANCELLED):
        for target in (
            STATUS_PENDING,
            STATUS_AWAITING_PAYMENT,
            STATUS_PAID,
            STATUS_COMPLETED,
            STATUS_REJECTED,
            STATUS_CANCELLED,
        ):
            assert not svc.can_transition(final, target)


def test_payment_email_names_amount_network_and_address():
    req = TopUpRequest(
        id="req-1",
        user_id="u1",
        email="someone@example.com",
        amount=20.0,
        network="USDT_TRC20",
        wallet_address="TXYZabc1234567890",
        admin_note="Fee is on you.",
    )
    subject, body = svc.payment_email(req)
    assert "$20" in subject
    assert "TXYZabc1234567890" in body
    assert "TRC-20" in body
    assert "Fee is on you." in body
    assert "req-1" in body
    link = svc.mailto_link(req)
    assert link.startswith("mailto:someone%40example.com?subject=")
