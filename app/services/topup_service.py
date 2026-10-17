"""
Balance top-up requests: the pure rules (amounts, networks, which status may
follow which) plus the payment-instructions email.

The rules are pure so they can be unit-tested offline (``tests/test_topup.py``);
the endpoints in ``app/api/v1/endpoints/billing.py`` only load rows, call
``can_transition`` and persist.
"""

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional
from urllib.parse import quote

from app.core.config import settings
from app.models.billing import (
    STATUS_AWAITING_PAYMENT,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_PAID,
    STATUS_PENDING,
    STATUS_REJECTED,
    TopUpRequest,
)

logger = logging.getLogger(__name__)

# The only amounts a user can request, in USD.
TOPUP_AMOUNTS = (5, 10, 20, 30)

# Network key -> human label. The key is what the API accepts and stores.
CRYPTO_NETWORKS = {
    "USDT_TRC20": "USDT (Tron · TRC-20)",
    "USDT_ERC20": "USDT (Ethereum · ERC-20)",
    "USDT_BEP20": "USDT (BNB Smart Chain · BEP-20)",
    "USDT_TON": "USDT (TON)",
    "BTC": "Bitcoin (BTC)",
    "ETH": "Ethereum (ETH)",
    "TRX": "Tron (TRX)",
    "TON": "Toncoin (TON)",
}

# status -> statuses it may move to. Anything absent is terminal.
_TRANSITIONS = {
    STATUS_PENDING: {STATUS_AWAITING_PAYMENT, STATUS_REJECTED, STATUS_CANCELLED},
    STATUS_AWAITING_PAYMENT: {
        # Re-sending the email (e.g. a corrected address) keeps the status.
        STATUS_AWAITING_PAYMENT,
        STATUS_PAID,
        # The admin may confirm a payment they can already see on-chain even if
        # the user never pressed "I've paid".
        STATUS_COMPLETED,
        STATUS_REJECTED,
        STATUS_CANCELLED,
    },
    STATUS_PAID: {STATUS_COMPLETED, STATUS_REJECTED},
}


def is_valid_amount(amount: float) -> bool:
    return amount in TOPUP_AMOUNTS


def is_valid_network(network: str) -> bool:
    return network in CRYPTO_NETWORKS


def can_transition(current: str, target: str) -> bool:
    """Pure rule: may a request in ``current`` move to ``target``?"""
    return target in _TRANSITIONS.get(current, set())


def payment_email(req: TopUpRequest) -> tuple[str, str]:
    """Subject and plain-text body of the payment-instructions email."""
    network = CRYPTO_NETWORKS.get(req.network, req.network)
    subject = f"Academic Co-Pilot — payment details for your ${req.amount:g} top-up"
    lines = [
        "Hello,",
        "",
        f"Thanks for your request to add ${req.amount:g} to your Academic Co-Pilot balance.",
        "",
        f"Please send the equivalent of ${req.amount:g} in {network} to this address:",
        "",
        f"    {req.wallet_address}",
        "",
        "Only send on the network named above — funds sent on another network "
        "may be lost.",
    ]
    if req.admin_note:
        lines += ["", req.admin_note]
    lines += [
        "",
        "Once you have paid, open the app, click your balance and press "
        "\"I've paid\" (adding the transaction hash helps us find it quickly). "
        "Your balance is credited as soon as we confirm the transfer.",
        "",
        f"Request ID: {req.id}",
    ]
    return subject, "\n".join(lines)


def mailto_link(req: TopUpRequest) -> str:
    """A ``mailto:`` URL with the same message, for when SMTP isn't configured."""
    subject, body = payment_email(req)
    return f"mailto:{quote(req.email)}?subject={quote(subject)}&body={quote(body)}"


def smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and (settings.SMTP_FROM or settings.SMTP_USER))


def _send_sync(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    if settings.SMTP_USE_SSL:
        server: smtplib.SMTP = smtplib.SMTP_SSL(
            settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=20
        )
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20)
    with server:
        if settings.SMTP_USE_TLS and not settings.SMTP_USE_SSL:
            server.starttls(context=context)
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_payment_email(req: TopUpRequest) -> Optional[str]:
    """Send the payment instructions. Returns an error message, or None on success.

    Never raises: a mail failure must not lose the admin's status change, the UI
    just offers the mailto: fallback instead.
    """
    if not smtp_configured():
        return "SMTP is not configured."
    subject, body = payment_email(req)
    try:
        await asyncio.to_thread(_send_sync, req.email, subject, body)
    except Exception as exc:  # noqa: BLE001 — report any SMTP failure to the admin
        logger.warning("Top-up email to %s failed: %s", req.email, exc)
        return f"Email could not be sent: {exc}"
    return None
