# Payments & Third-Party Spend

gtm-forge itself is free (MIT). "Payments" here means the external services it can touch.

| Service | When it bills you | Control |
|---|---|---|
| LLM provider (Anthropic/OpenAI) | Every non-dry-run LLM call | `costs.budget_usd_per_run` hard stop; `gtm costs report` |
| NeverBounce / ZeroBounce | Per verification, only when their API key is set | Provider order in `leads.email_providers`; put free `regex` first if credits are tight |
| Ollama | Never (local) | Default for zero-cost runs |

Rules:
1. `--dry-run` never spends anything — no LLM calls, no verification credits.
2. Providers without keys are skipped automatically; you can't be billed by accident.
3. The cost ledger (`costs` table) is the receipt. Review it weekly.
4. Set `budget_usd_per_run` in shared/cron environments — always.
