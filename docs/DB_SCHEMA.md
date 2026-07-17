# Database Schema

SQLite at `~/.gtm-forge/state.db` (configurable: `paths.state_db`). Managed by `gtm_forge.core.state.StateStore`. Migrations are additive `CREATE TABLE IF NOT EXISTS` — safe to open with any version.

## runs

| Column | Type | Notes |
|---|---|---|
| run_id | TEXT PK | 12-char hex, one per CLI invocation |
| skill | TEXT | e.g. `eval`, `experiment` |
| command | TEXT | subcommand name |
| status | TEXT | running / success / failed |
| dry_run | INTEGER | 1 if `--dry-run` |
| started_at | TEXT | ISO-8601 UTC |
| finished_at | TEXT | nullable |
| error | TEXT | nullable |

## costs

| Column | Type | Notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| run_id | TEXT | FK -> runs.run_id |
| model | TEXT | e.g. claude-sonnet-4-5 |
| input_tokens | INTEGER | |
| output_tokens | INTEGER | |
| cost_usd | REAL | computed at call time from the config price table |
| ts | TEXT | ISO-8601 UTC |

## breaker

| Column | Type | Notes |
|---|---|---|
| name | TEXT PK | e.g. `llm:anthropic` |
| state | TEXT | closed / open / half-open |
| failures | INTEGER | consecutive failures |
| opened_at | TEXT | when the circuit last opened |

## kv

| Column | Type | Notes |
|---|---|---|
| key | TEXT PK | free-form |
| value | TEXT | JSON-encoded payloads allowed |

## Artifacts (not in SQLite)

Experiments are JSON files in `<output_dir>/experiments/`; reports, briefs, calendars, dossiers, and clip manifests are plain files under `<output_dir>/`. Nothing precious lives only in the database — it is a ledger, not a source of truth.
