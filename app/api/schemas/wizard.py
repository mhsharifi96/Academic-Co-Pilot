"""
Request/response schemas for the wizard endpoints.

Two audiences, two shapes:

* **Public / user** routes return text already resolved for one language
  (``title``, ``short_description``, ``name``) and never expose a step's
  ``guideline_prompt`` — it is the admin's instruction to the model, not user
  content.
* **Admin** routes return the raw ``*_en`` / ``*_fa`` columns so the editor can
  show both languages side by side.

The admin write schemas accept the field spellings from the original feature
request (``gaurdline_prompt``, ``max_masseage``) as aliases, so a client written
against either name works.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field


# --------------------------------------------------------------------------- #
# Public / user reads
# --------------------------------------------------------------------------- #
class WizardStepPublicOut(BaseModel):
    """A step as the runner shows it — no prompt, just the shape of the path."""

    id: str
    name: str
    position: int
    max_messages: Optional[int] = None


class WizardPublicOut(BaseModel):
    id: str
    slug: str
    title: str
    short_description: str
    icon: Optional[str] = None
    step_count: int
    lang: str


class WizardPublicDetailOut(WizardPublicOut):
    steps: List[WizardStepPublicOut] = []


class WizardMessageOut(BaseModel):
    id: str
    step_id: Optional[str] = None
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WizardRunOut(BaseModel):
    id: str
    wizard_id: str
    wizard_slug: str
    wizard_title: str
    session_id: str
    status: str  # "active" | "completed" | "abandoned"
    current_step: Optional[WizardStepPublicOut] = None
    current_step_index: Optional[int] = None  # 1-based
    total_steps: int
    step_message_count: int
    messages_left_in_step: Optional[int] = None  # None == unlimited
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    lang: str


class WizardRunDetailOut(WizardRunOut):
    steps: List[WizardStepPublicOut] = []
    messages: List[WizardMessageOut] = []


# --------------------------------------------------------------------------- #
# User writes
# --------------------------------------------------------------------------- #
class StartRunRequest(BaseModel):
    """Identify the wizard to start by id or by slug — exactly one."""

    wizard_id: Optional[str] = None
    slug: Optional[str] = None


class WizardTurnRequest(BaseModel):
    message: str


class WizardResumeRequest(BaseModel):
    decision: Literal["approve", "edit", "reject"]
    edited_args: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None


class WizardTurnResponse(BaseModel):
    response: str
    run_id: str
    session_id: str
    status: Literal["complete", "interrupted", "blocked"] = "complete"
    interrupt: Optional[Dict[str, Any]] = None
    run_status: str
    step_advanced: bool = False
    completed: bool = False
    # The agent judged this step's goal met and is offering to move on. Advisory
    # only — the run does not advance until the user asks it to.
    step_complete_suggested: bool = False
    current_step: Optional[WizardStepPublicOut] = None
    current_step_index: Optional[int] = None
    total_steps: int = 0
    messages_left_in_step: Optional[int] = None
    balance: Optional[float] = None


class SuggestionOut(BaseModel):
    question: str
    reason: str = ""


class SuggestionsResponse(BaseModel):
    """Follow-up questions the user could send next. Generated on request."""

    run_id: str
    suggestions: List[SuggestionOut] = []
    balance: Optional[float] = None


class AbandonRunResponse(BaseModel):
    run_id: str
    abandoned: bool


# --------------------------------------------------------------------------- #
# Admin
# --------------------------------------------------------------------------- #
class StepAdminOut(BaseModel):
    id: str
    wizard_id: str
    name_en: str
    name_fa: str
    guideline_prompt: str
    max_messages: Optional[int] = None
    position: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WizardAdminOut(BaseModel):
    id: str
    slug: str
    name: str
    title_en: str
    title_fa: str
    short_description_en: str
    short_description_fa: str
    icon: Optional[str] = None
    position: int
    is_published: bool
    enforce_scope_guardrail: bool
    created_at: datetime
    updated_at: datetime
    step_count: int = 0
    run_count: int = 0

    model_config = {"from_attributes": True}


class WizardAdminDetailOut(WizardAdminOut):
    steps: List[StepAdminOut] = []


class WizardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    # Derived from ``name`` when omitted; must be ASCII-sluggable.
    slug: Optional[str] = None
    title_en: str = ""
    title_fa: str = ""
    short_description_en: str = ""
    short_description_fa: str = ""
    icon: Optional[str] = None
    position: int = 0
    is_published: bool = False
    enforce_scope_guardrail: bool = True


class WizardUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    slug: Optional[str] = None
    title_en: Optional[str] = None
    title_fa: Optional[str] = None
    short_description_en: Optional[str] = None
    short_description_fa: Optional[str] = None
    icon: Optional[str] = None
    position: Optional[int] = None
    is_published: Optional[bool] = None
    enforce_scope_guardrail: Optional[bool] = None


class StepCreate(BaseModel):
    name_en: str = ""
    name_fa: str = ""
    guideline_prompt: str = Field(
        min_length=1,
        validation_alias=AliasChoices("guideline_prompt", "gaurdline_prompt"),
    )
    # NULL means the step is uncapped and only ends when an admin adds a cap.
    max_messages: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("max_messages", "max_masseage"),
    )
    position: Optional[int] = None

    model_config = {"populate_by_name": True}


class StepBulkCreate(BaseModel):
    """
    An outline — one step name per line — appended as steps in that order.

    Every created step gets the same ``max_messages`` and the same generated
    ``guideline_prompt``; the admin then edits each one. Parsing rules live in
    ``wizard_service.parse_step_outline``.
    """

    outline: str
    max_messages: Optional[int] = Field(default=None, ge=1)
    # ``{name}`` is replaced with the step's name. Blank uses the service's
    # default template.
    guideline_template: str = ""


class StepUpdate(BaseModel):
    name_en: Optional[str] = None
    name_fa: Optional[str] = None
    guideline_prompt: Optional[str] = Field(
        default=None,
        min_length=1,
        validation_alias=AliasChoices("guideline_prompt", "gaurdline_prompt"),
    )
    max_messages: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("max_messages", "max_masseage"),
    )
    position: Optional[int] = None

    model_config = {"populate_by_name": True}


class ReorderStepsRequest(BaseModel):
    """Every step id of the wizard, in the desired order."""

    step_ids: List[str]


class DeleteResponse(BaseModel):
    id: str
    deleted: bool
