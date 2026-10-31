# rahsia — spec

**Goal:** Let a startup and an investor check if they fit, privately on their own laptops with Gemma 4, before revealing anything; then draft the intro and keep a receipt of what was shared.
**Users:** Seekers (startups, candidate teams) and providers (investors, accelerators, angel groups).

## Phase 1 — Prepare before the hack day (open items below still needed, mainly the answer key)
- [ ] Message the KrackedDevs organisers: can our team stay together? Is code pre-work allowed?
- [ ] Teammate registers on MLH (each person registers alone)
- [ ] Interview 2-3 investors/accelerator staff: pitches per month, pitches read
- [ ] Interview 3 founders: what they hid in their last pitch and why
- [ ] Write the answer key: 30 fake profile pairs with the correct match answer
- [ ] Write 20 messy notes (English, Malay, mixed) with the correct profile fields
- [ ] Search competitors properly and write the findings in IDEA.md section 12
- [ ] Pick the PSI library and the model runner; pre-download Gemma 4 E4B and 12B
- [ ] Share the proposal with the team (message in IDEA.md pitch)

## Phase 2 — Hack day sprint, 31 Oct 11:00-15:00 (current)
- [x] Profile builder: notes in, schema-checked JSON out (`profile_builder/`, first version; not yet scored, no answer key exists)
- [ ] Private match check on bucketed fields
- [x] Two-role screen (seeker, provider): `app/`, six steps, tested with Gemma; waits for the real match engine
- [x] Draft generator using only the shared overlap (`profile_builder/draft.py`, first version; not yet scored). It also writes a first-call agenda
- [x] Notes can come from a file: text files, `.pdf`, `.docx` (`app/reader.py`)
- [ ] Disclosure receipt (hash, time, signature)
- [ ] Measure: match accuracy, leakage, profile quality, invented facts, speed
- [ ] Submit before 15:00; prepare the 5-minute demo

## Later
- Voice input with Gemma native audio
- Malay and Mandarin mixed notes
- Provider short list across many startups
- Pilot Passport (turn a match into a pilot plan and track conversion)
- Grant Autopilot (same private-profile idea for grants)
- First pilot with one accelerator

## Decisions
- 2026-10-29: docs-only start (no webapp/python/static-site preset) — only an idea so far, and the event may limit pre-written code.
- 2026-10-29: private GitHub repo — the idea and plans are not public yet.
- 2026-10-29: pick Startup ASEAN Problem 1 (outcome conversion) — private first contact is where connections fail.
- 2026-10-29: never claim it stops idea theft — it reduces early sharing and records what was shared.
- 2026-10-29: use a maintained PSI library, no custom cryptography — hashing small tag lists is not private.
- 2026-10-31: public landing page in `site/` (Astro 6, static, Cloudflare Worker named `rahsia`). Isyraf asked for it, chose Astro, and confirmed code before the sprint was allowed. This choice is for the page only; the app stack is still open. Astro 6 because Astro 7 needs Node 22.23+.
- 2026-10-31: Phase 2 is current (Isyraf confirmed). Profile builder uses Python 3.11 + pydantic and Ollama (`gemma4:e4b`, localhost only). Errors are repaired in code, never retried. Other parts of the app stack are still open.
- 2026-10-31: web UI is a local FastAPI server with plain HTML, CSS and JS in `app/`, because Isyraf asked for a beautiful UI with no limits, and the demo runs with the internet off, so nothing may load from a CDN. Isyraf owns the UI. The match engine plugs in through `app/engine.py`, which is a stand-in and says on screen that it is not private until the real PSI engine replaces it.
- 2026-10-31: run all Gemma layers on the GPU (`num_gpu` 99) and return one-line JSON. Checked on Isyraf's laptop (GTX 1650, 4 GB) on 2026-10-31, on 3 fake notes: a profile went from about 21 seconds to about 3 to 4, and a draft with agenda takes about 2 to 4. It uses 3.8 GB of the 4 GB, so a smaller GPU falls back to Ollama's own split. The teammate's laptop is unverified. The app loads Gemma when it starts, because a cold load takes about 32 seconds.
- 2026-10-31: after both agree, the app gives a first-call agenda as well as the draft, because Isyraf wanted more than a message. Both use only the overlap.
- 2026-10-31: profile builder output follows the Shared fields in TASKS.md (Isyraf approved the fix). Money buckets are computed in code. Injection text is removed before the model reads the notes, and a value is kept only if words in the notes support it, because in testing Gemma obeyed an injection and filled blank fields even with prompt rules against both.
