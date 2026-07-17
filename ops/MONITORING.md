# Monitoring

## What to watch

| Signal | Where | Alert when |
|---|---|---|
| Failed runs | `runs` table (`status='failed'`) | Any failure in cron contexts |
| Breaker openings | `breaker` table (`state='open'`) | Provider circuit opens — means repeated provider failures |
| Spend | `costs` table | Weekly total exceeds expectation |
| Slack/email channel failures | stderr logs (`notification failed`) | Alert channel itself is broken |

## Quick queries

```sql
-- failures in the last day
SELECT skill, command, error FROM runs
WHERE status='failed' AND started_at > datetime('now', '-1 day');

-- spend by day
SELECT date(ts) d, SUM(cost_usd) FROM costs GROUP BY d ORDER BY d DESC;
```

## Health check

`gtm doctor` is the human health check (config, credentials, ffmpeg, version). For machines, `gtm serve` exposes `GET /health` returning `{"status": "ok", "version": ...}` — wire it to your uptime checker.

## Log shipping

stderr is JSON lines. For cron, append to a file (`2>>/var/log/gtm-forge.jsonl`) and let your existing log agent (Vector, Fluent Bit) ship it. No vendor-specific agent is bundled.
