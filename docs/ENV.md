# Environment & Configuration Reference

## Files

| Path | Purpose |
|---|---|
| `~/.gtm-forge/config.yaml` | Main config (override with `--config` or `GTM_FORGE_CONFIG`) |
| `~/.gtm-forge/state.db` | Runs, costs, breaker state, kv |
| `./gtm-output/` | Artifacts (override `paths.output_dir`) |

## Environment variables

| Variable | Used for |
|---|---|
| `GTM_FORGE_HOME` | Move the whole `.gtm-forge` directory |
| `GTM_FORGE_CONFIG` | Point at a specific config file |
| `ANTHROPIC_API_KEY` | Anthropic provider (or your `llm.api_key_env`) |
| `OPENAI_API_KEY` | OpenAI provider |
| `GTM_FORGE_SLACK_WEBHOOK` | Slack notifications |
| `GTM_FORGE_NEVERBOUNCE_KEY` | Email verification provider |
| `GTM_FORGE_ZEROBOUNCE_KEY` | Email verification provider |

## Full config schema

```yaml
version: 1
llm:
  provider: anthropic        # anthropic | openai | ollama
  model: null                # null -> DEFAULT_MODELS[provider]
  api_key_env: null          # env var name holding the key
  base_url: null             # custom/OpenAI-compatible/ollama endpoint
  max_tokens: 4096
  temperature: 0.2
  request_timeout_s: 60.0
paths:
  state_db: ~/.gtm-forge/state.db
  output_dir: gtm-output
resilience:
  retries: 3
  backoff_base_s: 0.5
  backoff_max_s: 8.0
  breaker_threshold: 5
  breaker_cooldown_s: 60.0
costs:
  track: true
  budget_usd_per_run: null   # hard stop; null = unlimited
  prices:                    # USD per 1M tokens; edit to match your plan
    claude-sonnet-4-5: {input: 3.0, output: 15.0}
notifications:
  slack_webhook_env: GTM_FORGE_SLACK_WEBHOOK
  on_success: false
  on_failure: true
  email:
    enabled: false
    smtp_host: localhost
    smtp_port: 25
    sender: gtm-forge@localhost
    recipients: []
    username_env: null
    password_env: null
    starttls: true
video:
  whisper: local             # local | openai
  whisper_bin: whisper-cli
  whisper_model_path: models/ggml-base.en.bin
  ffmpeg_bin: ffmpeg
  window_seconds: 90
  clip_count: 4
leads:
  email_providers: [neverbounce, zerobounce, regex]
  http_timeout_s: 10.0
features:
  flags: {}
skills: {}                   # free-form per-skill overrides
```
