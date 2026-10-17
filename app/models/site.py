"""
ORM model for site-wide settings an admin can flip at runtime.

A single row (``id == SITE_SETTINGS_ID``) holds switches that must outlive a
process restart and apply to everyone — unlike ``app/core/config.py``, which is
read from the environment at import time and needs a redeploy to change.

First switch: ``registration_open``. When false, ``POST /auth/register`` is
refused (403) and the sign-up form is hidden in the UI; logging in is
unaffected. Business logic lives in ``app/services/site_settings_service.py``.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# The settings row is a singleton: one fixed primary key, upserted on demand.
SITE_SETTINGS_ID = "global"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SiteSetting(Base):
    __tablename__ = "site_settings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=SITE_SETTINGS_ID)
    # Whether new visitors may create an account. Default open, so an existing
    # deployment behaves exactly as it did before this table existed.
    registration_open: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
