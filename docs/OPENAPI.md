# OpenAPI

The REST API (`gtm serve`) is described by `docs/openapi.yaml`, generated from the FastAPI app itself — the spec is never hand-maintained.

## Regenerate

```bash
python -c "
import yaml, json
from gtm_forge.serve import create_app
spec = create_app().openapi()
print(yaml.safe_dump(json.loads(json.dumps(spec)), sort_keys=False))
" > docs/openapi.yaml
```

## Endpoints summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + version |
| GET | `/costs/summary` | Aggregated spend by model |
| POST | `/skills/growth/analyze` | Bootstrap + Mann-Whitney on posted samples |
| POST | `/skills/outbound/score` | ICP scoring with posted weights |
| POST | `/skills/seo/cannibalize` | Overlap detection on posted pages |
| POST | `/skills/content-eval/run` | 7-expert panel (uses server config's LLM) |

Interactive docs: `http://127.0.0.1:8420/docs` while the server runs.
