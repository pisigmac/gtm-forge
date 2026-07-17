---
name: gtm-lead-intel
description: Build company dossiers from public website signals (tech stack, hiring, contacts) and verify emails through a provider cascade. Use for account research and list cleaning.
---

# Lead Intelligence

## When to use
Researching a target account before outreach, or verifying an email before sending.

## Commands
```bash
gtm lead dossier --company "Acme" --url https://acme.com [--out dossier.md]
gtm lead verify someone@acme.com                    # cascade: configured providers, first conclusive wins
gtm --dry-run lead verify someone@acme.com          # shows the cascade order only
```

## Rules
- Exit code 4 means invalid or disposable — do not send.
- Providers without API keys report "unknown" and the cascade moves on; the free regex checker is always last.
- Dossiers use only public facts. Say so when evidence is thin.
