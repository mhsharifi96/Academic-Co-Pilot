"""
Offline unit tests for the PDF download queue's pure decision logic
(app/services/download_service.py): DOI normalisation, tier/priority scheduling,
per-user jitter, the fair scheduler, and the retry state machine.

These need no DB and no provider — they exercise the pure functions the DB
wrappers and the worker delegate to. Quota enforcement / dedupe and the worker's
happy path are DB/network-bound and are covered by the manual integration
verification in the plan.
"""

import types
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.models.downloads import TIER_FAST, TIER_STANDARD
from app.services import download_service as svc


NOW = datetime(2026, 7, 11, 12, 0, 0, tzinfo=timezone.utc)


# --------------------------------------------------------------------------- #
# normalize_doi
# --------------------------------------------------------------------------- #
def test_normalize_doi_accepts_bare_and_url_forms():
    target = "10.1007/s10600-011-9854-z"
    assert svc.normalize_doi(target) == target
    assert svc.normalize_doi("  " + target + "  ") == target
    assert svc.normalize_doi("doi:" + target) == target
    assert svc.normalize_doi("https://doi.org/" + target) == target
    assert svc.normalize_doi("http://dx.doi.org/" + target) == target
    # Trailing sentence punctuation is stripped.
    assert svc.normalize_doi(target + ").") == target


def test_normalize_doi_rejects_non_doi():
    for bad in ["", "not a doi", "12.345/x", "https://example.com/x"]:
        with pytest.raises(svc.InvalidDOI):
            svc.normalize_doi(bad)


# --------------------------------------------------------------------------- #
# schedule_for  (tier / priority / timing)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n", [1, 2, 3])
def test_schedule_first_three_are_fast(n):
    s = svc.schedule_for(n, "user-a", NOW)
    assert s.service_tier == TIER_FAST
    assert s.priority_round == n
    assert s.available_at == NOW  # immediately available
    assert s.target_deadline == NOW + timedelta(minutes=settings.FAST_TARGET_MINUTES)


@pytest.mark.parametrize("n", [4, 5, 6, 7, 8, 9, 10])
def test_schedule_four_to_ten_are_standard_and_spread(n):
    s = svc.schedule_for(n, "user-a", NOW)
    assert s.service_tier == TIER_STANDARD
    assert s.priority_round is None
    assert s.target_deadline == NOW + timedelta(hours=settings.STANDARD_TARGET_HOURS)
    # Available in the future (spread across the 24h window), never before now.
    assert s.available_at >= NOW
    assert s.available_at <= NOW + timedelta(
        hours=settings.STANDARD_TARGET_HOURS + 1
    )


def test_standard_available_times_increase_with_request_number():
    # Ignoring jitter, later requests are scheduled later. Compare far-apart
    # requests so the monotonic base offset dominates the ± jitter.
    early = svc.schedule_for(4, "user-a", NOW).available_at
    late = svc.schedule_for(10, "user-a", NOW).available_at
    assert late > early


def test_jitter_differs_between_users_but_is_stable():
    j1 = svc.deterministic_jitter("user-a", 4, 15)
    j2 = svc.deterministic_jitter("user-b", 4, 15)
    assert j1 != j2  # different users don't collide on the same instant
    assert svc.deterministic_jitter("user-a", 4, 15) == j1  # stable/repeatable
    assert abs(j1.total_seconds()) <= 15 * 60  # within ± max


# --------------------------------------------------------------------------- #
# retry_plan  (state machine)
# --------------------------------------------------------------------------- #
def test_retry_plan_schedules_then_gives_up():
    # Attempt 1 failed → retry ~10 min later, attempt_count -> 1.
    p1 = svc.retry_plan(0, NOW)
    assert not p1.give_up
    assert p1.attempt_count == 1
    assert p1.available_at == NOW + timedelta(minutes=10)

    # Attempt 2 failed → retry ~20 min later, attempt_count -> 2.
    p2 = svc.retry_plan(1, NOW)
    assert not p2.give_up
    assert p2.attempt_count == 2
    assert p2.available_at == NOW + timedelta(minutes=20)

    # Attempt 3 failed → give up (PDF_NOT_FOUND), no further schedule.
    p3 = svc.retry_plan(2, NOW)
    assert p3.give_up
    assert p3.attempt_count == 3
    assert p3.available_at is None


def test_retry_delay_is_a_future_time_not_a_sleep():
    # The worker never sleeps for the delay; it reschedules via available_at.
    plan = svc.retry_plan(0, NOW)
    assert plan.available_at > NOW


# --------------------------------------------------------------------------- #
# pick_next  (fair scheduler)
# --------------------------------------------------------------------------- #
def _job(
    *,
    user_id,
    tier=TIER_FAST,
    priority_round=1,
    attempt_count=0,
    available_at=None,
    target_deadline=None,
    created_at=None,
):
    return types.SimpleNamespace(
        user_id=user_id,
        service_tier=tier,
        priority_round=priority_round,
        attempt_count=attempt_count,
        available_at=available_at or NOW,
        target_deadline=target_deadline or (NOW + timedelta(hours=1)),
        created_at=created_at or NOW,
    )


def test_pick_next_none_when_empty():
    assert svc.pick_next([], {}, 0, NOW) is None


def test_pick_next_rotates_users_within_a_round():
    # Two users each with a round-1 FAST job; the one that has been served less
    # goes first (prevents monopolisation). user-a has already had 2 processed.
    a = _job(user_id="a", priority_round=1, created_at=NOW)
    b = _job(user_id="b", priority_round=1, created_at=NOW + timedelta(seconds=1))
    served = {"a": 2, "b": 0}
    chosen = svc.pick_next([a, b], served, 0, NOW)
    assert chosen is b


def test_pick_next_prefers_lower_priority_round():
    r1 = _job(user_id="a", priority_round=1)
    r2 = _job(user_id="a", priority_round=2)
    assert svc.pick_next([r2, r1], {}, 0, NOW) is r1


def test_pick_next_deadline_override_jumps_urgent_fast():
    normal = _job(user_id="a", priority_round=1, target_deadline=NOW + timedelta(hours=1))
    urgent = _job(
        user_id="b",
        priority_round=3,  # lower priority round…
        target_deadline=NOW + timedelta(minutes=5),  # …but about to miss its target
    )
    chosen = svc.pick_next(
        [normal, urgent], {}, 0, NOW, deadline_urgent_minutes=10
    )
    assert chosen is urgent


def test_pick_next_anti_starvation_serves_standard_after_streak():
    fast = _job(user_id="a", tier=TIER_FAST, priority_round=1)
    std = _job(user_id="b", tier=TIER_STANDARD, priority_round=None)
    # Below threshold → FAST still wins.
    assert svc.pick_next([fast, std], {}, 4, NOW, fast_before_standard=5) is fast
    # At/above threshold → the STANDARD job is served to avoid starvation.
    assert svc.pick_next([fast, std], {}, 5, NOW, fast_before_standard=5) is std


def test_pick_next_retries_sort_behind_fresh_attempts():
    fresh = _job(user_id="a", priority_round=1, attempt_count=0)
    retried = _job(user_id="b", priority_round=1, attempt_count=2)
    # Same round, same served counts → the fresh first-attempt is picked.
    assert svc.pick_next([retried, fresh], {}, 0, NOW) is fresh


def test_pick_next_falls_back_to_standard_when_no_fast():
    s1 = _job(user_id="a", tier=TIER_STANDARD, priority_round=None, available_at=NOW)
    s2 = _job(
        user_id="b",
        tier=TIER_STANDARD,
        priority_round=None,
        available_at=NOW + timedelta(minutes=5),
    )
    assert svc.pick_next([s2, s1], {}, 0, NOW) is s1  # oldest available first
