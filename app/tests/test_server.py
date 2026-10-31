import time

import pytest
from fastapi.testclient import TestClient

from app import engine, server
from profile_builder.builder import BuildResult
from profile_builder.schema import Profile

PROFILE = {"side": "seeker", "intent": "funding", "stage": ["seed"], "sector": ["fintech"],
           "money_rm": ["100k-250k"], "geography": ["malaysia"], "timeline_months": None,
           "deal_breakers": "", "disclosure": "", "reviewed": False}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "_folder", tmp_path)
    monkeypatch.setattr(engine, "RECEIPTS", tmp_path / "receipts")
    monkeypatch.setattr(server.client, "model_state", lambda model: "ready")
    with TestClient(server.app, base_url="http://127.0.0.1:8001") as test_client:
        test_client.post("/api/reset")
        yield test_client


def wait_for(client, phase):
    for _ in range(100):
        state = client.get("/api/state").json()
        if state["phase"] == phase:
            return state
        time.sleep(0.02)
    raise AssertionError(f"never reached {phase}: {state}")


def test_another_site_cannot_reach_the_server():
    with TestClient(server.app, base_url="http://evil.example") as other:
        assert other.get("/api/config").status_code == 400


def test_config_tells_the_page_the_engine_is_not_private(client):
    body = client.get("/api/config").json()
    assert body["engine"]["private"] is False
    assert body["choices"]["seeker_intent"] == ["funding", "partner", "mentor"]
    assert [s["name"] for s in body["samples"]["provider"]] == ["provider_ms"]


def test_the_page_can_ask_if_gemma_is_ready(client):
    assert client.get("/api/gemma").json() == {"state": "ready"}


def test_the_page_is_served(client):
    assert "Who is using this laptop?" in client.get("/").text


def test_profile_comes_back_with_warnings(client, monkeypatch):
    result = BuildResult(Profile(**PROFILE), warnings=["a warning"], seconds=1.5)
    monkeypatch.setattr(server, "build_profile", lambda notes, side: result)
    body = client.post("/api/profile", json={"notes": "fake", "side": "seeker"}).json()
    assert body["profile"]["intent"] == "funding"
    assert body["warnings"] == ["a warning"]


def test_a_file_comes_back_as_text(client):
    response = client.post("/api/read", content="kami buat sensor".encode(), headers={"X-File-Kind": "txt"})
    assert response.json() == {"text": "kami buat sensor"}


def test_a_bad_file_gives_a_clear_message(client):
    response = client.post("/api/read", content=b"MZ\0\0binary", headers={"X-File-Kind": "exe"})
    assert response.status_code == 422
    assert "not a text file" in response.json()["detail"]


def test_gemma_being_down_gives_a_clear_message(client, monkeypatch):
    def down(notes, side):
        raise server.RunnerError("no runner")
    monkeypatch.setattr(server, "build_profile", down)
    response = client.post("/api/profile", json={"notes": "fake", "side": "seeker"})
    assert response.status_code == 503
    assert "Start Ollama" in response.json()["detail"]


def test_a_bad_profile_is_refused(client):
    response = client.post("/api/match", json={"profile": {**PROFILE, "sector": ["not a sector"]}})
    assert response.status_code == 422


def test_full_round(client, monkeypatch):
    monkeypatch.setattr(engine, "run_match", lambda profile: True)
    monkeypatch.setattr(engine, "reveal_overlap", lambda profile: {"sector": ["fintech"]})
    assert client.post("/api/match", json={"profile": PROFILE}).status_code == 200
    wait_for(client, "matched")
    client.post("/api/agree")
    assert wait_for(client, "revealed")["overlap"] == {"sector": ["fintech"]}
    assert client.post("/api/receipt").json()["fields_shared"] == {"sector": ["fintech"]}


def test_no_match_shows_nothing_else(client, monkeypatch):
    monkeypatch.setattr(engine, "run_match", lambda profile: False)
    client.post("/api/match", json={"profile": PROFILE})
    state = wait_for(client, "no_match")
    assert state["overlap"] is None
    assert client.post("/api/agree").status_code == 409
    assert client.post("/api/receipt").status_code == 409


def test_an_engine_error_reaches_the_page(client, monkeypatch):
    def broken(profile):
        raise engine.EngineError("The other laptop did not connect.")
    monkeypatch.setattr(engine, "run_match", broken)
    client.post("/api/match", json={"profile": PROFILE})
    assert "did not connect" in wait_for(client, "error")["error"]


def test_a_cancelled_round_cannot_change_the_next_one(client, monkeypatch):
    server._set(server.state.number - 1, phase="matched")
    assert client.get("/api/state").json()["phase"] == "idle"
