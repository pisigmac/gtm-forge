# Architecture

## Principles

1. **Pure functions first, execution last.** Parsing, scoring, statistics, and command-building are pure and unit-tested. Network, subprocess, and LLM calls happen at the edges, behind `--dry-run`.
2. **One runtime, many skills.** Resilience, cost tracking, logging, and notifications live in `core/` — a skill gets them by using `build_provider` and `RunContext`, never by re-implementing.
3. **Config over code.** Anything a user might tune — models, prices, thresholds, provider order, stage medians — is YAML, validated by pydantic.
4. **Local-first.** Statistics, ICP scoring, cannibalization, deal health, calendars, and syntax checks run with zero API calls. Paid providers are optional upgrades in a cascade.

## Components

```
┌────────────────────────────────────────────────────────────┐
│ Interfaces: CLI (typer) · REST (fastapi) · Python import   │
├────────────────────────────────────────────────────────────┤
│ Skills (8): growth · eval · seo · video · lead · outbound  │
│             content · sales                                │
├────────────────────────────────────────────────────────────┤
│ LLM layer: Provider protocol                               │
│   └── TrackedProvider = retry + circuit breaker + cost     │
│       ledger + budget enforcement                          │
├────────────────────────────────────────────────────────────┤
│ Core: StateStore (SQLite) · costs · notify · credentials   │
│       updater · JSON logging · RunContext                  │
├────────────────────────────────────────────────────────────┤
│ External: Anthropic / OpenAI / Ollama · ffmpeg/whisper.cpp │
│           NeverBounce/ZeroBounce · Slack/SMTP · GitHub API │
└────────────────────────────────────────────────────────────┘
```

## State

SQLite at `~/.gtm-forge/state.db`: run history, cost ledger, breaker state, key-value store. Schema: `docs/DB_SCHEMA.md`. Experiments and artifacts are plain files under `paths.output_dir` so they diff in git.

## Failure model

| Failure | Behavior |
|---|---|
| LLM timeout/5xx | Retry with backoff+jitter (3x), then breaker records a failure |
| 5 consecutive provider failures | Circuit opens 60s (persisted — survives process restarts) |
| Run exceeds USD budget | `BudgetExceededError`, run marked failed, notification fired |
| Notify channel down | Logged, swallowed — notifications never crash a run |
| Update check offline | Warned, skipped — never blocks a command |

## Extensibility

- New LLM provider: implement `Provider`, register in `llm/factory.py`.
- New skill: new package under `skills/`, sub-app in `cli.py`, entry in `SKILLS`, SKILL.md, tests.
- New verifier: implement `ApiVerifier`, register in `build_cascade`.
