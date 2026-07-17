---
name: gtm-sales-pipeline
description: Score deal health with transparent rules (stage age, activity, champion, threading) and surface departed champions for re-engagement. Use for pipeline reviews and account win-back.
---

# Sales Pipeline

## When to use
Weekly pipeline review, or finding win-back opportunities when champions change jobs.

## Commands
```bash
gtm sales health --csv deals.csv
# columns: id,name,amount,stage,stage_entered,last_activity,has_champion,contacts

gtm sales champions --csv champions.csv [--draft] [--limit 5]
# columns: name,old_company,status,new_company,role,last_deal
```

## Rules
- Tiers: healthy < 30, at-risk 30-59, critical 60+. Show the reasons, not just the number.
- --draft uses the LLM to write re-engagement notes for departed champions.
