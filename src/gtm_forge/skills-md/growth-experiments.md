---
name: gtm-growth-experiments
description: Run statistically rigorous growth experiments with bootstrap confidence intervals and Mann-Whitney U tests. Use when the user wants to A/B test a marketing change, analyze variant performance, or get a ship/kill verdict on experiment data.
---

# Growth Experiments

## When to use
The user has (or is collecting) per-variant metric data — impressions, watch time, conversion — and wants a real statistical answer, not "this one got more likes."

## Commands
```bash
gtm experiment create --name NAME --hypothesis H --variable V --variants control,treatment --metric M
gtm experiment add EXP_ID --variant VARIANT --values 1,2,3   # or --csv file.csv (columns: variant,value)
gtm experiment analyze EXP_ID [--alpha 0.05] [--n-boot 5000]
gtm experiment decide EXP_ID --decision promoted|killed
gtm experiment list
```

## Rules
- The FIRST variant is always the control.
- Both variants need at least 2 observations; 8+ per side gives reliable p-values.
- Verdicts: SHIP IT / KILL IT / INCONCLUSIVE. Never override an INCONCLUSIVE without more data.
- Experiments are JSON files under gtm-output/experiments/ — safe to read and edit by hand.
