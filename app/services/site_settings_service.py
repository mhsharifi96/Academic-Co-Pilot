"""
Read/write the singleton site-settings row, plus the pure rule that decides
whether a sign-up may proceed.

The row is created lazily on first read so no migration or seed step is needed:
a database that has never seen this table simply gets the defaults (open
registration), matching how the app behaved before the switch existed.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.site import SITE_SETTINGS_ID, SiteSetting


def registration_allowed(registration_open: bool, user_count: int) -> bool:
    """Pure rule: may a new account be created right now?

    Open registration always allows it. When closed we still let the *very
    first* account through — otherwise a fresh deployment whose switch was
    turned off (or shipped off) could never get its bootstrap admin, and there
    would be nobody able to turn it back on.
    """
    if registration_open:
        return True
    return user_count == 0


async def get_site_settings(db: AsyncSession) -> SiteSetting:
    """Return the settings row, inserting it with defaults if it's missing."""
    row = await db.get(SiteSetting, SITE_SETTINGS_ID)
    if row is None:
        row = SiteSetting(id=SITE_SETTINGS_ID)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return row


async def set_registration_open(db: AsyncSession, value: bool) -> SiteSetting:
    """Flip the sign-up switch and persist it."""
    row = await get_site_settings(db)
    row.registration_open = bool(value)
    await db.commit()
    await db.refresh(row)
    return row
