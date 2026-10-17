"""
ORM model for balance top-up requests paid in cryptocurrency.

The flow is deliberately manual — there is no payment gateway:

1. The user asks for a top-up (amount + crypto network + contact email)
   → ``pending``.
2. An admin emails them the wallet address for that network
   → ``awaiting_payment``.
3. The user sends the crypto and reports it, optionally with the tx hash
   → ``paid``.
4. The admin checks the transfer and confirms, which credits ``User.balance``
   → ``completed``.

A request can also end as ``rejected`` (by the admin) or ``cancelled`` (by the
user). Transition rules live in ``app/services/topup_service.py``.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


STATUS_PENDING = "pending"
STATUS_AWAITING_PAYMENT = "awaiting_payment"
STATUS_PAID = "paid"
STATUS_COMPLETED = "completed"
STATUS_REJECTED = "rejected"
STATUS_CANCELLED = "cancelled"

# Statuses that still need someone to act; a user may hold only one at a time.
OPEN_STATUSES = (STATUS_PENDING, STATUS_AWAITING_PAYMENT, STATUS_PAID)


class TopUpRequest(Base):
    __tablename__ = "topup_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Where the admin should send payment instructions. Defaults to the account
    # email in the UI but the user may give another address.
    email: Mapped[str] = mapped_column(String, nullable=False)
    # USD to credit once paid; one of TOPUP_AMOUNTS.
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    # Key into CRYPTO_NETWORKS, e.g. "USDT_TRC20".
    network: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, default=STATUS_PENDING, index=True, nullable=False
    )
    # Set by the admin when sending payment instructions.
    wallet_address: Mapped[str] = mapped_column(String, nullable=True)
    admin_note: Mapped[str] = mapped_column(Text, nullable=True)
    # Reported by the user once they have paid.
    tx_hash: Mapped[str] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
