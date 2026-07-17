---
name: gtm-outbound-engine
description: Score leads against an ICP with explainable YAML weights and generate multi-step outreach sequences. Use for lead prioritization and first-touch campaign drafting.
---

# Outbound Engine

## When to use
Prioritizing a lead list, or drafting a personalized sequence grounded in fit reasons.

## Commands
```bash
gtm outbound score --csv leads.csv --icp icp.yaml [--out ranked.csv]
gtm outbound sequence --icp icp.yaml --lead-json '{"company":"Acme","industry":"saas"}' --steps 5
```

## ICP file format
```yaml
weights:            # exact match
  industry: {saas: 30, fintech: 25}
keyword_weights:    # substring match
  title: {vp: 20, head: 15}
range_weights:      # numeric ranges
  employees: [{min: 50, max: 500, points: 20}]
thresholds: {hot: 60, warm: 30}
```

## Rules
- Every score comes with reasons. Show them — reps trust explainable scores.
