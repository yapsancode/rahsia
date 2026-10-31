"""The plug between the screens and the match engine.

THIS FILE IS A STAND-IN, SO THE SCREENS WORK BEFORE THE REAL ENGINE ARRIVES.
It is not private: it writes the full profile to a temp folder, in plain text,
and the other side reads it. It works between two copies of the app on ONE
laptop, with fake data only. The screens say so while ENGINE_PRIVATE is False.

To plug in the real engine, keep these function names and what they return,
then set ENGINE_PRIVATE and ENGINE_SIGNED to True. The screens do not change.

    run_match(profile)            True or False, nothing else
    reveal_overlap(profile)       after both agree: the shared values, or None if they declined
    decline(profile)              tell the other side we said no
    save_receipt(overlap, side)   write the receipt file and return what it holds
    reset(side)                   forget this round
"""
import hashlib
import json
import os
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_NAME = "Stand-in engine"
ENGINE_PRIVATE = False  # True only for the real PSI check. The word "private" depends on this.
ENGINE_SIGNED = False  # True only when receipts are signed with a maintained library.

WAIT_SECONDS = 180
POLL_SECONDS = 0.2
RECEIPTS = Path(__file__).resolve().parent.parent / "receipts"
MATCH_FIELDS = ("stage", "sector", "money_rm", "geography")
INTENT_FITS = {("funding", "invest"), ("partner", "partner"), ("mentor", "mentor")}

_folder = Path(tempfile.gettempdir()) / "rahsia-stand-in"
_stop = threading.Event()
_other_profile: dict | None = None


class EngineError(RuntimeError):
    pass


def _other(side: str) -> str:
    return "provider" if side == "seeker" else "seeker"


def _write(name: str, text: str) -> None:
    _folder.mkdir(exist_ok=True)
    temporary = _folder / f"{name}.tmp"
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, _folder / name)  # the other side never reads half a file


def _remove(*names: str) -> None:
    for name in names:
        (_folder / name).unlink(missing_ok=True)


def _take(*names: str) -> tuple[str, str]:
    """Wait for one of these files, then read and delete it, so each is used once."""
    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        if _stop.is_set():
            raise EngineError("Cancelled.")
        for name in names:
            path = _folder / name
            if path.exists():
                text = path.read_text(encoding="utf-8")
                path.unlink(missing_ok=True)
                return name, text
        time.sleep(POLL_SECONDS)
    raise EngineError("The other laptop did not connect. Check that it is running, then try again.")


def matches(seeker: dict, provider: dict) -> bool:
    """The Match rule in TASKS.md."""
    if (seeker.get("intent"), provider.get("intent")) not in INTENT_FITS:
        return False
    return all(set(seeker.get(f) or []) & set(provider.get(f) or []) for f in MATCH_FIELDS)


def run_match(profile: dict) -> bool:
    global _other_profile
    side = profile["side"]
    _stop.clear()
    _other_profile = None
    _remove(f"{side}.agree", f"{side}.decline", f"{_other(side)}.agree", f"{_other(side)}.decline")
    _write(f"{side}.profile", json.dumps(profile))
    try:
        _, text = _take(f"{_other(side)}.profile")
    except EngineError:
        _remove(f"{side}.profile")
        raise
    _other_profile = json.loads(text)
    seeker, provider = (profile, _other_profile) if side == "seeker" else (_other_profile, profile)
    return matches(seeker, provider)


def reveal_overlap(profile: dict) -> dict | None:
    side = profile["side"]
    _write(f"{side}.agree", "yes")
    name, _ = _take(f"{_other(side)}.agree", f"{_other(side)}.decline")
    if name.endswith(".decline"):
        return None
    return {f: [v for v in profile.get(f) or [] if v in (_other_profile.get(f) or [])] for f in MATCH_FIELDS}


def decline(profile: dict) -> None:
    _write(f"{profile['side']}.decline", "no")


def save_receipt(overlap: dict, side: str) -> dict:
    """Stand-in receipt: hashed but not signed. Saved in receipts/, which Git ignores."""
    now = datetime.now(timezone.utc).astimezone()
    body = {
        "fields_shared": overlap,
        "other_party": "Investor" if side == "seeker" else "Startup",
        "time": now.isoformat(timespec="seconds"),
        "note": "Evidence, not a legal contract.",
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    receipt = {**body, "hash": digest, "signature": None}
    RECEIPTS.mkdir(exist_ok=True)
    path = RECEIPTS / f"receipt-{side}-{now:%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return {**receipt, "file": str(path)}


def reset(side: str | None) -> None:
    _stop.set()
    if side:
        _remove(f"{side}.profile", f"{side}.agree", f"{side}.decline")
