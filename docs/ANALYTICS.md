# Analytics

gtm-forge tracks usage **locally only**. Nothing phones home. There is no telemetry.

## What is recorded (locally)

| Signal | Where | Purpose |
|---|---|---|
| Run start/finish, skill, status, dry-run | `runs` table | Audit trail, `gtm costs runs` |
| Tokens + USD per LLM call | `costs` table | `gtm costs report`, budgets |
| Breaker transitions | `breaker` table | Resilience across runs |
| JSON logs | stderr | Ship to your log stack if you want aggregation |

## Answering common questions

- **What did we spend this month?** `gtm costs report` (or query the `costs` table by `ts`).
- **Which skill fails most?** `SELECT skill, status, COUNT(*) FROM runs GROUP BY skill, status`.
- **Are we wasting money on dry runs?** Dry runs record zero cost by construction.

## If you want dashboards

Point any SQLite-aware BI tool (Metabase, Datasette) at `state.db`, or tail the JSON logs into Loki/ELK. The schema is stable within a major version (`docs/DB_SCHEMA.md`).

## Privacy

No PII leaves your machine except what you explicitly send to your configured LLM provider and email-verification providers. Lead CSVs stay local; dossiers fetch public web pages only.
