"""Notes in, schema-checked profile out."""
import json
import re
import time
from dataclasses import dataclass, field

from pydantic import ValidationError

from . import client
from .prompt import system_prompt, user_prompt
from .repair import repair
from .schema import Profile, model_json_schema

DEFAULT_MODEL = "gemma4:e4b"


@dataclass
class BuildResult:
    profile: Profile | None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    seconds: float = 0.0
    model: str = DEFAULT_MODEL
    raw: str = ""

    @property
    def ok(self) -> bool:
        return self.profile is not None


def _parse_json(text: str) -> dict | None:
    """Parse the model text. Safe repair: strip code fences or text around one object."""
    candidates = [text.strip()]
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        candidates.append(match.group())
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def build_profile(notes: str, role: str, model: str = DEFAULT_MODEL, seed: int = 0,
                  temperature: float = 0.0) -> BuildResult:
    """One model call, then repair and check in code. No retry on bad output."""
    if role not in ("seeker", "provider"):
        raise ValueError("role must be 'seeker' or 'provider'")
    if not notes.strip():
        return BuildResult(None, errors=["the notes are empty"], model=model)

    started = time.perf_counter()
    raw = client.chat(model, system_prompt(), user_prompt(notes, role),
                      model_json_schema(), seed=seed, temperature=temperature)
    result = BuildResult(None, model=model, raw=raw)

    data = _parse_json(raw)
    if data is None:
        result.errors.append("the model did not return a JSON object")
    else:
        fixed, result.warnings = repair(data, role, notes)
        try:
            result.profile = Profile(role=role, **fixed)
        except ValidationError as error:
            result.errors.extend(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors())
    result.seconds = round(time.perf_counter() - started, 2)
    return result


def diff_profiles(a: Profile, b: Profile) -> dict[str, tuple]:
    """Fields where two runs on the same notes disagree."""
    one, two = a.model_dump(), b.model_dump()
    return {k: (one[k], two[k]) for k in one if one[k] != two[k]}
