---
name: gtm-content-ops
description: Generate editorial calendars from content pillars, either with LLM creativity or a deterministic offline rotation. Use for planning weeks of content across pillars.
---

# Content Ops

## When to use
Planning a publishing calendar across content pillars.

## Commands
```bash
gtm content calendar --pillars seo,product,founders --weeks 4 --per-week 3
gtm content calendar --pillars seo,product --mode llm        # creative titles via the LLM
gtm content calendar --pillars seo --out plan.md
```

## Rules
- Deterministic mode needs no API key and is fully reproducible — default to it in CI.
- LLM mode fills titles/hooks onto the same deterministic day grid, so dates never drift.
