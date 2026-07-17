# Python API

Everything the CLI does, you can do from Python.

## Statistics (no LLM required)

```python
from gtm_forge.skills.growth.stats import analyze

report = analyze([100, 120, 110, 105, 115], [150, 160, 170, 155, 165])
print(report.verdict)          # SHIP IT / KILL IT / INCONCLUSIVE
print(report.bootstrap.low, report.bootstrap.high, report.mann_whitney.p_value)
```

## Experiment store

```python
from pathlib import Path
from gtm_forge.skills.growth.engine import create_experiment, add_observations, analyze_experiment

exp = create_experiment(Path("gtm-output"), name="test", hypothesis="h",
                        variable="format", variants=["a", "b"], metric="ctr")
add_observations(exp, "a", [1.0, 1.2])
reports = analyze_experiment(exp)
```

## Content eval (LLM)

```python
from gtm_forge.config import load_settings
from gtm_forge.llm.factory import build_provider
from gtm_forge.skills.content_eval.panel import run_panel

settings = load_settings()
provider = build_provider(settings)          # retry + breaker + cost tracking included
report = run_panel(provider, idea="10 lessons from 100 episodes",
                   gate=90, model=settings.llm.resolved_model())
print(report.mean, report.passed)
```

## Deterministic skills

```python
from gtm_forge.skills.seo.brief import Page, find_cannibals
from gtm_forge.skills.outbound.icp import ICPConfig, score_lead
from gtm_forge.skills.sales.health import Deal, portfolio_health
from gtm_forge.skills.contentops.calendar import deterministic_calendar
from gtm_forge.skills.leads.enrich import verify_cascade
from gtm_forge.skills.leads.dossier import detect_tech, extract_signals
from gtm_forge.skills.video.pipeline import parse_whisper_json, chunk_segments, build_cut_commands
```

## Runtime services

```python
from gtm_forge.core.state import StateStore          # runs, costs, breaker, kv
from gtm_forge.core.breaker import CircuitBreaker    # persisted circuit breaking
from gtm_forge.core.costs import estimate_cost       # USD math
from gtm_forge.core.notify import notify             # slack + email
```

## Custom providers

Implement the `Provider` protocol (`complete(system, prompt, model, max_tokens, temperature) -> LLMResult`) and pass it anywhere a provider is accepted. `TrackedProvider` wraps it with resilience and cost tracking.
