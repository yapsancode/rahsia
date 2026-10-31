import pytest

from profile_builder.client import RunnerError, runner_url


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
