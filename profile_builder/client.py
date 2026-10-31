"""Tiny client for a local Ollama server. Refuses any host that is not this laptop."""
import json
import os
import urllib.error
import urllib.request
from urllib.parse import urlparse

LOOPBACK = {"localhost", "127.0.0.1", "::1"}


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


def chat(model: str, system: str, user: str, schema: dict, seed: int = 0,
         temperature: float = 0.0, timeout: float = 120.0) -> str:
    """One request, schema-constrained JSON back as text."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": temperature, "seed": seed},
    }
    request = urllib.request.Request(
        runner_url() + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        raise RunnerError(f"Ollama returned {error.code}: {detail}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise RunnerError(f"Cannot reach Ollama at {runner_url()}: {error}") from error
    return body.get("message", {}).get("content", "")
