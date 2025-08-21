# Prognosis — Risks, Confirmation, Fix (v0.2)

| Risk | Confirm | Fix |
|---|---|---|
| Env concatenation | gcloud run services describe … env[] | remove-env then add per key |
| /plan vs /plan_band band mismatch | curl /plan & /plan_band | wrap compute_actions in /plan with _with_policy_band() |
| Scheduler 404s | logs filter prices_append/apply_paper | delete legacy jobs; keep hourly snapshot |
| Fallback numeric-only | cat gs://$bucket/state/balances.json | ensure only numeric keys |
| Idempotent ledger | diff cycle runs | key by cycle_id; upsert |
| Structured logs | grep JSON fields | standard schema in runbook |
| Kill switch cloud | N/A | script to pause scheduler + traffic off |
| CRLF churn | git warnings | .gitattributes normalize |
