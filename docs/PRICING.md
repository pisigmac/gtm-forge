# Pricing Model (for cost tracking)

gtm-forge is MIT-licensed and free. This doc covers **LLM usage pricing** — how the cost ledger prices calls.

## How pricing works

`costs.prices` maps model name -> `{input, output}` USD per 1M tokens. After each LLM call, the tracker computes:

```
cost = (input_tokens * price.input + output_tokens * price.output) / 1_000_000
```

Unknown models cost `0.0` and are treated as untracked (visible in logs, absent from the ledger). Local models (Ollama) price at zero.

## Default table (edit to match your actual plan)

| Model | Input / 1M | Output / 1M |
|---|---|---|
| claude-sonnet-4-5 | $3.00 | $15.00 |
| claude-opus-4-1 | $15.00 | $75.00 |
| claude-haiku-4-5 | $1.00 | $5.00 |
| gpt-4.1 | $2.00 | $8.00 |
| gpt-4.1-mini | $0.40 | $1.60 |
| gpt-4.1-nano | $0.10 | $0.40 |
| llama3.1 (local) | $0.00 | $0.00 |

Defaults are starting points only. Providers change prices; keep your config in sync.

## Budgets

`costs.budget_usd_per_run` is a hard stop per CLI invocation. Typical safe budgets: eval panel run ~$0.05, dossier ~$0.02, sequence ~$0.04, video scoring ~$0.01-0.03 depending on transcript length.

## Checking spend

```bash
gtm costs report     # by model
gtm costs runs       # recent runs with status
```
