"""The real match engine: private set intersection (PSI) between two laptops.

Two laptops talk over one TCP connection. The startup (seeker) waits for the
connection and the investor (provider) connects to it. The maths is done by
the maintained OpenMined PSI library, which runs in `psi_worker.py`. On
Windows that file runs inside WSL, because the library has no Windows build.

How a match works. Each side turns its profile into tokens, one for every
combination of intent, stage, sector, money and geography it accepts. Two
profiles share a token only if every one of those fields has a value in
common, which is exactly the Match rule in TASKS.md. Then PSI runs twice,
once with each side as the one who asks, so each side learns the answer on
its own and nobody has to believe the other side. Each side learns only
whether the sets share a token. On no match it learns nothing else.

After BOTH sides agree, PSI runs twice more and each side learns the exact
values they have in common. Nothing else is sent.

What this does not do (say it plainly when presenting):
- It does not stop someone who keeps asking with made-up profiles from
  narrowing down the other side, one yes/no at a time.
- The number of tokens each side sends is visible to the other side.
- The connection is not encrypted and the other laptop is not signed in.
  Use it on a network you trust. The profile fields are never sent in clear
  before both sides agree.

The functions at the bottom keep the names the screens use:

    run_match(profile)            True or False, nothing else
    reveal_overlap(profile)       after both agree: the shared values, or None if they declined
    decline(profile)              tell the other side we said no
    save_receipt(overlap, side)   write the receipt file and return what it holds
    reset(side)                   forget this round
"""
import hashlib
import itertools
import json
import os
import queue
import secrets
import shlex
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

ENGINE_NAME = "PSI (OpenMined, via WSL on Windows)"
ENGINE_PRIVATE = True  # the match check really is private set intersection
ENGINE_SIGNED = False  # True only when receipts are signed with a maintained library.

DEFAULT_PORT = 47321  # a high port: on Windows 5000 is often taken by the system
WAIT_SECONDS = 180
WORKER_START_SECONDS = 90  # the first start of WSL can be slow
WORKER_CALL_SECONDS = 30
MAX_TOKENS = 2000  # 4 stages x 6 sectors x 5 money x 7 places = 840, so real profiles fit
MAX_FRAME = 8 * 1024 * 1024
RECEIPTS = Path(__file__).resolve().parent.parent / "receipts"
WORKER_FILE = Path(__file__).resolve().parent / "psi_worker.py"
MATCH_FIELDS = ("stage", "sector", "money_rm", "geography")
SEEKER_TO_PROVIDER = {"funding": "invest", "partner": "partner", "mentor": "mentor"}
PROVIDER_INTENTS = {"invest", "partner", "mentor"}  # hire_team never matches


class EngineError(RuntimeError):
    pass


# ---------- tokens (plain Python, no cryptography) ----------

def _values(profile: dict, field: str) -> list[str]:
    cleaned = (str(v).strip().lower() for v in profile.get(field) or [])
    return list(dict.fromkeys(v for v in cleaned if v))


def match_tokens(profile: dict) -> list[str]:
    """One token per combination the profile accepts. Empty means this profile can never match."""
    intent = str(profile.get("intent") or "").strip().lower()
    if profile.get("side") == "seeker":
        intent = SEEKER_TO_PROVIDER.get(intent, "")
    elif intent not in PROVIDER_INTENTS:
        intent = ""
    lists = [_values(profile, f) for f in MATCH_FIELDS]
    if not intent or not all(lists):
        return []
    return ["|".join((intent, *combo)) for combo in itertools.product(*lists)]


def reveal_tokens(profile: dict) -> list[tuple[str, str]]:
    return [(f, v) for f in MATCH_FIELDS for v in _values(profile, f)]


def matches(seeker: dict, provider: dict) -> bool:
    """The Match rule in TASKS.md, in plain Python. Used to check the PSI result in tests."""
    return bool(set(match_tokens(seeker)) & set(match_tokens(provider)))


# ---------- the worker that runs the PSI library ----------

def _wsl_path(path: Path) -> str:
    drive, rest = os.path.splitdrive(str(path.resolve()))
    return f"/mnt/{drive[:1].lower()}" + rest.replace("\\", "/")


def worker_command() -> list[str]:
    python = os.environ.get("RAHSIA_WSL_PYTHON") or os.environ.get("RAHSIA_PSI_PYTHON")
    if sys.platform == "win32":
        distro = os.environ.get("RAHSIA_WSL_DISTRO")
        script = f"exec {shlex.quote(python)} \"$0\"" if python else 'exec "$HOME/rahsia-psi/bin/python" "$0"'
        return ["wsl.exe", *(["-d", distro] if distro else []), "--exec", "bash", "-c", script, _wsl_path(WORKER_FILE)]
    return [python or sys.executable, str(WORKER_FILE)]


class Worker:
    """Talks to psi_worker.py through a pipe. One call at a time."""

    def __init__(self, command: list[str] | None = None):
        self._command = command or worker_command()
        self._process: subprocess.Popen | None = None
        self._replies: queue.Queue = queue.Queue()
        self._lock = threading.Lock()
        self._next_id = 0
        self._noise: list[str] = []

    def _read_loop(self, process: subprocess.Popen, replies: queue.Queue) -> None:
        for raw in process.stdout:
            text = raw.decode("utf-8", "replace").replace("\x00", "").strip()
            if text.startswith("{"):
                try:
                    replies.put(json.loads(text))
                    continue
                except ValueError:
                    pass
            if text:
                self._noise = (self._noise + [text])[-5:]
        replies.put({"closed": True})

    def _start(self) -> None:
        try:
            self._process = subprocess.Popen(
                self._command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except OSError as error:
            raise EngineError(f"Could not start the PSI worker: {error}")
        threading.Thread(target=self._read_loop, args=[self._process, self._replies], daemon=True).start()
        first = self._wait(WORKER_START_SECONDS)
        if not first.get("ready"):
            self.close()
            raise EngineError(self._explain("The PSI worker did not start."))

    def _explain(self, message: str) -> str:
        hint = " ".join(self._noise)
        return f"{message} {hint}".strip() + " See the README: 'Run the real match'."

    def _wait(self, seconds: float) -> dict:
        try:
            return self._replies.get(timeout=seconds)
        except queue.Empty:
            self.close()
            raise EngineError(self._explain("The PSI worker did not answer in time."))

    def call(self, op: str, **fields) -> dict:
        with self._lock:
            if self._process is None or self._process.poll() is not None:
                self._replies = queue.Queue()
                self._start()
            self._next_id += 1
            line = json.dumps({"id": self._next_id, "op": op, **fields}) + "\n"
            try:
                self._process.stdin.write(line.encode())
                self._process.stdin.flush()
            except OSError:
                self.close()
                raise EngineError(self._explain("The PSI worker stopped."))
            reply = self._wait(WORKER_CALL_SECONDS)
            if reply.get("closed"):
                self.close()
                raise EngineError(self._explain("The PSI worker stopped."))
            if not reply.get("ok"):
                raise EngineError(f"PSI worker error: {reply.get('error')}")
            return reply

    def close(self) -> None:
        process, self._process = self._process, None
        if process is not None:
            try:
                process.kill()
            except OSError:
                pass


# ---------- the two-laptop engine ----------

class PsiEngine:
    def __init__(self, peer: str | None = None, port: int | None = None,
                 wait_seconds: float | None = None, worker: Worker | None = None):
        self.peer = peer or os.environ.get("RAHSIA_PEER", "127.0.0.1")
        self.port = int(port or os.environ.get("RAHSIA_PSI_PORT", DEFAULT_PORT))
        self.wait_seconds = wait_seconds or WAIT_SECONDS
        self.worker = worker or Worker()
        self._stop = threading.Event()
        self._connection: socket.socket | None = None
        self._listener: socket.socket | None = None

    # connection

    def _close(self) -> None:
        connection, listener = self._connection, self._listener
        self._connection = self._listener = None
        for sock in (connection, listener):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass

    def _timeout_error(self) -> EngineError:
        return EngineError("The other laptop did not connect. Check that it is running, then try again.")

    def _connect(self, side: str) -> None:
        deadline = time.monotonic() + self.wait_seconds
        if side == "seeker":
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._listener = listener
            if sys.platform != "win32":  # on Windows this option would let another program share the port
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(("0.0.0.0", self.port))
            except OSError as error:
                raise EngineError(f"Port {self.port} is busy or blocked: {error}")
            listener.listen(1)
            listener.settimeout(0.5)
            while True:
                if self._stop.is_set():
                    raise EngineError("Cancelled.")
                if time.monotonic() > deadline:
                    raise self._timeout_error()
                try:
                    connection, _ = listener.accept()
                    break
                except socket.timeout:
                    continue
                except OSError:
                    raise EngineError("Cancelled.")
            listener.close()
            self._listener = None
        else:
            while True:
                if self._stop.is_set():
                    raise EngineError("Cancelled.")
                if time.monotonic() > deadline:
                    raise self._timeout_error()
                try:
                    connection = socket.create_connection((self.peer, self.port), timeout=2)
                    break
                except OSError:
                    time.sleep(0.5)
        connection.settimeout(1.0)
        self._connection = connection

    def _send(self, message: dict) -> None:
        data = json.dumps(message).encode()
        try:
            self._connection.sendall(len(data).to_bytes(4, "big") + data)
        except (OSError, AttributeError) as error:
            raise EngineError(f"Lost the connection to the other laptop: {error}")

    def _read(self, size: int) -> bytes:
        deadline = time.monotonic() + self.wait_seconds
        buffer = bytearray()
        while len(buffer) < size:
            if self._stop.is_set():
                raise EngineError("Cancelled.")
            if time.monotonic() > deadline:
                raise self._timeout_error()
            try:
                chunk = self._connection.recv(size - len(buffer))
            except socket.timeout:
                continue
            except (OSError, AttributeError) as error:
                raise EngineError(f"Lost the connection to the other laptop: {error}")
            if not chunk:
                raise EngineError("The other laptop closed the connection.")
            buffer += chunk
        return bytes(buffer)

    def _receive(self, key: str | None = None):
        size = int.from_bytes(self._read(4), "big")
        if size > MAX_FRAME:
            raise EngineError("The other laptop sent too much data.")
        message = json.loads(self._read(size))
        if key is None:
            return message
        if not isinstance(message, dict) or key not in message:
            raise EngineError("The other laptop sent a message this version does not understand.")
        return message[key]

    # one PSI round: one side asks, the other answers

    def _ask(self, items: list[str], reveal: bool) -> dict:
        """I learn the answer. Returns {"size": n} or, when revealing, {"indices": [...]}."""
        self._send({"count": len(items)})
        setup = self._receive("setup")
        request = self.worker.call("client_request", items=items, reveal=reveal)["request"]
        self._send({"request": request})
        response = self._receive("response")
        return self.worker.call("client_finish", setup=setup, response=response, reveal=reveal)

    def _answer(self, items: list[str], reveal: bool) -> None:
        """The other side learns the answer. I learn nothing."""
        count = int(self._receive("count"))
        if not 1 <= count <= MAX_TOKENS:
            raise EngineError("The other laptop sent a set of the wrong size.")
        setup = self.worker.call("server_setup", items=items, count=count, reveal=reveal)["setup"]
        self._send({"setup": setup})
        request = self._receive("request")
        self._send({"response": self.worker.call("server_process", request=request)["response"]})

    def _both_ways(self, side: str, items: list[str], reveal: bool) -> dict:
        """Round 1: the investor asks. Round 2: the startup asks. Each side learns its own answer."""
        if side == "seeker":
            self._answer(items, reveal)
            return self._ask(items, reveal)
        result = self._ask(items, reveal)
        self._answer(items, reveal)
        return result

    # the five functions the screens call

    def run_match(self, profile: dict) -> bool:
        side = profile["side"]
        self._stop.clear()
        self._close()
        # A profile that can never match still runs the same steps, so the other side cannot tell.
        items = match_tokens(profile) or [f"nomatch|{secrets.token_hex(16)}"]
        if len(items) > MAX_TOKENS:
            raise EngineError("This profile accepts too many combinations. Narrow it down.")
        try:
            self._connect(side)
            matched = self._both_ways(side, items, reveal=False)["size"] > 0
        except Exception:
            self._close()
            raise
        if not matched:
            self._close()
        return matched

    def reveal_overlap(self, profile: dict) -> dict | None:
        side = profile["side"]
        try:
            self._send({"agree": True})
            if not self._receive("agree"):
                return None
            pairs = reveal_tokens(profile)
            found = self._both_ways(side, [f"{f}={v}" for f, v in pairs], reveal=True)["indices"]
        finally:
            self._close()
        overlap: dict[str, list[str]] = {f: [] for f in MATCH_FIELDS}
        for index in found:
            field, value = pairs[index]
            overlap[field].append(value)
        return overlap

    def decline(self, profile: dict) -> None:
        try:
            self._send({"agree": False})
            self._finish()
        except EngineError:
            pass
        self._close()

    def _finish(self) -> None:
        """Close politely: a hard close can throw away our 'no' before the other side reads it."""
        try:
            self._connection.shutdown(socket.SHUT_WR)
            self._connection.settimeout(0.5)
            end = time.monotonic() + 2
            while time.monotonic() < end and self._connection.recv(4096):
                pass
        except (OSError, AttributeError):
            pass

    def reset(self) -> None:
        self._stop.set()
        self._close()


# ---------- the names the screens use ----------

_engine: PsiEngine | None = None


def _get() -> PsiEngine:
    global _engine
    if _engine is None:
        _engine = PsiEngine()
    return _engine


def run_match(profile: dict) -> bool:
    return _get().run_match(profile)


def reveal_overlap(profile: dict) -> dict | None:
    return _get().reveal_overlap(profile)


def decline(profile: dict) -> None:
    _get().decline(profile)


def reset(side: str | None) -> None:
    if _engine is not None:
        _engine.reset()


def save_receipt(overlap: dict, side: str) -> dict:
    """Receipt: hashed but not signed yet. Saved in receipts/, which Git ignores."""
    now = datetime.now(timezone.utc).astimezone()
    body = {
        "fields_shared": overlap,
        "other_party": "Investor" if side == "seeker" else "Startup",
        "time": now.isoformat(timespec="seconds"),
        "method": "Private set intersection (OpenMined PSI)",
        "note": "Evidence, not a legal contract.",
    }
    digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    receipt = {**body, "hash": digest, "signature": None}
    RECEIPTS.mkdir(exist_ok=True)
    path = RECEIPTS / f"receipt-{side}-{now:%Y%m%d-%H%M%S}.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return {**receipt, "file": str(path)}
