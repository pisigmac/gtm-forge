# Email Operations

Two distinct email concerns. Do not conflate them.

## 1. Verification (the `lead verify` skill)

- Cascade order from `leads.email_providers` (default: neverbounce -> zerobounce -> regex).
- First conclusive answer wins; `unknown` moves to the next provider.
- Verdicts: `valid` / `invalid` / `disposable` / `unknown`. Exit code 4 on invalid+disposable.
- Disposable domains are a static set in `enrich.py` — extend via PR, not config, to keep the audit trail identical everywhere.

## 2. Notifications (run failure alerts)

- SMTP via `notifications.email.*`. Off by default (`enabled: false`).
- Credentials come from env vars (`username_env`, `password_env`) — never stored in config.
- STARTTLS on by default; disable only for localhost relays.

## Rules for outbound sequences

`gtm outbound sequence` generates *copy only*. Sending is out of scope on purpose: deliverability, warm-up, and compliance (CAN-SPAM/GDPR) belong to your sending platform. Verify every address first (`lead verify`); never send to `unknown` verdicts at volume.
