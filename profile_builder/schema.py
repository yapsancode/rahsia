"""Profile schema, matching the Shared fields in TASKS.md.

The model fills `Extracted`. Code then builds `Profile`, the JSON the match
check reads. Exact amounts stay in `Extracted`; `Profile` holds only money
buckets. Blank means null, an empty list or empty text, depending on the field.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Side = Literal["seeker", "provider"]

SEEKER_INTENTS = ("funding", "partner", "mentor")
PROVIDER_INTENTS = ("invest", "partner", "mentor", "hire_team")
INTENTS = tuple(dict.fromkeys(SEEKER_INTENTS + PROVIDER_INTENTS))
STAGES = ("idea", "pre-seed", "seed", "series-a")
SECTORS = ("agritech", "fintech", "logistics", "healthtech", "edtech", "other")
MONEY_BUCKETS = ("under-100k", "100k-250k", "250k-500k", "500k-1m", "over-1m")
MONEY_EDGES = (100_000, 250_000, 500_000, 1_000_000)  # upper edge of each bucket but the last
GEOGRAPHIES = ("malaysia", "singapore", "indonesia", "thailand", "vietnam", "philippines", "other-asean")
CURRENCIES = ("MYR", "SGD", "USD", "IDR", "other")

MAX_TEXT_CHARS = 120
MAX_MONEY = 10_000_000_000

Intent = Literal[INTENTS]
Stage = Literal[STAGES]
Sector = Literal[SECTORS]
Money = Literal[MONEY_BUCKETS]
Geography = Literal[GEOGRAPHIES]
Currency = Literal[CURRENCIES]


class Extracted(BaseModel):
    """What the model is asked to return. Unknown means null, an empty list or empty text."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent | None = None
    stage: list[Stage] = Field(default_factory=list)
    sector: list[Sector] = Field(default_factory=list)
    money_min: int | None = Field(None, ge=0, le=MAX_MONEY)
    money_max: int | None = Field(None, ge=0, le=MAX_MONEY)
    currency: Currency | None = None
    geography: list[Geography] = Field(default_factory=list)
    timeline_months: int | None = Field(None, ge=1, le=60)
    deal_breakers: str = ""
    disclosure: str = ""


class Profile(BaseModel):
    """The shared profile. `reviewed` is the one extra field: the person confirmed it."""

    model_config = ConfigDict(extra="forbid")

    side: Side
    intent: Intent | None = None
    stage: list[Stage] = Field(default_factory=list)
    sector: list[Sector] = Field(default_factory=list)
    money_rm: list[Money] = Field(default_factory=list)
    geography: list[Geography] = Field(default_factory=list)
    timeline_months: int | None = Field(None, ge=1, le=60)
    deal_breakers: str = Field("", max_length=MAX_TEXT_CHARS)
    disclosure: str = Field("", max_length=MAX_TEXT_CHARS)
    reviewed: bool = False  # becomes true only after the person confirms it

    @model_validator(mode="after")
    def _check_intent_for_side(self):
        allowed = SEEKER_INTENTS if self.side == "seeker" else PROVIDER_INTENTS
        if self.intent is not None and self.intent not in allowed:
            raise ValueError(f"intent {self.intent!r} is not valid for a {self.side}")
        return self


def model_json_schema() -> dict:
    """Schema sent to the runner so the model can only produce these fields.

    All fields are marked required: otherwise the model skips fields that have
    defaults (it left out the money fields in our first test).
    """
    schema = Extracted.model_json_schema()
    schema["required"] = list(schema["properties"])
    return schema
