# Feature Index

## Core runtime (shared by every skill)

| Feature | What it does | Where |
|---|---|---|
| Unified CLI | One `gtm` binary, sub-app per skill | `src/gtm_forge/cli.py` |
| YAML config | Pydantic-validated, env-overridable | `config.py` |
| Dry-run | Plan + cost preview on every skill, no side effects | `--dry-run` flag |
| Cost ledger | Per-call token + USD accounting in SQLite | `core/costs.py`, `core/state.py` |
| Run budgets | Hard stop when a run exceeds `budget_usd_per_run` | `core/costs.py` |
| Circuit breaker | Persisted closed/open/half-open per provider | `core/breaker.py` |
| Retry | Exponential backoff with full jitter | `core/breaker.py` |
| Notifications | Slack webhook + SMTP on failure (opt-in) | `core/notify.py` |
| Secrets | Env vars first, OS keychain second | `core/credentials.py` |
| Self-update | Checks GitHub Releases, upgrades via uv/pipx | `core/updater.py` |
| Structured logs | JSON lines to stderr with run IDs | `core/logging.py` |
| Feature flags | `features.flags` in config, `Settings.features.enabled()` | `config.py` |
| Init wizard | `gtm init` interviews and writes config | `cli.py` |
| Doctor | Verifies config, keys, ffmpeg, whisper, version | `cli.py` |

## Skills

1. **experiment** — bootstrap CI + Mann-Whitney U; SHIP/KILL/INCONCLUSIVE verdicts; JSON-file experiment store.
2. **eval** — 7-expert JSON-scored panel, configurable gate, markdown reports, exit code 3 below gate.
3. **seo** — LLM attack briefs; Jaccard-based cannibalization detection from CSV.
4. **video** — whisper.cpp transcription, LLM hook scoring, ffmpeg cuts, manifest output.
5. **lead** — public-web dossiers (tech fingerprints, hiring, socials); cascade email verification with audit trail.
6. **outbound** — explainable ICP scoring (exact/keyword/range weights in YAML); LLM sequences grounded in fit reasons.
7. **content** — editorial calendars; deterministic offline mode + LLM creative mode on the same day grid.
8. **sales** — transparent deal-health scoring with reasons; departed-champion re-engagement with LLM-drafted notes.

## Interfaces

- CLI (primary), REST API (`gtm serve`, OpenAPI in `docs/openapi.yaml`), Python import (`from gtm_forge.skills.growth.stats import analyze`).
