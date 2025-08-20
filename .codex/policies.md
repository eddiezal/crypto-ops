# Codex Guardrails
- Never commit secrets. Use ENV vars (see .env.example) and secret managers.
- Respect rate limits in `src/ingest/common.py`.
- No schema changes; write via approved helpers (e.g., `bq_write_v3()`).
- Trading paths default to DRY-RUN in non-prod; never place real orders.