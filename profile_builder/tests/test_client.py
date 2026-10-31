import http.server
import json
import threading

import pytest

from profile_builder import client
from profile_builder.client import RunnerError, chat, runner_url


def test_localhost_is_allowed(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
    assert runner_url() == "http://127.0.0.1:11434"
    monkeypatch.setenv("OLLAMA_HOST", "http://localhost:9999")
    assert runner_url() == "http://localhost:9999"


@pytest.mark.parametrize("host", ["http://example.com:11434", "192.168.1.20:11434", "0.0.0.0:11434"])
def test_other_hosts_are_refused(monkeypatch, host):
    monkeypatch.setenv("OLLAMA_HOST", host)
    with pytest.raises(RunnerError):
        runner_url()


def _server(calls):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            calls.append(self.path)
            # Read the body first: on Windows, closing with unread data aborts the connection.
            self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": {"content": "ok"}}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def _small_gpu_server(bodies):
    """Refuses a request for the full GPU, as Ollama does when the model will not fit."""
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            bodies.append(body)
            self.send_response(500 if "num_gpu" in body["options"] else 200)
            self.end_headers()
            self.wfile.write(b'{"message": {"content": "ok"}}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_a_small_gpu_falls_back_once_and_stays_there(monkeypatch):
    bodies = []
    server = _small_gpu_server(bodies)
    monkeypatch.setenv("OLLAMA_HOST", f"127.0.0.1:{server.server_port}")
    monkeypatch.setattr(client, "_full_gpu", True)
    try:
        assert chat("m", "s", "u", {}) == "ok"
        assert chat("m", "s", "u", {}) == "ok"
    finally:
        server.shutdown()
    assert ["num_gpu" in body["options"] for body in bodies] == [True, False, False]


def test_every_call_sends_the_same_loading_options(monkeypatch):
    bodies = []
    server = _small_gpu_server(bodies)
    monkeypatch.setenv("OLLAMA_HOST", f"127.0.0.1:{server.server_port}")
    monkeypatch.setattr(client, "_full_gpu", False)
    try:
        client.warm_up("m")
        chat("m", "s", "u", {})
    finally:
        server.shutdown()
    assert bodies[0]["options"]["num_ctx"] == bodies[1]["options"]["num_ctx"]
    assert bodies[0]["keep_alive"] == bodies[1]["keep_alive"]


def test_a_proxy_setting_is_ignored(monkeypatch):
    ollama_calls, proxy_calls = [], []
    ollama, proxy = _server(ollama_calls), _server(proxy_calls)
    monkeypatch.setenv("OLLAMA_HOST", f"127.0.0.1:{ollama.server_port}")
    monkeypatch.setenv("HTTP_PROXY", f"http://127.0.0.1:{proxy.server_port}")
    monkeypatch.setenv("http_proxy", f"http://127.0.0.1:{proxy.server_port}")
    try:
        assert chat("m", "s", "secret notes", {}) == "ok"
    finally:
        ollama.shutdown()
        proxy.shutdown()
    assert ollama_calls == ["/api/chat"]
    assert proxy_calls == []
