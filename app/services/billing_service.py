"""
Per-user usage billing.

Each chat turn measures its token usage (see ``BaseAgent.run``); this module
converts that into a dollar cost, deducts it from ``User.balance``, and writes
an audit row to ``usage_records``. The authoritative remaining credit always
lives on ``User.balance`` — usage rows are just history for the admin view.

Billing is a no-op when ``settings.ENABLE_BILLING`` is False, so local dev and
the offline test suite are unaffected.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.auth import User, UsageRecord


def compute_cost(usage: dict) -> float:
    """Convert ``{"input_tokens", "output_tokens"}`` into a USD cost."""
    input_tokens = int((usage or {}).get("input_tokens", 0) or 0)
    output_tokens = int((usage or {}).get("output_tokens", 0) or 0)
    cost = (
        input_tokens / 1_000_000 * settings.COST_INPUT_PER_1M
        + output_tokens / 1_000_000 * settings.COST_OUTPUT_PER_1M
    )
    return round(cost, 6)


def has_sufficient_balance(user: User) -> bool:
    """
    Whether ``user`` may start a new turn. Billing-disabled or admin users are
    never blocked; everyone else needs balance above the configured floor.
    """
    if not settings.ENABLE_BILLING or user.is_admin:
        return True
    return user.balance > settings.MIN_BALANCE_TO_CHAT


async def charge_usage(
    db: AsyncSession,
    user: User,
    usage: dict,
    session_id: str | None = None,
) -> float:
    """
    Deduct the cost of ``usage`` from ``user.balance``, record an audit row, and
    commit. Returns the user's new balance. A no-op (returns current balance)
    when billing is disabled or there was no measurable usage.
    """
    if not settings.ENABLE_BILLING:
        return user.balance

    cost = compute_cost(usage)
    if cost <= 0:
        return user.balance

    # Deduct; allow the crossing turn to dip to/just below zero — the next turn
    # is what gets blocked by ``has_sufficient_balance``.
    user.balance = round(user.balance - cost, 6)
    db.add(
        UsageRecord(
            user_id=user.id,
            session_id=session_id,
            input_tokens=int((usage or {}).get("input_tokens", 0) or 0),
            output_tokens=int((usage or {}).get("output_tokens", 0) or 0),
            cost=cost,
        )
    )
    await db.commit()
    await db.refresh(user)
    return user.balance
