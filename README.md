# Rahsia

Private matchmaking for startups and investors. Each side runs Gemma 4 on their own laptop and checks if they fit **before** revealing anything. No match: nothing is learned. Match: the AI drafts the intro and saves a receipt of what was shared.

*Rahsia* is Malay for "secret".

- **Event:** Hacktoberfest Hack Day Kuala Lumpur, 31 Oct 2026
- **Problem statement:** Startup ASEAN, Problem 1 (outcome conversion)
- **Category:** Best Open-Source AI Project (open-weight model, run locally)
- **Licence:** [MIT](LICENSE)
- **Full idea, demo plan and limits:** [IDEA.md](IDEA.md)

## The problem

Founders hold back real details in a first pitch because they fear the idea will be copied, and they often do not know what the other side really wants (invest, partner, or hire the team). Investors hold back their real budget and focus. So the first meeting is shallow, and many connections never reach a real conversation.

## How it works

```
messy notes -> Gemma 4 (local) -> clean profile (JSON, checked by schema)
            -> buckets -> private match check (PSI) -> match / no match
            -> if both agree: draft intro -> disclosure receipt
```

1. **Profile builder.** Gemma 4 turns messy notes (English, Malay or mixed) into a profile. Code checks the JSON against a schema. The person reviews it before it counts.
2. **Private match check.** A maintained PSI library compares bucketed fields (stage, sector, money range, geography, intent). Each side learns only match or no match.
3. **Draft and receipt.** After both sides agree, Gemma drafts an intro using only the shared overlap. A signed, time-stamped receipt records what was shared.

Before a match, profile data stays on the laptop: the runner client refuses any host that is not this machine, and it ignores proxy settings. After both sides agree, only the overlap is shared.

## Status

This is a hack-day build. Update this table as parts land.

| Part | Status |
|---|---|
| Profile builder (`profile_builder/`) | In progress |
| Private match check (PSI) | Not started |
| Two-role screen (`app/`) | First version, runs on a stand-in match engine |
| Draft and first-call agenda | First version, not yet scored |
| Disclosure receipt | Stand-in: hashed, not signed yet |
| Landing page (`site/`) | Done |

## Run it

### Requirements

- Python 3.11 or newer
- [Ollama](https://ollama.com) running on the same laptop
- Gemma 4 E4B pulled once: `ollama pull gemma4:e4b` (6.6 GB on disk, download before the event)

### The app

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows. On macOS or Linux: source .venv/bin/activate
pip install -r app/requirements.txt
python -m app --port 8001 --open
```

The app loads Gemma when it starts, which takes about 30 seconds. The left side shows when it is ready. Notes can be typed, or loaded from a text file, `.pdf` or `.docx`. A scanned PDF has no text to read.

Gemma runs fully on the GPU by default. If the model does not fit, the app falls back to Ollama's own split, which is slower. To turn it off, set `RAHSIA_FULL_GPU=0`.

Each person runs their own copy. To try both sides on one laptop, run a second copy with `--port 8002` and pick the other side. The match step uses a stand-in in `app/engine.py` until the PSI engine is plugged in. **The stand-in is not private**, and the screens say so.

### Profile builder only

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows. On macOS or Linux: source .venv/bin/activate
pip install -r profile_builder/requirements.txt
python -m profile_builder --side seeker --file notes.txt --out profile.json
```

The output uses the Shared fields in [TASKS.md](TASKS.md), plus `reviewed`. Exact amounts become `money_rm` buckets, so the profile does not hold them.

Useful options:

- `--side seeker|provider` is required.
- `--twice` runs the model two times and shows where it disagrees with itself.
- `--model` picks another Ollama model (default `gemma4:e4b`).
- `--yes` marks the profile as reviewed without asking.

Run the tests with `python -m pytest`.

The repo uses fake data only. Do not put real people, real pitch decks or real investor data in it.

## Honest limits

- Rahsia **does not stop idea theft.** It reduces early sharing and records what was shared.
- The privacy is **demo level**, not bank-grade. After a match is revealed, the other side knows what was shared and we cannot take it back.
- Money is matched in ranges (buckets), not exact amounts.
- The receipt is evidence, not a legal contract.
- A small local model can misread messy notes, so the person must review the profile.
- Results are reported in [IDEA.md](IDEA.md) section 8 as real numbers once measured. Until then they are targets, not results.

## Repo guide

| Path | What it is |
|---|---|
| `app/` | The six-step app: a local server and the screens. `app/engine.py` is the plug for the match engine |
| `profile_builder/` | Notes to checked profile JSON, and the intro draft, using Gemma 4 through a local Ollama server |
| `site/` | Public landing page (Astro, Cloudflare) |
| `IDEA.md` | The full idea, demo plan, numbers and limits |
| `SPEC.md` | Plan and decisions |
| `TASKS.md` | Team task list for the hack day |
| `LICENSE` | MIT |

## Licence

MIT. See [LICENSE](LICENSE).
