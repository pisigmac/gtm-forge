# Marketing Notes

## One-liner

The GTM toolkit that treats marketing like engineering: real statistics, dry-run everything, and a receipt for every dollar of LLM spend.

## Positioning

Against the flood of "500 AI marketing prompts" repos: those are prompts in a trench coat. gtm-forge is an installable system — retries, circuit breakers, cost budgets, exit codes — that happens to ship eight marketing skills.

## Audiences

1. **Solo founders / indie hackers** — replace a $5K/mo agency retainer's worth of busywork for the cost of API calls.
2. **Growth marketers who can code** — stop guessing with "this post got more likes"; get p-values.
3. **Agencies** — standardize client work on one CLI with per-run cost receipts.
4. **AI-agent builders** — SKILL.md files drop straight into agent runtimes.

## Proof points to cite

- Bootstrap CIs and Mann-Whitney U instead of vibes.
- `--dry-run` shows exact ffmpeg commands and token estimates before anything runs.
- Circuit breaker state survives cron restarts (SQLite-persisted).
- Exit codes 3 and 4 built for CI pipelines.
- 80+ tests, mypy-clean, three Python versions in CI.

## Objection handling

- "I can just paste prompts into a chatbot." — Sure. Then do it 50 times a day, track what it cost, and prove the variant won. That's the part this automates.
- "I don't want to pay for APIs." — Ollama runs fully local; half the skills need no LLM at all.

## Channels

Show HN (lead with the stats engine), r/growthmarketing, agency-operator communities, and a comparison post vs prompt-pack repos.
