"""The local server between the screens and the Python parts.

One copy runs per laptop for one person, so one round of state lives in memory.
The match runs in a thread and the page asks for the state, because a match
waits for the other laptop.
"""
import threading
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from profile_builder import client, schema
from profile_builder.builder import DEFAULT_MODEL, build_profile
from profile_builder.client import RunnerError
from profile_builder.draft import build_draft
from profile_builder.schema import Profile, Side

from . import engine

ROOT = Path(__file__).resolve().parent
SAMPLES = ROOT.parent / "profile_builder" / "samples"
SAMPLE_FILES = {"seeker": ["seeker_en.txt", "seeker_mixed_injection.txt"], "provider": ["provider_ms.txt"]}

app = FastAPI(title="Rahsia", docs_url=None, redoc_url=None, openapi_url=None)
# A web page on another site must not be able to reach this server through the browser.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])


@dataclass
class Round:
    phase: str = "idle"  # idle, matching, matched, no_match, agreeing, revealed, declined, error
    profile: dict | None = None
    overlap: dict | None = None
    error: str = ""
    number: int = 0  # a thread from an earlier round must not change this one


state = Round()
lock = threading.Lock()


class NotesIn(BaseModel):
    notes: str
    side: Side


class ProfileIn(BaseModel):
    profile: dict


def _set(number: int, **changes) -> None:
    with lock:
        if number != state.number:
            return
        for name, value in changes.items():
            setattr(state, name, value)


def _in_thread(number: int, task) -> None:
    def run():
        try:
            task()
        except Exception as error:  # the page must show this, not hang on "waiting"
            _set(number, phase="error", error=str(error))
    threading.Thread(target=run, daemon=True).start()


def _need_phase(*phases: str) -> Round:
    if state.phase not in phases:
        raise HTTPException(409, f"This step is not open yet (now: {state.phase}).")
    return state


def _samples() -> dict[str, list[dict]]:
    return {side: [{"name": name.removesuffix(".txt"), "text": (SAMPLES / name).read_text(encoding="utf-8")}
                   for name in names] for side, names in SAMPLE_FILES.items()}


@app.get("/api/config")
def config():
    return {
        "model": DEFAULT_MODEL,
        "gemma_ready": client.has_model(DEFAULT_MODEL),
        "engine": {"name": engine.ENGINE_NAME, "private": engine.ENGINE_PRIVATE, "signed": engine.ENGINE_SIGNED},
        "choices": {"seeker_intent": schema.SEEKER_INTENTS, "provider_intent": schema.PROVIDER_INTENTS,
                    "stage": schema.STAGES, "sector": schema.SECTORS, "money_rm": schema.MONEY_BUCKETS,
                    "geography": schema.GEOGRAPHIES},
        "limits": {"text": schema.MAX_TEXT_CHARS},
        "samples": _samples(),
    }


@app.post("/api/profile")
async def make_profile(body: NotesIn):
    try:
        result = await run_in_threadpool(build_profile, body.notes, body.side)
    except RunnerError as error:
        raise HTTPException(503, f"Gemma is not reachable. Start Ollama, then try again. ({error})")
    return {"profile": result.profile.model_dump() if result.profile else None, "warnings": result.warnings,
            "errors": result.errors, "seconds": result.seconds, "model": result.model}


@app.post("/api/match")
def start_match(body: ProfileIn):
    try:
        profile = Profile(**{**body.profile, "reviewed": True}).model_dump()
    except ValidationError as error:
        raise HTTPException(422, error.errors()[0]["msg"])
    with lock:
        state.number += 1
        number = state.number
        state.phase, state.profile, state.overlap, state.error = "matching", profile, None, ""

    def task():
        found = engine.run_match(profile)
        _set(number, phase="matched" if found else "no_match")
    _in_thread(number, task)
    return {"phase": "matching"}


@app.get("/api/state")
def read_state():
    return {"phase": state.phase, "overlap": state.overlap, "error": state.error}


@app.post("/api/agree")
def agree():
    round_now = _need_phase("matched")
    number, profile = round_now.number, round_now.profile
    _set(number, phase="agreeing")

    def task():
        overlap = engine.reveal_overlap(profile)
        if overlap is None:
            _set(number, phase="declined")
        else:
            _set(number, phase="revealed", overlap=overlap)
    _in_thread(number, task)
    return {"phase": "agreeing"}


@app.post("/api/decline")
def decline():
    round_now = _need_phase("matched")
    engine.decline(round_now.profile)
    _set(round_now.number, phase="idle")
    return {"phase": "idle"}


@app.post("/api/draft")
async def draft():
    round_now = _need_phase("revealed")
    try:
        result = await run_in_threadpool(build_draft, round_now.overlap, round_now.profile["side"])
    except RunnerError as error:
        raise HTTPException(503, f"Gemma is not reachable. Start Ollama, then try again. ({error})")
    return {"text": result.text, "source": result.source, "warnings": result.warnings,
            "seconds": result.seconds, "model": result.model}


@app.post("/api/receipt")
def receipt():
    round_now = _need_phase("revealed")
    return engine.save_receipt(round_now.overlap, round_now.profile["side"])


@app.post("/api/reset")
def reset():
    with lock:
        side = state.profile["side"] if state.profile else None
        state.number += 1
        state.phase, state.profile, state.overlap, state.error = "idle", None, None, ""
    engine.reset(side)
    return {"phase": "idle"}


app.mount("/", StaticFiles(directory=ROOT / "static", html=True), name="static")
