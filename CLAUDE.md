# rahsia

Private matchmaking for startups and investors on local Gemma 4. Idea stage. Read IDEA.md and SPEC.md before any work. Work only on the current phase in SPEC.md.

## Stack
Docs only until the hack day. Planned: Gemma 4 (E4B, 12B) through a local runner, a maintained PSI library, a small local web UI. Nothing is chosen yet; do not pick a stack without asking.

## Claims (strict)
- Never write or say that Rahsia stops idea theft. It reduces early sharing and records what was shared.
- Never say "private" for anything that only hashes small tag lists. Use a maintained PSI library. No custom cryptography.
- The receipt is evidence, not a legal contract.
- Mark every number as checked (with source and date) or unverified.

## Privacy rules
- Profile building and matching run on the user's laptop with open-weight models. No call to a cloud AI API for profile or match data.
- Secrets go in .env files, never in code, never committed. Keys for receipts stay out of git.
- Never put real people's names, real pitch decks or real investor data in the repo. Use fake data only.

## Evaluation rules
- Write the pass rule before reading any result. Changing it after is not allowed.
- The answer key is written by hand before the model runs.
- Run a model twice on the same input first to measure how much it disagrees with itself.
- Check model output in code (schema, language). Repair safe things in code instead of retrying.
- Test inputs must include English, Malay and mixed notes, and one hidden prompt-injection line.

## Hack day
- Event: 31 Oct 2026, sprint 11:00-15:00, submit by 15:00, finalist demo 5 minutes.
- Check the organisers' rules on pre-written code before adding any code to this repo.

## Git
- Private repo, account yapsancode. Commit messages: `type: short summary`.
