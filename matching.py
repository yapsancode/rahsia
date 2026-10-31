import hashlib

SEEKER_TO_PROVIDER = {"funding": "invest", "partner": "partner", "mentor": "mentor"}

def canonical_intent(role: str, raw_intent: str):
    intent = raw_intent.strip().lower()
    if role == "seeker":  # founder
        return SEEKER_TO_PROVIDER.get(intent)  # None if unmapped
    if role == "provider":  # investor
        return None if intent == "hire_team" else intent
    return None

def profile_token(profile: dict, role: str) -> list[str]:
    intent = canonical_intent(role, profile["intent"])
    if intent is None:
        return []
    tup = (intent, profile["stage"].strip().lower(), profile["sector"].strip().lower(),
           profile["money"].strip().lower(), profile["geography"].strip().lower())
    return [hashlib.sha256("|".join(tup).encode()).hexdigest()]