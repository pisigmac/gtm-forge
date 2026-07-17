---
name: gtm-content-eval
description: Score a content idea with a 7-expert panel (brand, SEO, audience, conversion, competitive, voice, platform) before producing it. Use when the user asks whether an idea is worth making, or wants a numeric quality gate on content.
---

# Content Eval

## When to use
Before any content production. The panel returns a mean score; nothing ships below the gate.

## Commands
```bash
gtm --dry-run eval --idea "IDEA"                    # plan + estimated tokens, zero cost
gtm eval --idea "IDEA" --context audience.md        # full run, writes markdown report
gtm eval --idea "IDEA" --gate 85                    # custom gate (default 90)
```

## Rules
- Exit code 3 means below gate — revise or kill the idea. Surface this to the user.
- Always read the weakest expert's fix first; it is the cheapest score gain.
- Reports land in gtm-output/evals/.
