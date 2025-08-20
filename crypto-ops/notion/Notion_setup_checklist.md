# Notion Setup Checklist (Ultra-Minimal)

Create two **databases** (full-page tables). Property names must match exactly.

## 1) Runs (Database)
- **Name** – Title
- **Bot** – Select (values: Rebalancer, Basis, Other)
- **Project** – Rich text (optional)
- **Start** – Date
- **End** – Date
- **Decision** – Select (values: No-Op, Enter, Exit, Rebalance, Error, (Dry) Enter, (Dry) Exit)
- **Notional (USD)** – Number
- **Message** – Rich text
- **Logs URL** – URL (optional)

## 2) Ledger Snapshots (Database)
- **Name** – Title
- **Date** – Date
- **NAV (USD)** – Number
- **Vault %** – Number
- **Cash %** – Number
- **Trading %** – Number
- **PnL 1d** – Number (optional)
- **Fees (1d)** – Number (optional)

## Integration
- Create a Notion internal integration → copy token to `.env` as `NOTION_TOKEN`.
- Share both DBs with your integration (Invite → select integration).
