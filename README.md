# gtm-forge

Production-grade, config-driven GTM and AI marketing skills. One CLI, eight skills, zero lock-in.

Most "AI marketing toolkits" are loose folders of demo scripts. gtm-forge is the opposite: an installable Python package where every skill shares the same runtime — retries, circuit breaking, cost tracking, dry-run mode, structured logs, and a real test suite.

## Why teams pick it up fast

- **One command to learn.** `gtm <skill> <command>`. Every skill works the same way.
- **`--dry-run` everywhere.** See the exact plan — prompts, ffmpeg commands, estimated tokens — before anything runs or costs a cent.
- **No paid dependencies to start.** Local transcription, heuristic tech detection, free email syntax checks, deterministic calendar mode. Add API keys when you want more.
- **Bring your own model.** Anthropic, OpenAI, or fully-local Ollama. Switch with one line of YAML.
- **It fails like grown-up software.** Persisted circuit breakers, per-run budgets, exit codes you can build CI on, and a cost ledger in SQLite.

## Install

```bash
# uv (recommended)
uv tool install gtm-forge

# pipx
pipx install gtm-forge

# plain pip, with an LLM provider and the REST API
pip install "gtm-forge[anthropic,serve]"
```

## Sixty-second quickstart

```bash
gtm init --yes                      # writes ~/.gtm-forge/config.yaml
export ANTHROPIC_API_KEY=...        # or use ollama for fully local runs
gtm doctor                          # verifies config, keys, ffmpeg, updates

# your first experiment (no API key needed — statistics are local)
gtm experiment create --name "Thread test" \
  --hypothesis "Threads beat single posts" --variable format \
  --variants single,thread --metric impressions
gtm experiment add <id> --variant single --values 100,120,110,105,115,108,112,118
gtm experiment add <id> --variant thread --values 150,160,170,155,165,175,158,162
gtm experiment analyze <id>         # bootstrap CI + Mann-Whitney, plain-English verdict

# preview an LLM run without spending anything
gtm --dry-run eval --idea "10 lessons from 100 podcast episodes"
```

## The eight skills

| Skill | Command | What it does |
|---|---|---|
| Growth experiments | `gtm experiment` | Bootstrap confidence intervals + Mann-Whitney U. Verdicts: SHIP / KILL / INCONCLUSIVE. |
| Content eval | `gtm eval` | 7-expert panel scores an idea; exits non-zero below your gate (default 90). |
| SEO ops | `gtm seo` | Attack briefs; keyword cannibalization detection across your pages. |
| Video clips | `gtm video clips` | whisper.cpp transcription → LLM hook scoring → ffmpeg cuts, with a manifest. |
| Lead intel | `gtm lead` | Company dossiers from public signals; cascade email verification. |
| Outbound | `gtm outbound` | Explainable ICP scoring from YAML weights; sequence generation. |
| Content ops | `gtm content calendar` | Editorial calendars — LLM creative mode or deterministic offline mode. |
| Sales pipeline | `gtm sales` | Transparent deal-health scoring; departed-champion re-engagement. |

## Configuration

One YAML file at `~/.gtm-forge/config.yaml` controls everything:

```yaml
llm:
  provider: anthropic        # anthropic | openai | ollama
  model: claude-sonnet-4-5   # blank = provider default
costs:
  budget_usd_per_run: 0.50   # hard stop when a run exceeds this
resilience:
  retries: 3
  breaker_threshold: 5       # consecutive failures before the circuit opens
notifications:
  slack_webhook_env: GTM_FORGE_SLACK_WEBHOOK
  on_failure: true
video:
  whisper_bin: whisper-cli   # local whisper.cpp binary
  ffmpeg_bin: ffmpeg
leads:
  email_providers: [neverbounce, zerobounce, regex]   # cascade order
```

Full reference: [docs/ENV.md](docs/ENV.md). Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Production behavior

- **Exit codes** — `0` success, `1` error, `3` content below eval gate, `4` email invalid/disposable. See [docs/ERRORS.md](docs/ERRORS.md).
- **Cost ledger** — every LLM call recorded; `gtm costs report` shows spend by model.
- **Circuit breaker** — a provider that fails 5 times in a row stops being called for 60s, even across separate cron runs (state lives in SQLite).
- **Notifications** — Slack/email on failure, off by default.
- **Updates** — `gtm update --check` against GitHub Releases; `gtm update` upgrades via uv/pipx.

## REST API

```bash
pip install "gtm-forge[serve]"
gtm serve --port 8420
# OpenAPI docs at http://127.0.0.1:8420/docs
```

Static spec: [docs/openapi.yaml](docs/openapi.yaml).

## Use it from an AI coding agent

```bash
gtm skills install --dest .claude/skills
```

Writes agent-readable SKILL.md files (one per skill) into your project so an agent can discover and drive the CLI. The format is agent-neutral — no vendor lock-in.

## Development

```bash
git clone https://github.com/pisigmac/gtm-forge.git
cd gtm-forge
uv venv && uv pip install -e ".[dev]"
ruff check . && ruff format --check src tests
mypy src
pytest --cov=gtm_forge
```

CI runs the same four gates on Python 3.11, 3.12, and 3.13.

## Layout

```
src/gtm_forge/
  cli.py            one Typer CLI, sub-app per skill
  config.py         YAML + pydantic settings
  core/             state, costs, breaker, retry, notify, credentials, updater, logging
  llm/              provider protocol + anthropic/openai/ollama + tracked wrapper
  skills/           the eight skills (pure functions first, execution last)
  serve.py          optional FastAPI surface
tests/              80+ tests: unit, CLI end-to-end, API
docs/               architecture, API, errors, ops runbooks, and more
```

## License

MIT. Clone it, fork it, sell it.
