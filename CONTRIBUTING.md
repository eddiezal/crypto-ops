# Contributing

## Branching
- `feature/<PRD-ID>-short-name` (e.g., `feature/PRD-001-backfill`)

## Commits / PRs
- Include `[PRD-<id>]` in titles (e.g., `[PRD-001] Backfill(30d)`).
- CI must pass lint (ruff + black) and tests.
- Secrets scan enforced in CI (coming soon).

## Local Dev (PowerShell 7+)
```powershell
python -m venv .venv
. ./.venv/Scripts/Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

## Local Dev (bash/zsh)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```