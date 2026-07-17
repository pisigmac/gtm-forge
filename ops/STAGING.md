# Staging

There is no hosted service to stage — but there *is* a safe way to rehearse changes before they touch real data.

## Isolated home per environment

```bash
export GTM_FORGE_HOME=/srv/gtm-forge/staging     # staging config + state.db
gtm init --yes
# vs production:
export GTM_FORGE_HOME=/srv/gtm-forge/prod
```

Config, state, and cost ledgers are fully separated by directory.

## Staging checklist for new versions

1. `uv tool install git+https://github.com/pisigmac/gtm-forge.git@<branch>` into a throwaway env.
2. `gtm doctor` against the staging home.
3. Run each cron command with `--dry-run` first; diff the plan against production behavior.
4. Run one real, low-cost command (`gtm content calendar`) and inspect the artifact.
5. Check `gtm costs report` — staging spend should be near zero.
6. Promote: `gtm update` in the production env.

## Data

Never point staging at production CSVs containing real customer PII. Use the fixtures in `tests/` as templates for synthetic deals/leads/champions files.
