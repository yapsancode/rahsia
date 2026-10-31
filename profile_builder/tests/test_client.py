import http.server
import threading

import pytest

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
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"message": {"content": "ok"}}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


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
