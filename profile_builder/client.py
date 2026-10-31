"""Tiny client for a local Ollama server. Refuses any host that is not this laptop."""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

LOOPBACK = {"localhost", "127.0.0.1", "::1"}
KEEP_ALIVE = "2h"  # a cold start took 60 seconds on the GTX 1650 laptop (measured 2026-10-31), far over the target
# Every call must send the same values: a change makes Ollama reload the model.
RUNNER_OPTIONS = {"num_ctx": 4096}
# Ollama keeps much of this model off a 4 GB GPU by default. All layers on it took 3.4 seconds
# against 17 for the same answer (GTX 1650, measured 2026-10-31). Set RAHSIA_FULL_GPU=0 to turn it off.
FULL_GPU = {"num_gpu": 99}

_full_gpu = os.environ.get("RAHSIA_FULL_GPU", "1") != "0"

# urlopen would follow HTTP_PROXY and send the notes to the proxy, whatever the URL says.
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class RunnerError(RuntimeError):
    pass


def runner_url() -> str:
    host = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
    if "://" not in host:
        host = "http://" + host
    parsed = urlparse(host)
    if parsed.hostname not in LOOPBACK:
        raise RunnerError(
            f"Refusing to send notes to {parsed.hostname!r}. "
            "Profile data must stay on this laptop (localhost only)."
        )
    return f"{parsed.scheme}://{parsed.hostname if parsed.hostname != '::1' else '[::1]'}:{parsed.port or 11434}"


def _model_names(path: str) -> list[str]:
    with _NO_PROXY.open(runner_url() + path, timeout=2) as response:
        return [m.get("name") for m in json.load(response).get("models", [])]


def model_state(model: str) -> str:
    """'ready' (in memory), 'loading' (on disk), or 'missing' (no runner or no model). Never raises."""
    try:
        if model in _model_names("/api/ps"):
            return "ready"
        return "loading" if model in _model_names("/api/tags") else "missing"
    except (RunnerError, OSError, ValueError):
        return "missing"


def _send(path: str, payload: dict, options: dict, timeout: float) -> dict:
    all_options = {**RUNNER_OPTIONS, **(FULL_GPU if _full_gpu else {}), **options}
    request = urllib.request.Request(
        runner_url() + path,
        data=json.dumps({**payload, "options": all_options}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with _NO_PROXY.open(request, timeout=timeout) as response:
        return json.load(response)


def _post(path: str, payload: dict, options: dict, timeout: float) -> dict:
    """Send once. If the model does not fit on this GPU, go back to Ollama's own split for good."""
    global _full_gpu
    try:
        return _send(path, payload, options, timeout)
    except urllib.error.HTTPError as error:
        if not _full_gpu or error.code < 500:
            raise
        _full_gpu = False
    return _send(path, payload, options, timeout)


def warm_up(model: str) -> None:
    """Load the model now, so nobody waits for it during the first request. Never raises."""
    payload = {"model": model, "keep_alive": KEEP_ALIVE, "stream": False}
    try:
        _post("/api/generate", payload, {}, timeout=180)
    except (RunnerError, OSError, ValueError):
        pass  # the first request will show the person a clear error


def chat(model: str, system: str, user: str, schema: dict, seed: int = 0,
         temperature: float = 0.0, timeout: float = 120.0) -> str:
    """One request, schema-constrained JSON back as text."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "think": False,
        "keep_alive": KEEP_ALIVE,
        "format": schema,
    }
    try:
        body = _post("/api/chat", payload, {"temperature": temperature, "seed": seed}, timeout)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise RunnerError(f"Ollama returned {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RunnerError(f"Cannot reach Ollama at {runner_url()}: {error}") from error
    return body.get("message", {}).get("content", "")
