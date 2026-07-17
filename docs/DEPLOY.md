# Deploy & Release

## For users (install)

```bash
uv tool install gtm-forge        # or: pipx install gtm-forge
gtm init --yes && gtm doctor
```

## For operators (cron)

```bash
# weekly content calendar, Mondays 06:00
0 6 * * 1  cd /srv/marketing && gtm content calendar --pillars seo,product --weeks 1

# daily deal health with Slack alert on failure
0 7 * * *  cd /srv/sales && gtm sales health --csv deals.csv
```

Notes: breaker state survives across runs (SQLite), so a provider outage opens the circuit once instead of every cron tick. Set `notifications.on_failure: true` and `GTM_FORGE_SLACK_WEBHOOK` to get paged.

## Releasing (maintainers)

1. Bump `version` in `pyproject.toml` and `src/gtm_forge/__init__.py`.
2. Update `docs/CHANGELOG.md`.
3. Merge to main — CI gates must be green.
4. Tag: `git tag v0.2.0 && git push --tags`.
5. Create the GitHub Release (this powers `gtm update --check`).
6. Publish to PyPI: `uv build && uv publish`.

Versioning: semver. Exit codes and config keys are public API — breaking them needs a major bump.

## Server mode

```bash
pip install "gtm-forge[serve]"
gtm serve --host 0.0.0.0 --port 8420
```

Run behind your usual reverse proxy with auth; the API itself is unauthenticated by design (it is a localhost tool).
