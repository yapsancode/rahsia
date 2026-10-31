import json
import threading

import pytest

from app import engine

SEEKER = {"side": "seeker", "intent": "funding", "stage": ["pre-seed"], "sector": ["agritech"],
          "money_rm": ["250k-500k", "500k-1m"], "geography": ["malaysia", "indonesia"]}
PROVIDER = {"side": "provider", "intent": "invest", "stage": ["pre-seed", "seed"], "sector": ["agritech", "logistics"],
            "money_rm": ["100k-250k", "250k-500k"], "geography": ["malaysia", "singapore"]}


def test_a_fitting_pair_matches():
    assert engine.matches(SEEKER, PROVIDER)


@pytest.mark.parametrize("change", [
    {"intent": "hire_team"},
    {"intent": "partner"},
    {"intent": None},
    {"stage": ["series-a"]},
    {"sector": ["fintech"]},
    {"money_rm": ["over-1m"]},
    {"geography": ["vietnam"]},
    {"geography": []},
])
def test_any_failed_check_means_no_match(change):
    assert not engine.matches(SEEKER, {**PROVIDER, **change})


def test_two_sides_are_compared_and_each_learns_only_the_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "_folder", tmp_path)
    other = threading.Thread(target=lambda: engine._write("provider.profile", json.dumps(PROVIDER)))
    other.start()
    assert engine.run_match(SEEKER) is True
    other.join()
    assert not (tmp_path / "provider.profile").exists()


def test_overlap_holds_only_shared_values(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "_folder", tmp_path)
    monkeypatch.setattr(engine, "_other_profile", PROVIDER)
    engine._write("provider.agree", "yes")
    assert engine.reveal_overlap(SEEKER) == {"stage": ["pre-seed"], "sector": ["agritech"],
                                             "money_rm": ["250k-500k"], "geography": ["malaysia"]}


def test_a_decline_returns_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "_folder", tmp_path)
    monkeypatch.setattr(engine, "_other_profile", PROVIDER)
    engine._write("provider.decline", "no")
    assert engine.reveal_overlap(SEEKER) is None


def test_the_other_laptop_not_coming_gives_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "_folder", tmp_path)
    monkeypatch.setattr(engine, "WAIT_SECONDS", 0.01)
    with pytest.raises(engine.EngineError, match="did not connect"):
        engine.run_match(SEEKER)
    assert not (tmp_path / "seeker.profile").exists()


def test_receipt_has_no_notes_and_stays_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "RECEIPTS", tmp_path)
    receipt = engine.save_receipt({"sector": ["agritech"]}, "seeker")
    saved = json.loads((tmp_path / receipt["file"].rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_text(encoding="utf-8"))
    assert saved["fields_shared"] == {"sector": ["agritech"]}
    assert saved["signature"] is None
    assert "not a legal contract" in saved["note"]
    assert len(saved["hash"]) == 64


def test_the_stand_in_never_calls_itself_private():
    assert engine.ENGINE_PRIVATE is False
