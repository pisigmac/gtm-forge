# Data Retention

## What lives where

| Data | Location | Default retention |
|---|---|---|
| Run history, costs, breaker | `~/.gtm-forge/state.db` | Forever (user-deletable) |
| Experiments | `<output_dir>/experiments/*.json` | Forever (user-deletable) |
| Reports, briefs, calendars, dossiers | `<output_dir>/` | Forever (user-deletable) |
| Video intermediates (WAV, transcripts) | `<out>/_work/` | Delete after review — they are large |
| Logs | stderr (user's log stack) | User-controlled |

## Deleting

```bash
rm ~/.gtm-forge/state.db        # full ledger reset
rm -rf gtm-output/              # all artifacts
```

There is no remote copy of anything. Uninstalling the package (`uv tool uninstall gtm-forge`) removes the code; the two data locations above are yours to keep or delete.

## PII handling

- Lead/deal/champion CSVs never leave your machine (pure local processing).
- Dossiers fetch public pages only; nothing is uploaded except the LLM prompt you configure.
- LLM prompts may contain lead/company facts you pass in — that data goes to *your* LLM provider under *your* terms. Use Ollama for fully local processing of sensitive accounts.
- Retention rule of thumb: if you wouldn't paste it into a chatbot, use the local provider.

## Compliance note

For GDPR/CCPA requests covering data in `state.db` or artifacts: the tables are plain SQLite and the artifacts are plain files — locate by name/company string, delete, done. No processor relationships exist because nothing is transmitted to us.
