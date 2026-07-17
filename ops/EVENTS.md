# Events

All events are JSON lines on stderr (see `docs/ERRORS.md` for format) plus state-table records.

## Event catalog

| Event | Carrier | Fields |
|---|---|---|
| `run started` | log + `runs` row | run_id, skill, command, dry_run |
| `run finished` | log + `runs` row | run_id, status, cost_usd |
| `llm call` | log + `costs` row | run_id, model, input/output tokens, cost_usd |
| breaker open/half-open/close | `breaker` row | name, state, failures, opened_at |
| notification sent | log | channel, success |

## Consuming events

- **Local:** `gtm costs runs`, `gtm costs report`.
- **Pipes:** stderr is JSON — `gtm eval ... 2>> events.jsonl` gives you an event stream.
- **Alerting:** turn on `notifications.on_failure` with a Slack webhook for cron jobs.

## Naming

Snake-case nouns, past tense for completions (`run finished`), present tense for starts (`run started`). New events must be documented here and must never include secrets or PII payloads.
