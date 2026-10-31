import json
import socket
import sys
import threading
from pathlib import Path

import pytest

from app import engine

SEEKER = {"side": "seeker", "intent": "funding", "stage": ["pre-seed"], "sector": ["agritech"],
          "money_rm": ["250k-500k", "500k-1m"], "geography": ["malaysia", "indonesia"]}
PROVIDER = {"side": "provider", "intent": "invest", "stage": ["pre-seed", "seed"], "sector": ["agritech", "logistics"],
            "money_rm": ["100k-250k", "250k-500k"], "geography": ["malaysia", "singapore"]}
OVERLAP = {"stage": ["pre-seed"], "sector": ["agritech"], "money_rm": ["250k-500k"], "geography": ["malaysia"]}


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


def test_tokens_cover_every_combination_and_match_the_rule():
    assert len(engine.match_tokens(SEEKER)) == 1 * 1 * 2 * 2
    assert all(t.startswith("invest|") for t in engine.match_tokens(SEEKER))
    assert engine.match_tokens({**SEEKER, "stage": []}) == []


def test_every_real_profile_fits_under_the_size_cap():
    from profile_builder import schema
    biggest = {"side": "seeker", "intent": "funding", "stage": schema.STAGES, "sector": schema.SECTORS,
               "money_rm": schema.MONEY_BUCKETS, "geography": schema.GEOGRAPHIES}
    assert len(engine.match_tokens(biggest)) <= engine.MAX_TOKENS


def test_the_worker_command_runs_the_worker_file():
    assert engine.WORKER_FILE.name in " ".join(engine.worker_command())


@pytest.mark.skipif(sys.platform != "win32", reason="WSL paths are only needed on Windows")
def test_the_wsl_path_of_a_windows_file():
    assert engine._wsl_path(Path("E:/Projects/rahsia/app/psi_worker.py")) == "/mnt/e/Projects/rahsia/app/psi_worker.py"


def test_receipt_has_no_notes_and_stays_honest(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "RECEIPTS", tmp_path)
    receipt = engine.save_receipt({"sector": ["agritech"]}, "seeker")
    saved = json.loads((tmp_path / receipt["file"].rsplit("\\", 1)[-1].rsplit("/", 1)[-1]).read_text(encoding="utf-8"))
    assert saved["fields_shared"] == {"sector": ["agritech"]}
    assert saved["signature"] is None
    assert "not a legal contract" in saved["note"]
    assert len(saved["hash"]) == 64


def test_the_engine_says_private_only_because_it_uses_psi():
    assert engine.ENGINE_PRIVATE is True
    assert engine.ENGINE_SIGNED is False


# ---------- the real thing: two engines, two PSI workers, one TCP connection ----------

@pytest.fixture(scope="module")
def psi_available():
    worker = engine.Worker()
    try:
        worker.call("ping")
    except engine.EngineError as error:
        pytest.skip(f"PSI worker not available here: {error}")
    finally:
        worker.close()


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class Recorded(engine.PsiEngine):
    """An engine that remembers every message it sends to the other laptop."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent: list[str] = []

    def _send(self, message):
        self.sent.append(json.dumps(message))
        super()._send(message)


def run_pair(seeker, provider, seeker_says=True, provider_says=True):
    port = free_port()
    startup = Recorded(port=port, wait_seconds=60)
    investor = Recorded(peer="127.0.0.1", port=port, wait_seconds=60)
    out, errors = {}, []

    def side(name, who, profile, says):
        try:
            matched = who.run_match(profile)
            out[name] = {"matched": matched}
            if matched:
                out[name]["overlap"] = who.reveal_overlap(profile) if says else who.decline(profile)
        except Exception as error:  # a thread must report, not vanish
            errors.append(f"{name}: {error!r}")

    threads = [threading.Thread(target=side, args=("seeker", startup, seeker, seeker_says)),
               threading.Thread(target=side, args=("provider", investor, provider, provider_says))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    for who in (startup, investor):
        who.worker.close()
    assert not errors, errors
    return out, startup.sent + investor.sent


def test_a_match_reveals_exactly_the_overlap_after_both_agree(psi_available):
    out, _ = run_pair(SEEKER, PROVIDER)
    assert out["seeker"] == {"matched": True, "overlap": OVERLAP}
    assert out["provider"] == {"matched": True, "overlap": OVERLAP}


def test_no_match_means_both_sides_learn_only_no(psi_available):
    out, sent = run_pair(SEEKER, {**PROVIDER, "sector": ["fintech"]})
    assert out == {"seeker": {"matched": False}, "provider": {"matched": False}}
    wire = " ".join(sent)
    for word in ("agritech", "fintech", "malaysia", "pre-seed", "250k-500k", "invest", "funding"):
        assert word not in wire


def test_no_profile_value_crosses_the_wire_in_clear_even_on_a_match(psi_available):
    _, sent = run_pair(SEEKER, PROVIDER)
    wire = " ".join(sent)
    for word in ("agritech", "logistics", "indonesia", "singapore", "pre-seed", "500k-1m"):
        assert word not in wire


def test_a_profile_that_can_never_match_looks_the_same_to_the_other_side(psi_available):
    out, _ = run_pair({**SEEKER, "stage": []}, PROVIDER)
    assert out == {"seeker": {"matched": False}, "provider": {"matched": False}}


def test_one_side_saying_no_reveals_nothing_to_either(psi_available):
    out, sent = run_pair(SEEKER, PROVIDER, provider_says=False)
    assert out["seeker"] == {"matched": True, "overlap": None}
    assert out["provider"] == {"matched": True, "overlap": None}
    assert "agritech" not in " ".join(sent)


def test_the_other_laptop_not_coming_gives_a_clear_error():
    lone = engine.PsiEngine(port=free_port(), wait_seconds=0.6)
    with pytest.raises(engine.EngineError, match="did not connect"):
        lone.run_match(SEEKER)
    investor = engine.PsiEngine(peer="127.0.0.1", port=free_port(), wait_seconds=0.6)
    with pytest.raises(engine.EngineError, match="did not connect"):
        investor.run_match(PROVIDER)
