# Empty States

Every "nothing here yet" path must tell the user the next action. Current behavior:

| Situation | Output | Next action offered |
|---|---|---|
| No experiments | "No experiments yet." | Points to `gtm experiment create` |
| No cannibalization conflicts | Green "none above threshold" line | States the threshold used |
| Empty cost ledger | Empty table + `Total: $0.0000` | Implies: no tracked LLM calls yet |
| No re-engagement targets | Empty table | (CSV had no departed champions) |
| Missing config | Defaults used silently | `gtm init` suggested in README and init command |
| Experiment with <2 observations | Error: "Both groups need at least 2 observations." | Tells you to add data |
| Provider SDK missing | `LLMError` with the exact pip install command | Copy-paste fix |

## Rules

1. Never print a bare "[]" or an empty table with no explanation.
2. Empty is not an error — exit code stays 0 unless the user asked for something impossible.
3. Always name the command that changes the empty state.
