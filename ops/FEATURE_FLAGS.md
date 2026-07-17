# Feature Flags

Flags live in config.yaml:

```yaml
features:
  flags:
    video_openai_whisper: false
    experimental_power_calc: true
```

## Reading a flag in code

```python
if settings.features.enabled("experimental_power_calc"):
    ...
```

## Rules

1. Default is always `False` for unreleased features — a missing flag must mean "off".
2. Flags gate *behavior*, never *fixes*. Bug fixes ship unflagged.
3. A flag must have an owner and a removal plan in `docs/FUTURE_PLAN.md` before merging.
4. Remove flags within one minor release of the feature going GA; delete the code path, not just the flag.
5. `gtm doctor` does not evaluate flags — config must load identically regardless of flag state.

## Current flags

None yet. The mechanism ships in 0.1.0; the first consumer is planned for the OpenAI Whisper video path.
