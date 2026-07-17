# Agent Integration

gtm-forge is built to be *driven by* AI agents as much as by humans.

## SKILL.md files

`gtm skills install --dest .claude/skills` writes one agent-readable file per skill. Each file carries YAML frontmatter (`name`, `description`) so agent runtimes can index it, plus usage commands and operating rules. The format is agent-neutral — it works with any runtime that reads skill files.

## Design choices for agent drivers

- **Deterministic output.** JSON dry-run plans (`--dry-run`), machine-parseable logs (JSON lines), stable exit codes.
- **Composable units.** Every skill is also a Python function: `from gtm_forge.skills.seo.brief import find_cannibals`.
- **Honest failures.** Exit 3 (below gate) and exit 4 (invalid email) let agents branch without parsing prose.
- **Cost visibility.** Agents can check `gtm costs report` and respect `budget_usd_per_run`.

## REST for agent services

`gtm serve` exposes the dependency-free skills over HTTP for agents that run remotely. OpenAPI spec: `docs/openapi.yaml`.

## Safety rules encoded in the skills themselves

Each SKILL.md contains "Rules" sections — e.g., never send to a `disposable` email, never override an INCONCLUSIVE verdict. Keep those rules current; they are the guardrails agents actually read.
