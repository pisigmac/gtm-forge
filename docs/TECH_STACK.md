# Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Data + LLM ecosystem, modern stdlib |
| CLI | Typer + Rich | Typed commands, great help output, tables |
| Config | pydantic v2 + PyYAML | Validation with defaults; YAML humans can edit |
| HTTP | httpx | One client for sync calls everywhere |
| API server | FastAPI + uvicorn (optional) | OpenAPI for free |
| Stats | stdlib math/random | Bootstrap + Mann-Whitney need nothing heavier |
| State | SQLite (stdlib sqlite3) | Zero-config, transactional, cron-safe |
| Media | ffmpeg + whisper.cpp (external binaries) | Industry standard, local, free |
| LLM SDKs | anthropic / openai (optional extras) | Core install stays light |
| Local LLM | Ollama over HTTP | Fully offline runs |
| Packaging | hatchling, src layout | Modern, simple, reproducible |
| Deps mgmt | uv (dev), pip/pipx/uv (users) | Speed and ubiquity |
| Quality | ruff (lint+format), mypy, pytest | Three gates, wired into CI |
| CI | GitHub Actions, Python 3.11/3.12/3.13 | Matrix gate on every push |

## Dependency policy

Base install: 5 runtime deps (typer, rich, pydantic, PyYAML, httpx). Everything else is an optional extra: `anthropic`, `openai`, `serve`, `video`. New dependencies must justify their weight in a PR description.
