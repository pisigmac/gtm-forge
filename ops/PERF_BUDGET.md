# Performance Budget

Budgets for a healthy run on a laptop. If a command consistently exceeds these, something is wrong.

| Command | p50 target | Hard ceiling | Notes |
|---|---|---|---|
| `gtm experiment analyze` (5k bootstrap) | < 2s | 10s | Pure Python; n_boot=100k still < 30s |
| `gtm eval` | < 30s | 120s | 7 sequential LLM calls; dominated by provider latency |
| `gtm seo cannibalize` (1k pages) | < 2s | 15s | O(n^2) pair comparison, fine to ~5k pages |
| `gtm video clips` (60-min episode) | < 15 min | 30 min | Dominated by whisper.cpp + ffmpeg; LLM scoring < 1% |
| `gtm lead dossier` | < 20s | 60s | One HTTP fetch + one LLM call |
| `gtm sales health` (500 deals) | < 1s | 5s | Pure rules |
| `gtm content calendar` (deterministic) | < 1s | 2s | No I/O |
| CLI startup | < 500ms | 1.5s | No heavy imports at startup; SDKs load lazily |

## Rules

- Provider SDKs (`anthropic`, `openai`) import lazily inside factory functions — never at module top level.
- No skill may do network I/O at import time.
- Bootstrap loops stay in stdlib (`random`); do not add numpy for the stats engine.
