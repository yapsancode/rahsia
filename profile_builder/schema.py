"""Profile schema. The model fills `Extracted`; code adds `role` and `reviewed`.

Every field is a fixed choice or a number so the matching step can compare
profiles later. Free text is limited to `deal_breakers`, which is shown to a
human and is not meant for matching.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Role = Literal["seeker", "provider"]

SEEKER_INTENTS = ("funding", "partner", "mentor", "programme")
PROVIDER_INTENTS = ("invest", "partner", "hire_team")
INTENTS = tuple(dict.fromkeys(SEEKER_INTENTS + PROVIDER_INTENTS))
STAGES = ("idea", "pre_seed", "seed", "series_a", "growth")
SECTORS = (
    "agritech", "fintech", "logistics", "healthtech", "edtech", "cleantech",
    "ecommerce", "saas", "deeptech", "other",
)
GEOGRAPHIES = ("MY", "SG", "ID", "TH", "VN", "PH", "other_asean", "global")
DISCLOSURE_LEVELS = ("after_match", "after_nda", "open")
CURRENCIES = ("MYR", "SGD", "USD", "IDR", "other")
LANGUAGES = ("en", "ms", "mixed")

MAX_DEAL_BREAKERS = 5
MAX_DEAL_BREAKER_CHARS = 80
MAX_MONEY = 10_000_000_000

Intent = Literal[INTENTS]
Stage = Literal[STAGES]
Sector = Literal[SECTORS]
Geography = Literal[GEOGRAPHIES]
Disclosure = Literal[DISCLOSURE_LEVELS]
Currency = Literal[CURRENCIES]
Language = Literal[LANGUAGES]


class Extracted(BaseModel):
    """What the model is asked to return. Unknown means null or an empty list."""

    model_config = ConfigDict(extra="forbid")

    intent: list[Intent] = Field(default_factory=list)
    stage: list[Stage] = Field(default_factory=list)
    sector: list[Sector] = Field(default_factory=list)
    money_min: int | None = Field(None, ge=0, le=MAX_MONEY)
    money_max: int | None = Field(None, ge=0, le=MAX_MONEY)
    currency: Currency | None = None
    geography: list[Geography] = Field(default_factory=list)
    timeline_months: int | None = Field(None, ge=1, le=60)
    deal_breakers: list[str] = Field(default_factory=list, max_length=MAX_DEAL_BREAKERS)
    disclosure_level: Disclosure | None = None
    language: Language = "en"

    @model_validator(mode="after")
    def _check_consistency(self):
        if self.money_min is not None and self.money_max is not None and self.money_min > self.money_max:
            raise ValueError("money_min is larger than money_max")
        if (self.money_min is not None or self.money_max is not None) and self.currency is None:
            raise ValueError("an amount needs a currency")
        for text in self.deal_breakers:
            if not text.strip() or len(text) > MAX_DEAL_BREAKER_CHARS:
                raise ValueError("deal_breakers must be short, non-empty phrases")
        return self


class Profile(Extracted):
    role: Role
    reviewed: bool = False  # becomes true only after the person confirms it

    @model_validator(mode="after")
    def _check_intent_for_role(self):
        allowed = SEEKER_INTENTS if self.role == "seeker" else PROVIDER_INTENTS
        bad = [i for i in self.intent if i not in allowed]
        if bad:
            raise ValueError(f"intent {bad} is not valid for a {self.role}")
        return self


def model_json_schema() -> dict:
    """Schema sent to the runner so the model can only produce these fields.

    All fields are marked required: otherwise the model skips fields that have
    defaults (it left out the money fields in our first test).
    """
    schema = Extracted.model_json_schema()
    schema["required"] = list(schema["properties"])
    return schema
