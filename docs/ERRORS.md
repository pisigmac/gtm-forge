# Errors & Exit Codes

## Exit codes (public API — stable within a major version)

| Code | Meaning | Raised by |
|---|---|---|
| 0 | Success | all commands |
| 1 | Generic failure (config invalid, missing tool, provider error, budget exceeded) | any command |
| 2 | CLI usage error (bad flags) | typer |
| 3 | Content below the eval gate — revise or kill | `gtm eval` |
| 4 | Email invalid or disposable — do not send | `gtm lead verify` |

## Exception taxonomy

| Exception | Module | When | User action |
|---|---|---|---|
| `LLMError` | `llm.base` | Provider misconfigured or request failed | Run `gtm doctor`; check keys and `llm.*` config |
| `CredentialError` | `core.credentials` | Required secret missing | Set the env var or `gtm keys set NAME` |
| `BudgetExceededError` | `core.costs` | Run passed `costs.budget_usd_per_run` | Raise the budget or trim the run |
| `CircuitOpenError` | `core.breaker` | Provider circuit open after repeated failures | Wait out the cooldown; check provider status |
| `ValueError` | skills | Bad input data (too few observations, unknown variant, malformed CSV) | Fix the input — the message says how |
| `FileNotFoundError` | skills | Missing experiment/CSV/transcript | Check the path printed in the message |

## Log format

All logs are JSON lines on stderr: `{"ts", "level", "logger", "msg", "run_id", "skill", ...}`. Grep by `run_id` to trace one run end to end.

## Notification behavior

Failures trigger notifications when `notifications.on_failure: true` (default) and a channel is configured. Notification failures are logged and swallowed — they never change an exit code.
