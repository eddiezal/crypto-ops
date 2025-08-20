# CryptoOps

Lightweight scaffolding for crypto data ops: ingestion → metrics → CI. Opinionated, PS7-friendly, and safe by default.

## Quickstart

```powershell
./scripts/bootstrap.ps1 -Dev
pytest -q
uvicorn src.metrics.api:app --reload
```

If you're on bash/zsh:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
uvicorn src.metrics.api:app --reload
```

## Env
Copy and edit `.env.example` → `.env`.

- `DRY_RUN=1` logs instead of writing to BigQuery.
- `MOCK_INGEST=1` makes `backfill()` return synthetic OHLCV.

## Structure
```
src/
  ingest/
  metrics/
tests/
docs/
  prd/ adr/ runbooks/
```

## CI
GitHub Actions: lint (ruff + black), tests (pytest), mocked ingestion by default.