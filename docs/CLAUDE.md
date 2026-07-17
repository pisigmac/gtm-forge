# Working on gtm-forge (for AI coding agents)

You are editing a production Python package. These rules keep it shippable.

## Non-negotiables

1. Run the gates before declaring done: `ruff check .`, `ruff format --check src tests`, `mypy src`, `pytest`. All four must pass.
2. Every new skill command gets a `--dry-run` path that performs zero side effects.
3. Pure functions first, execution last. Parsing, scoring, and command-building must be testable without network, API keys, or ffmpeg.
4. No secrets in code. Env var names in config, values in the environment or OS keychain.
5. LLM calls go through `gtm_forge.llm.factory.build_provider` — never instantiate SDK clients inside skills. That wrapper provides retry, the circuit breaker, and cost tracking for free.

## Conventions

- Python 3.11+, `from __future__ import annotations` in every module (except `serve.py` — FastAPI needs eager annotation resolution).
- Errors users can act on: raise `ValueError` with a fix suggestion; the CLI renders them.
- New exit codes must be documented in `docs/ERRORS.md`.
- New config keys get defaults so existing config files keep working.

## Layout

See `docs/CODEMAP.md`. Tests mirror `src/` one-to-one.

## When adding a skill

1. Create `src/gtm_forge/skills/<name>/` with pure logic modules.
2. Register a sub-app in `cli.py`, add the entry to `SKILLS` in `skills/__init__.py`.
3. Write `src/gtm_forge/skills-md/<name>.md` (and the root `skills-md/` copy).
4. Add unit tests + one CLI end-to-end test.
5. Update `docs/FEATURES.md` and `docs/CHANGELOG.md`.
