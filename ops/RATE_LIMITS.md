# Rate Limits

## Outbound calls we make

| Target | Limit behavior | Our handling |
|---|---|---|
| Anthropic API | Per-plan RPM/TPM | 3 retries, backoff 0.5s -> 8s with jitter; circuit opens after 5 consecutive failures (60s cooldown) |
| OpenAI API | Per-plan RPM/TPM | Same as above |
| Ollama | Local; bounded by hardware | No retry storms: same breaker applies |
| NeverBounce/ZeroBounce | Per-plan | Single call per verification; failures degrade to `unknown`, never retry-burn credits |
| Public websites (dossier) | Be polite | One GET per dossier, 10s timeout, descriptive User-Agent |
| GitHub Releases (update check) | 60 req/hr unauthenticated | One call per `gtm update`/`doctor`, 5s timeout, failures ignored |

## Inbound (server mode)

`gtm serve` has no built-in rate limiting — it is a localhost tool. If you expose it, put it behind a reverse proxy (nginx/Caddy) with `limit_req` and auth.

## Tuning

`resilience.retries`, `backoff_base_s`, `backoff_max_s`, `breaker_threshold`, `breaker_cooldown_s` — all in config.yaml.
