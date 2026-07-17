# Future Plan

## Near term (0.2.x)

- **Video: OpenAI Whisper path** — `video.whisper: openai` config exists; wire the API call so users without whisper.cpp can transcribe.
- **Short-form converter** — layout-aware 9:16 crops (talking head, screen share, side-by-side, gallery) on top of the clip pipeline.
- **Experiment power calculator** — required sample size given baseline, MDE, and alpha (pure math, no new deps).
- **`gtm report`** — weekly digest: runs, spend, verdicts, generated as markdown from the ledger.

## Mid term (0.3.x)

- **Cross-signal detector** — correlate call notes, CRM stages, and content engagement to surface deals warming up.
- **Humanizer lint** — pattern detector for AI-sounding marketing copy (rule-based, offline).
- **YouTube competitive analysis** — public-data channel comparison reports.
- **Sequence send integration** — optional send-platform adapters behind the same cascade pattern as email verification.

## Longer term (0.4+)

- **Web dashboard** — read-only UI over `state.db` and artifacts. Deliberately deferred: CLI first.
- **Team mode** — shared Postgres state backend as an alternative to SQLite (schema already isolated in `core/state.py`).
- **Plugin SDK** — third-party skills discovered via entry points.

## Explicit non-goals

- No hosted SaaS fork of the tool itself.
- No telemetry/phone-home, ever.
- No scraping behind logins. Public web + user-provided data only.

## How to propose a feature

Open an issue with: the marketing job-to-be-done, why existing skills can't do it, and whether it needs an LLM. Pure-Python features ship fastest.
