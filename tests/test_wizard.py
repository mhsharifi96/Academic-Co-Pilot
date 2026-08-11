"""
Offline unit tests for the wizard feature's pure decision logic
(app/services/wizard_service.py): the step state machine, step ordering and
reordering, locale resolution/fallback, slugification, and the per-turn guidance
text injected into the agent's context.

These need no DB and no LLM. The DB-bound behaviour (the start-or-resume lookup,
the ``SELECT ... FOR UPDATE`` on the turn path, and the cascade deletes) is
covered by the manual integration verification in the plan.
"""

import types
from datetime import datetime, timedelta, timezone

import pytest

from app.models.wizard import STATUS_ACTIVE, STATUS_COMPLETED
from app.services import wizard_service as svc


T0 = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


def step(step_id, position, created_at=T0, max_messages=None):
    """A duck-typed stand-in for a WizardStep row."""
    return types.SimpleNamespace(
        id=step_id, position=position, created_at=created_at, max_messages=max_messages
    )


def wizard_row(**fields):
    return types.SimpleNamespace(**fields)


# --------------------------------------------------------------------------- #
# apply_turn — the step state machine
# --------------------------------------------------------------------------- #
def test_apply_turn_under_cap_stays_on_step():
    out = svc.apply_turn(current_count=2, max_messages=5, next_step_id="s2")
    assert out.step_message_count == 3
    assert out.new_current_step_id is None
    assert out.status == STATUS_ACTIVE
    assert not out.advanced and not out.completed


def test_apply_turn_reaching_cap_advances_and_resets_counter():
    out = svc.apply_turn(current_count=4, max_messages=5, next_step_id="s2")
    assert out.advanced is True
    assert out.completed is False
    assert out.new_current_step_id == "s2"
    assert out.step_message_count == 0
    assert out.status == STATUS_ACTIVE


def test_apply_turn_reaching_cap_on_last_step_completes_the_run():
    out = svc.apply_turn(current_count=4, max_messages=5, next_step_id=None)
    assert out.completed is True
    assert out.advanced is False
    assert out.status == STATUS_COMPLETED
    assert out.new_current_step_id is None
    # The final turn is still counted, so the UI can show 5 of 5.
    assert out.step_message_count == 5


def test_apply_turn_cap_of_one_advances_on_the_first_turn():
    out = svc.apply_turn(current_count=0, max_messages=1, next_step_id="s2")
    assert out.advanced is True
    assert out.new_current_step_id == "s2"
    assert out.step_message_count == 0


def test_apply_turn_terminates_when_admin_lowered_the_cap_mid_step():
    # The counter is already past the cap; `>=` must still terminate rather than
    # loop forever waiting for an exact match.
    out = svc.apply_turn(current_count=9, max_messages=3, next_step_id="s2")
    assert out.advanced is True
    assert out.step_message_count == 0


@pytest.mark.parametrize("cap", [None, 0, -1])
def test_apply_turn_treats_non_positive_cap_as_unlimited(cap):
    out = svc.apply_turn(current_count=42, max_messages=cap, next_step_id="s2")
    assert out.step_message_count == 43
    assert out.new_current_step_id is None
    assert out.status == STATUS_ACTIVE
    assert not out.advanced and not out.completed


@pytest.mark.parametrize("cap", [None, 0, -1])
def test_apply_turn_uncapped_last_step_never_completes(cap):
    out = svc.apply_turn(current_count=99, max_messages=cap, next_step_id=None)
    assert out.completed is False
    assert out.status == STATUS_ACTIVE


# --------------------------------------------------------------------------- #
# apply_advance — the explicit "Finish step" action
# --------------------------------------------------------------------------- #
def test_apply_advance_moves_to_the_next_step_and_resets_the_counter():
    out = svc.apply_advance(next_step_id="s2")
    assert out.advanced is True
    assert out.completed is False
    assert out.new_current_step_id == "s2"
    assert out.step_message_count == 0
    assert out.status == STATUS_ACTIVE


def test_apply_advance_on_the_last_step_completes_the_run():
    out = svc.apply_advance(next_step_id=None)
    assert out.completed is True
    assert out.advanced is False
    assert out.status == STATUS_COMPLETED


def test_apply_advance_ignores_the_message_cap():
    # The whole point: an uncapped step is finishable, and a capped step can be
    # left early without spending its remaining turns.
    assert svc.apply_advance(next_step_id="s2").advanced is True


# --------------------------------------------------------------------------- #
# extract_completion_signal — the agent's "this step is done" marker
# --------------------------------------------------------------------------- #
def test_completion_signal_absent_leaves_text_untouched():
    text = "Here is your PICO question.\n\nWhat would you like to refine?"
    assert svc.extract_completion_signal(text) == (text, False)


def test_completion_signal_is_detected_and_stripped():
    clean, done = svc.extract_completion_signal(
        "Your question looks solid now.\n\n[[STEP_COMPLETE]]"
    )
    assert done is True
    assert clean == "Your question looks solid now."
    assert "STEP_COMPLETE" not in clean


@pytest.mark.parametrize(
    "marker",
    [
        "[[STEP_COMPLETE]]",
        "[STEP_COMPLETE]",
        "[[step_complete]]",
        "[[ STEP_COMPLETE ]]",
        "[[STEP COMPLETE]]",
        "[[STEP-COMPLETE]]",
        "**[[STEP_COMPLETE]]**",
        "`[[STEP_COMPLETE]]`",
    ],
)
def test_completion_signal_tolerates_the_shapes_models_emit(marker):
    clean, done = svc.extract_completion_signal(f"All done here.\n\n{marker}")
    assert done is True
    assert clean == "All done here."


def test_completion_signal_stripped_mid_text_without_leaving_holes():
    clean, done = svc.extract_completion_signal(
        "First line.\n\n[[STEP_COMPLETE]]\n\nSecond line."
    )
    assert done is True
    assert "STEP_COMPLETE" not in clean
    # No run of blank lines left behind where the marker was.
    assert "\n\n\n" not in clean


def test_completion_signal_handles_empty_input():
    assert svc.extract_completion_signal("") == ("", False)
    assert svc.extract_completion_signal(None) == ("", False)


# --------------------------------------------------------------------------- #
# messages_left
# --------------------------------------------------------------------------- #
def test_messages_left():
    assert svc.messages_left(0, 3) == 3
    assert svc.messages_left(2, 3) == 1
    # Never negative, even if an admin lowered the cap under the live counter.
    assert svc.messages_left(9, 3) == 0
    assert svc.messages_left(4, None) is None
    assert svc.messages_left(4, 0) is None


# --------------------------------------------------------------------------- #
# Step ordering
# --------------------------------------------------------------------------- #
def test_ordered_step_ids_uses_position_not_insertion_order():
    steps = [step("c", 2), step("a", 0), step("b", 1)]
    assert svc.ordered_step_ids(steps) == ["a", "b", "c"]


def test_next_step_id_walks_execution_order():
    steps = [step("c", 2), step("a", 0), step("b", 1)]
    assert svc.next_step_id(steps, "a") == "b"
    assert svc.next_step_id(steps, "b") == "c"


def test_next_step_id_returns_none_on_last_step():
    steps = [step("a", 0), step("b", 1)]
    assert svc.next_step_id(steps, "b") is None


def test_next_step_id_returns_none_for_unknown_step():
    # A step deleted underneath a run must complete it, not jump somewhere.
    steps = [step("a", 0), step("b", 1)]
    assert svc.next_step_id(steps, "deleted") is None
    assert svc.next_step_id(steps, None) is None


def test_ordering_breaks_position_ties_deterministically():
    steps = [
        step("z", 0, created_at=T0 + timedelta(minutes=1)),
        step("y", 0, created_at=T0),
    ]
    assert svc.ordered_step_ids(steps) == ["y", "z"]
    assert svc.ordered_step_ids(list(reversed(steps))) == ["y", "z"]


def test_step_number_is_one_based():
    steps = [step("a", 0), step("b", 1), step("c", 2)]
    assert svc.step_number(steps, "a") == 1
    assert svc.step_number(steps, "c") == 3
    assert svc.step_number(steps, "nope") is None
    assert svc.step_number(steps, None) is None


# --------------------------------------------------------------------------- #
# reordered_positions
# --------------------------------------------------------------------------- #
def test_reordered_positions_happy_path():
    assert svc.reordered_positions(["a", "b", "c"], ["c", "a", "b"]) == {
        "c": 0,
        "a": 1,
        "b": 2,
    }


@pytest.mark.parametrize(
    "requested",
    [
        ["a", "a", "b"],  # duplicate
        ["a", "b"],  # missing one
        ["a", "b", "c", "d"],  # extra
        ["a", "b", "x"],  # foreign id
    ],
)
def test_reordered_positions_rejects_non_permutations(requested):
    with pytest.raises(ValueError):
        svc.reordered_positions(["a", "b", "c"], requested)


# --------------------------------------------------------------------------- #
# resolve_locale
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw", ["fa", "FA", "fa-IR", "fa_IR", "  fa  "])
def test_resolve_locale_accepts_persian_forms(raw):
    assert svc.resolve_locale(raw) == "fa"


@pytest.mark.parametrize("raw", [None, "", "de", "zz", "english"])
def test_resolve_locale_falls_back_to_english(raw):
    assert svc.resolve_locale(raw) == "en"


# --------------------------------------------------------------------------- #
# localized
# --------------------------------------------------------------------------- #
def test_localized_prefers_the_requested_language():
    row = wizard_row(title_en="Screening", title_fa="غربالگری")
    assert svc.localized(row, "title", "fa") == "غربالگری"
    assert svc.localized(row, "title", "en") == "Screening"


def test_localized_falls_back_to_the_other_language():
    row = wizard_row(title_en="Screening", title_fa="")
    assert svc.localized(row, "title", "fa") == "Screening"


def test_localized_treats_whitespace_only_as_empty():
    row = wizard_row(title_en="Screening", title_fa="   ")
    assert svc.localized(row, "title", "fa") == "Screening"


def test_localized_returns_empty_when_nothing_is_filled_in():
    row = wizard_row(title_en="", title_fa=None)
    assert svc.localized(row, "title", "fa") == ""


# --------------------------------------------------------------------------- #
# slugify
# --------------------------------------------------------------------------- #
def test_slugify_normalises_case_and_punctuation():
    assert svc.slugify("My New Wizard!") == "my-new-wizard"
    assert svc.slugify("  Systematic  Review  ") == "systematic-review"
    assert svc.slugify("A/B — Test") == "a-b-test"


def test_slugify_is_idempotent():
    assert svc.slugify("my-new-wizard") == "my-new-wizard"


def test_slugify_of_farsi_only_input_is_empty():
    # Callers must reject this with a 400 rather than store an empty slug.
    assert svc.slugify("غربالگری مقالات") == ""


# --------------------------------------------------------------------------- #
# build_step_guidance
# --------------------------------------------------------------------------- #
def _guidance(**overrides):
    kwargs = dict(
        wizard_title="Systematic Review",
        step_name="Define the question",
        step_index=2,
        total_steps=4,
        guideline_prompt="Help the user write a PICO question.",
        remaining_messages=3,
        lang="en",
    )
    kwargs.update(overrides)
    return svc.build_step_guidance(**kwargs)


def test_guidance_includes_the_prompt_verbatim_and_the_step_position():
    text = _guidance()
    assert "Help the user write a PICO question." in text
    assert "step 2 of 4" in text
    assert '"Define the question"' in text
    assert '"Systematic Review"' in text


def test_guidance_retires_earlier_steps_instructions():
    # Previous steps' prompts are still in the same LangGraph thread, so the
    # framing has to explicitly supersede them.
    text = _guidance()
    assert "obsolete" in text
    assert "ONLY the instructions below" in text


def test_guidance_announces_the_remaining_turns():
    assert "3 messages left" in _guidance(remaining_messages=3)
    assert "1 message left" in _guidance(remaining_messages=1)


def test_guidance_omits_the_countdown_when_uncapped():
    text = _guidance(remaining_messages=None)
    assert "left in this" not in text
    assert "Help the user write a PICO question." in text


def test_guidance_requests_persian_only_for_fa():
    assert "Respond in Persian (Farsi)." in _guidance(lang="fa")
    assert "Persian" not in _guidance(lang="en")


def test_guidance_teaches_the_completion_marker():
    text = _guidance()
    assert svc.STEP_COMPLETE_MARKER in text
    # And tells the model to keep it invisible and not to jump ahead.
    assert "never mention it" in text
    assert "user's choice" in text


def test_guidance_marker_instruction_survives_round_trip():
    # A reply that follows the instruction must parse back out cleanly.
    reply = f"Looks good.\n\n{svc.STEP_COMPLETE_MARKER}"
    clean, done = svc.extract_completion_signal(reply)
    assert (clean, done) == ("Looks good.", True)
