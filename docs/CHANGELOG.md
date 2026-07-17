# Changelog

All notable changes to gtm-forge. Semver; exit codes and config keys are public API.

## [0.1.0] - 2026-07-17

Initial public release.

### Fixed (pre-release hardening)

- `typer>=0.16.0` floor: typer 0.15.x crashes rendering `--help` against click 8.2+.
- `gtm experiment add|analyze|decide` with an unknown experiment ID now exits 1 with a clean message instead of a `FileNotFoundError` traceback.
- JSON log handler re-resolves `sys.stderr` on every emit, so repeated invocations under stream-swapping runners never hit "Logging error" noise.

### Added

- Unified `gtm` CLI with 8 skills: growth experiments, content eval, SEO ops, video clips, lead intel, outbound engine, content ops, sales pipeline.
- Statistics engine: percentile bootstrap CIs and Mann-Whitney U (tie-corrected, continuity-corrected) with SHIP/KILL/INCONCLUSIVE verdicts.
- Provider-agnostic LLM layer (Anthropic, OpenAI, Ollama) wrapped with retry + jitter, persisted circuit breaker, per-call cost ledger, and per-run USD budgets.
- `--dry-run` on every skill with JSON plans and token estimates.
- SQLite state: run history, cost ledger, breaker state, kv store.
- Slack/email failure notifications, OS-keychain secret storage, self-update from GitHub Releases.
- Optional REST API (`gtm serve`) with OpenAPI spec.
- Agent integration: `gtm skills install` writes 8 SKILL.md files.
- Full documentation set (`docs/`, `ops/`), 80+ tests, CI on Python 3.11-3.13.
