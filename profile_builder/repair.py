"""Safe repairs done in code, so we do not need to ask the model again.

Each repair is small and predictable. Anything we cannot repair safely is
dropped and reported as a warning; the person sees it at review time.
"""
import re

from .schema import (
    CURRENCIES, DISCLOSURE_LEVELS, GEOGRAPHIES, INTENTS, LANGUAGES,
    MAX_DEAL_BREAKER_CHARS, MAX_DEAL_BREAKERS, SECTORS, SEEKER_INTENTS,
    PROVIDER_INTENTS, STAGES, Extracted,
)

LIST_FIELDS = {
    "intent": INTENTS,
    "stage": STAGES,
    "sector": SECTORS,
    "geography": GEOGRAPHIES,
}

ALIASES = {
    "intent": {"invest_in_startups": "invest", "investment": "invest", "mentorship": "mentor",
               "partnership": "partner", "accelerator": "programme", "program": "programme",
               "hire": "hire_team", "acquihire": "hire_team", "acqui_hire": "hire_team"},
    "stage": {"preseed": "pre_seed", "pre_seed_stage": "pre_seed", "seriesa": "series_a",
              "early": "pre_seed", "growth_stage": "growth"},
    "sector": {"agri_tech": "agritech", "agriculture": "agritech", "farming": "agritech",
               "fin_tech": "fintech", "finance": "fintech", "health": "healthtech",
               "healthcare": "healthtech", "education": "edtech", "e_commerce": "ecommerce",
               "software": "saas", "climate": "cleantech", "logistic": "logistics"},
    "geography": {"malaysia": "MY", "singapore": "SG", "indonesia": "ID", "thailand": "TH",
                  "vietnam": "VN", "philippines": "PH", "asean": "other_asean",
                  "southeast_asia": "other_asean", "sea": "other_asean", "worldwide": "global"},
}

CURRENCY_ALIASES = {"RM": "MYR", "MALAYSIAN_RINGGIT": "MYR", "RINGGIT": "MYR", "S$": "SGD",
                    "SGD": "SGD", "US$": "USD", "USD": "USD", "RP": "IDR", "IDR": "IDR"}
DISCLOSURE_ALIASES = {"after_matching": "after_match", "only_after_match": "after_match",
                      "nda": "after_nda", "after_an_nda": "after_nda", "public": "open"}

MONEY_WORDS = re.compile(r"\d|juta|ribu|million|thousand|ratus|hundred", re.IGNORECASE)
INJECTION = re.compile(
    r"ignore (all|any|the|previous|prior|above)|disregard|forget (all|your|the)|"
    r"system prompt|you are now|new instructions?|override|reveal|"
    r"abaikan|lupakan arahan|arahan baharu|arahan baru",
    re.IGNORECASE,
)


def _key(value: str) -> str:
    return re.sub(r"[\s\-/]+", "_", value.strip().lower())


def _parse_amount(value) -> int | None:
    """'300k', '1.5m', 'RM 2 juta', 300000 -> whole number, or None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return max(int(value), 0)
    text = str(value).lower().replace(",", "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(k|m|juta|ribu|million|thousand)?", text)
    if not match:
        return None
    number = float(match.group(1))
    factor = {"k": 1_000, "ribu": 1_000, "thousand": 1_000,
              "m": 1_000_000, "juta": 1_000_000, "million": 1_000_000}.get(match.group(2), 1)
    return int(number * factor)


def _parse_months(value) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def _fix_list(name: str, value, warnings: list[str]) -> list[str]:
    allowed = LIST_FIELDS[name]
    items = [] if value is None else value if isinstance(value, list) else [value]
    fixed: list[str] = []
    for item in items:
        if not isinstance(item, str):
            warnings.append(f"{name}: dropped non-text value {item!r}")
            continue
        token = _key(item)
        token = ALIASES[name].get(token, token)
        if name == "geography" and token.upper() in allowed:
            token = token.upper()
        if token in allowed:
            if token not in fixed:
                fixed.append(token)
        else:
            warnings.append(f"{name}: dropped unknown value {item!r}")
    return fixed


def find_injection(notes: str) -> list[str]:
    """Warn about lines in the notes that look like instructions to the model."""
    return [
        f"notes line {number} looks like an instruction to the AI: {line.strip()[:80]!r}"
        for number, line in enumerate(notes.splitlines(), start=1)
        if INJECTION.search(line)
    ]


def repair(raw: dict, role: str, notes: str) -> tuple[dict, list[str]]:
    """Return (repaired dict, warnings). Does not raise on bad model output."""
    warnings: list[str] = []
    fixed = {k: v for k, v in raw.items() if k in Extracted.model_fields}
    for extra in sorted(set(raw) - set(fixed)):
        warnings.append(f"dropped unknown field {extra!r}")

    for name in LIST_FIELDS:
        fixed[name] = _fix_list(name, fixed.get(name), warnings)

    allowed_intents = SEEKER_INTENTS if role == "seeker" else PROVIDER_INTENTS
    wrong_role = [i for i in fixed["intent"] if i not in allowed_intents]
    if wrong_role:
        warnings.append(f"intent: dropped {wrong_role}, not valid for a {role}")
        fixed["intent"] = [i for i in fixed["intent"] if i in allowed_intents]

    low = _parse_amount(fixed.get("money_min"))
    high = _parse_amount(fixed.get("money_max"))
    if (low is not None or high is not None) and not MONEY_WORDS.search(notes):
        warnings.append("money: no amount in the notes, so the model's amount was removed")
        low = high = None
    if low is not None and high is not None and low > high:
        low, high = high, low
        warnings.append("money: min and max were swapped")
    fixed["money_min"], fixed["money_max"] = low, high

    currency = fixed.get("currency")
    if isinstance(currency, str):
        currency = CURRENCY_ALIASES.get(currency.strip().upper(), currency.strip().upper())
        if currency not in CURRENCIES:
            warnings.append(f"currency: unknown {fixed['currency']!r}, set to 'other'")
            currency = "other"
    else:
        currency = None
    if currency is None and (low is not None or high is not None):
        currency = "MYR"
        warnings.append("currency: missing, assumed MYR (please check)")
    fixed["currency"] = currency

    months = _parse_months(fixed.get("timeline_months"))
    if months is not None and not 1 <= months <= 60:
        warnings.append(f"timeline_months: {months} is out of range, removed")
        months = None
    fixed["timeline_months"] = months

    breakers = []
    for item in fixed.get("deal_breakers") or []:
        text = str(item).strip()
        if text and text.lower() not in (b.lower() for b in breakers):
            breakers.append(text[:MAX_DEAL_BREAKER_CHARS])
    if len(breakers) > MAX_DEAL_BREAKERS:
        warnings.append(f"deal_breakers: kept the first {MAX_DEAL_BREAKERS}")
    fixed["deal_breakers"] = breakers[:MAX_DEAL_BREAKERS]

    level = fixed.get("disclosure_level")
    if isinstance(level, str):
        level = _key(level)
        level = DISCLOSURE_ALIASES.get(level, level)
        if level not in DISCLOSURE_LEVELS:
            warnings.append(f"disclosure_level: dropped unknown value {fixed['disclosure_level']!r}")
            level = None
    else:
        level = None
    fixed["disclosure_level"] = level

    language = fixed.get("language")
    fixed["language"] = language if language in LANGUAGES else "en"
    if language not in LANGUAGES:
        warnings.append("language: missing or unknown, set to 'en'")

    warnings.extend(find_injection(notes))
    return fixed, warnings
