# Testing

## Gates (all four must pass)

```bash
ruff check .
ruff format --check src tests
mypy src
pytest --cov=gtm_forge --cov-fail-under=60
```

CI runs them on Python 3.11, 3.12, 3.13 (`.github/workflows/ci.yml`).

## Suite layout

| File | Covers |
|---|---|
| `test_stats.py` | Bootstrap CI, Mann-Whitney (known cases, ties, direction), verdicts |
| `test_config.py` | Defaults, YAML roundtrip, env override, malformed config |
| `test_costs.py` | Price math, unknown models, budget enforcement |
| `test_breaker.py` | Retry, open/half-open/closed transitions |
| `test_state.py` | Runs, cost ledger, kv, breaker rows |
| `test_content_eval.py` | Panel aggregation, gate, JSON extraction, dry-run plan |
| `test_leads.py` | Tech fingerprints, signals, syntax checks, cascade order |
| `test_outbound.py` | ICP exact/keyword/range scoring, labels, YAML load |
| `test_contentops.py` | Calendar grid, rotation, markdown render |
| `test_sales.py` | Deal risk rules, portfolio rollup, champion targeting |
| `test_seo.py` | Jaccard, cannibal detection |
| `test_video.py` | Whisper JSON parse, chunking, clip plans, ffmpeg commands |
| `test_cli.py` | End-to-end: version, init, full experiment flow, dry-runs, exit codes |
| `test_serve.py` | API: health, analyze, score, cannibalize, costs |

## Conventions

- **No network in tests.** LLM calls use `FakeProvider` (conftest). HTTP verifiers use stub adapters.
- **Isolated state.** The `home` fixture points `GTM_FORGE_HOME` at a tmp dir with an ollama config — no API key required, no touching the developer's real state.
- **Statistics are seeded.** Every bootstrap call in tests passes an explicit seed — failures are reproducible.
- CLI tests use typer's `CliRunner`; user-facing output goes through click's echo so it is capturable.

## Adding tests

Mirror the source file (`skills/foo/bar.py` -> `tests/test_bar.py`). One happy path, one edge case, one failure mode minimum. Pure functions never need fixtures.
