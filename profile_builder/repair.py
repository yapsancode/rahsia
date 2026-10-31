"""Safe repairs done in code, so we do not need to ask the model again.

Each repair is small and predictable. Anything we cannot repair safely is
dropped and reported as a warning; the person sees it at review time.

The schema only proves the shape of an answer, not that it is true: Gemma fills
fields the notes never mention. So each field must also be supported by words
in the notes. A blank field means no match, which is the honest result.
"""
import re

from .schema import (
    CURRENCIES, GEOGRAPHIES, INTENTS, MAX_TEXT_CHARS, MONEY_BUCKETS, MONEY_EDGES,
    PROVIDER_INTENTS, SECTORS, SEEKER_INTENTS, STAGES, Extracted,
)

LIST_FIELDS = {"stage": STAGES, "sector": SECTORS, "geography": GEOGRAPHIES}

ALIASES = {
    "intent": {"investment": "invest", "mentorship": "mentor", "partnership": "partner",
               "hire": "hire_team", "hire-team": "hire_team", "acquihire": "hire_team"},
    "stage": {"preseed": "pre-seed", "seriesa": "series-a"},
    "sector": {"agri-tech": "agritech", "agriculture": "agritech", "fin-tech": "fintech",
               "health": "healthtech", "healthcare": "healthtech", "education": "edtech",
               "logistic": "logistics"},
    "geography": {"my": "malaysia", "sg": "singapore", "id": "indonesia", "th": "thailand",
                  "vn": "vietnam", "ph": "philippines", "asean": "other-asean",
                  "southeast-asia": "other-asean", "sea": "other-asean"},
}

CURRENCY_ALIASES = {"RM": "MYR", "MALAYSIAN_RINGGIT": "MYR", "RINGGIT": "MYR", "S$": "SGD",
                    "US$": "USD", "RP": "IDR"}
BLANK_TEXT = {"", "-", "none", "n/a", "na", "null", "nil", "tiada", "unknown", "not specified"}

MONEY_WORDS = re.compile(
    r"rm\s*\d|\d\s*(k|m|mil|jt|juta|ribu|million|thousand|ratus|hundred)\b|\d{5,}|\d{1,3}(,\d{3})+|"
    r"juta|ribu|million|thousand|ratus|hundred",
    re.IGNORECASE,
)

# Words that must be in the notes before we keep a value. Lower case unless noted.
INTENT_WORDS = {
    "funding": r"\brais|fund|invest|labur|modal|dana|capital",
    "partner": r"partner|rakan|kerja\s?sama|usaha\s?sama|collab|joint",
    "mentor": r"mentor|bimbing|coach|nasihat|advis|tunjuk ajar",
    "invest": r"invest|labur|cheque|\bcek\b|fund|angel|capital|modal|dana",
    "hire_team": r"\bhir(e|ing)|recruit|rekrut|acqui|talent|upah|pekerja|staff|gaji",
}
STAGE_WORDS = {
    "idea": r"\bidea\b",
    "pre-seed": r"pre[-\s]?se+d",
    "seed": r"(?<!pre)(?<!pre[-\s])\bse+d\b",
    "series-a": r"(series|seri|siri)[-\s]?a\b",
}
GEOGRAPHY_WORDS = {  # (?-i:...) = capitals only, so the code MY is not the English word "my"
    "malaysia": r"malaysia|msia|\bkl\b|kuala lumpur|selangor|penang|johor|sabah|sarawak|(?-i:\bMY\b)",
    "singapore": r"singap|\bsg\b",
    "indonesia": r"indonesia|\bindo\b|jakarta|(?-i:\bID\b)",
    "thailand": r"thai|bangkok|(?-i:\bTH\b)",
    "vietnam": r"viet\s?nam|hanoi|ho chi minh|(?-i:\bVN\b)",
    "philippines": r"philippines|filipina|manila|(?-i:\bPH\b)",
    "other-asean": r"asean|south\s?east asia|asia tenggara|brunei|cambodia|kemboja|laos|myanmar",
}
TIMELINE_WORDS = r"bulan|\bbln\b|month|\bmths?\b|tahun|\bthn\b|year|minggu|week|quarter|suku"
DEAL_BREAKER_WORDS = (
    r"\b(no|not|non|never|avoid|won'?t|tak|tidak|bukan|jangan|tanpa|refuse|except|without)\b|acqui"
)
DISCLOSURE_WORDS = (
    r"\bnda\b|shar(e|ing)|kongsi|deck|thesis|tesis|reveal|disclos|dedah|sulit|rahsia|"
    r"confidential|only after|after (a )?match|lepas (match|padan)|selepas (match|padan)"
)

INSTRUCTION_TARGET = r"(instructions?|rules?|prompts?|arahan|peraturan)"
INJECTION = re.compile(
    rf"\b(ignore|disregard|forget)\b.{{0,40}}{INSTRUCTION_TARGET}|"
    rf"\b(abaikan|lupakan|jangan ikut)\b.{{0,40}}{INSTRUCTION_TARGET}|"
    r"system prompt|you are now|new instructions?|arahan (baharu|baru)|"
    r"\b(set|change|make|tukar|ubah|letak)\s+(the\s+|your\s+)?"
    r"(sector|sektor|stage|intent|money|geography|output)\b",
    re.IGNORECASE,
)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _key(value: str) -> str:
    return re.sub(r"[\s_/]+", "-", value.strip().lower())


def _says(pattern: str, notes: str) -> bool:
    return re.search(pattern, notes, re.IGNORECASE) is not None


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


def money_buckets(low: int | None, high: int | None) -> list[str]:
    """Every bucket a range touches. See 'Bucket edges' in TASKS.md.

    A single amount on an edge uses the lower bucket. A range that starts or
    ends on an edge stays inside that bucket. A missing end is open.
    """
    if low is None and high is None:
        return []
    if low == high:
        return [next((b for b, edge in zip(MONEY_BUCKETS, MONEY_EDGES) if low <= edge), MONEY_BUCKETS[-1])]
    low = low or 0
    lower_edges = (0, *MONEY_EDGES)
    upper_edges = (*MONEY_EDGES, None)
    return [bucket for bucket, lower, upper in zip(MONEY_BUCKETS, lower_edges, upper_edges)
            if (upper is None or low < upper) and (high is None or high > lower)]


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
        if token in allowed:
            if token not in fixed:
                fixed.append(token)
        else:
            warnings.append(f"{name}: dropped unknown value {item!r}")
    return fixed


def _fix_intent(value, side: str, notes: str, asks_money: bool, warnings: list[str]) -> str | None:
    """One intent, valid for this side, and said in the notes."""
    allowed = SEEKER_INTENTS if side == "seeker" else PROVIDER_INTENTS
    supported = [i for i in allowed if _says(INTENT_WORDS[i], notes)
                 or (i == "funding" and asks_money)]
    if isinstance(value, list):
        value = value[0] if value else None
    token = None
    if isinstance(value, str):
        token = _key(value).replace("-", "_")
        token = ALIASES["intent"].get(token, token)
        if token not in INTENTS:
            warnings.append(f"intent: dropped unknown value {value!r}")
            token = None
        elif token not in allowed:
            warnings.append(f"intent: dropped {token!r}, not valid for a {side}")
            token = None
    if token in supported:
        return token
    if len(supported) == 1:
        if token is not None:
            warnings.append(f"intent: notes do not say {token!r}, used {supported[0]!r}")
        return supported[0]
    if token is not None:
        warnings.append(f"intent: notes do not say {token!r}, left blank")
    return None


def _fix_stage(values: list[str], notes: str, warnings: list[str]) -> list[str]:
    """Keep stages the notes name, and those between two named stages ('idea to seed')."""
    named = [STAGES.index(s) for s in values if _says(STAGE_WORDS[s], notes)]
    if not named:
        kept = []
    else:
        kept = [s for s in values if min(named) <= STAGES.index(s) <= max(named)]
    for stage in values:
        if stage not in kept:
            warnings.append(f"stage: notes do not say {stage!r}, removed")
    return kept


def _fix_geography(values: list[str], notes: str, warnings: list[str]) -> list[str]:
    kept = [g for g in values if _says(GEOGRAPHY_WORDS[g], notes)]
    for place in values:
        if place not in kept:
            warnings.append(f"geography: notes do not say {place!r}, removed")
    return kept


def _fix_text(name: str, value, pattern: str, notes: str, warnings: list[str]) -> str:
    if isinstance(value, list):
        value = "; ".join(str(v) for v in value)
    text = "" if value is None else str(value).strip()
    if text.lower().strip(".") in BLANK_TEXT:
        return ""
    if not _says(pattern, notes):
        warnings.append(f"{name}: notes do not say {text!r}, left blank")
        return ""
    if len(text) > MAX_TEXT_CHARS:
        warnings.append(f"{name}: shortened to {MAX_TEXT_CHARS} characters")
    return text[:MAX_TEXT_CHARS]


def remove_injection(notes: str) -> tuple[str, list[str]]:
    """Cut text that looks like an instruction to the model, so the model never reads it.

    Only the part from the instruction to the end of its sentence goes, so real
    facts in the same line stay. Telling the model to ignore it is not enough:
    in testing, Gemma still obeyed.
    """
    lines, warnings = [], []
    for number, line in enumerate(notes.splitlines(), start=1):
        kept = []
        for sentence in SENTENCE_END.split(line):
            found = INJECTION.search(sentence)
            if found:
                warnings.append(f"notes line {number}: removed text that looks like an instruction "
                                f"to the AI: {sentence[found.start():].strip()[:80]!r}")
                sentence = sentence[:found.start()].rstrip(" ,;:-")
            if sentence:
                kept.append(sentence)
        lines.append(" ".join(kept))
    return "\n".join(lines), warnings


def repair(raw: dict, side: str, notes: str) -> tuple[dict, list[str]]:
    """Return (profile fields, warnings). Does not raise on bad model output.

    `notes` must already have been through remove_injection.
    """
    warnings: list[str] = []
    for extra in sorted(set(raw) - set(Extracted.model_fields)):
        warnings.append(f"dropped unknown field {extra!r}")

    low = _parse_amount(raw.get("money_min"))
    high = _parse_amount(raw.get("money_max"))
    if (low is not None or high is not None) and not MONEY_WORDS.search(notes):
        warnings.append("money: no amount in the notes, so the model's amount was removed")
        low = high = None
    if low is not None and high is not None and low > high:
        low, high = high, low
        warnings.append("money: min and max were swapped")

    currency = raw.get("currency")
    if isinstance(currency, str):
        code = currency.strip().upper()
        currency = CURRENCY_ALIASES.get(code, code)
        if currency not in CURRENCIES:
            warnings.append(f"currency: unknown {raw['currency']!r}, set to 'other'")
            currency = "other"
    else:
        currency = None
    if currency is None and (low is not None or high is not None):
        currency = "MYR"
        warnings.append("currency: missing, assumed MYR (please check)")
    money_rm = money_buckets(low, high)
    if money_rm and currency != "MYR":
        warnings.append(f"money: amount is in {currency}, not RM, so money_rm is blank")
        money_rm = []

    months = _parse_months(raw.get("timeline_months"))
    if months is not None and not _says(TIMELINE_WORDS, notes):
        warnings.append(f"timeline_months: notes do not say {months}, removed")
        months = None
    if months is not None and not 1 <= months <= 60:
        warnings.append(f"timeline_months: {months} is out of range, removed")
        months = None

    lists = {name: _fix_list(name, raw.get(name), warnings) for name in LIST_FIELDS}
    fixed = {
        "intent": _fix_intent(raw.get("intent"), side, notes, bool(money_rm), warnings),
        "stage": _fix_stage(lists["stage"], notes, warnings),
        "sector": lists["sector"],
        "money_rm": money_rm,
        "geography": _fix_geography(lists["geography"], notes, warnings),
        "timeline_months": months,
        "deal_breakers": _fix_text("deal_breakers", raw.get("deal_breakers"), DEAL_BREAKER_WORDS,
                                   notes, warnings),
        "disclosure": _fix_text("disclosure", raw.get("disclosure"), DISCLOSURE_WORDS, notes, warnings),
    }
    return fixed, warnings
