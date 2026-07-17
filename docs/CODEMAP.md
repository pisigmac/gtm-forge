# Codemap

```
src/gtm_forge/
├── __init__.py              version
├── __main__.py              python -m gtm_forge
├── cli.py                   Typer app; sub-apps per skill; init/doctor/update/keys/skills/costs/serve
├── config.py                pydantic Settings, YAML load/save, DEFAULT_MODELS, DEFAULT_PRICES
├── serve.py                 FastAPI factory (optional extra)
├── core/
│   ├── breaker.py           retry_call (backoff+jitter), CircuitBreaker (persisted 3-state)
│   ├── context.py           RunContext: run records, notifications, dry-run plans
│   ├── costs.py             estimate_cost, check_budget, estimate_tokens
│   ├── credentials.py       env-first secret resolution, keychain storage
│   ├── logging.py           JSON-lines formatter
│   ├── notify.py            Slack webhook + SMTP, never crashes a run
│   ├── state.py             StateStore: runs/costs/breaker/kv in SQLite
│   └── updater.py           GitHub Releases check, uv/pipx self-update
├── llm/
│   ├── base.py              LLMResult, Provider protocol, LLMError
│   ├── anthropic.py         optional SDK wrapper
│   ├── openai.py            optional SDK wrapper (any OpenAI-compatible endpoint)
│   ├── ollama.py            local, HTTP /api/chat
│   └── factory.py           build_provider + TrackedProvider (retry/breaker/costs/budget)
├── skills/
│   ├── __init__.py          SKILLS registry
│   ├── growth/              stats.py (bootstrap, MWU), engine.py (experiment store)
│   ├── content_eval/        panel.py (7 experts, gate, markdown report)
│   ├── seo/                 brief.py (attack briefs, cannibalization)
│   ├── video/               pipeline.py (whisper parse, chunking, clip plans, ffmpeg)
│   ├── leads/               dossier.py (facts, tech), enrich.py (cascade verify)
│   ├── outbound/            icp.py (weights), sequences.py (LLM sequences)
│   ├── contentops/          calendar.py (deterministic + LLM modes)
│   └── sales/               health.py (risk rules), champions.py (re-engagement)
└── skills-md/               agent-readable SKILL.md files (package data)

tests/                       mirrors src: unit + CLI end-to-end + API tests
docs/                        this documentation set
ops/                         operational runbooks
skills-md/                   root copy of skill files for humans browsing the repo
```

## Data flow (typical LLM skill)

```
CLI command ──> RunContext (run record opened)
             ──> build_provider ──> TrackedProvider
                                      ├── CircuitBreaker.guard
                                      ├── retry_call (backoff + jitter)
                                      ├── provider.complete (anthropic/openai/ollama)
                                      └── StateStore.record_cost (+ budget check)
             ──> skill logic (pure functions around the call)
             ──> artifacts written to paths.output_dir
             ──> RunContext.end (run record closed, notifications fired)
```
