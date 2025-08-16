# Crypto Ops — Ultra-Minimal Starter (Windows, PowerShell 7+)

This **clean restart** has **no external Python dependencies**. It uses only the Python standard library.

It does 3 things:
1) Lets you run two bot skeletons (Rebalancer, Basis) in **dry-run** safely.
2) Posts **Runs** and **Ledger Snapshots** to **Notion** via the REST API.
3) Provides PowerShell helpers so setup is simple on **F:\**.

---

## Quickstart (PowerShell 7+, F:\ drive)

```powershell
F:
New-Item -ItemType Directory -Path F:\CryptoOps -Force | Out-Null
cd F:\CryptoOps

# Unzip this package (download from ChatGPT)
Expand-Archive .\crypto-ops-ultramin-win.zip -DestinationPath .\crypto-ops -Force
cd .\crypto-ops

# Allow scripts for THIS session only
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# One-time prep (creates .env if missing, prints Python version)
.\win\setup.ps1

# Open .env and paste your Notion token + DB IDs
.\win\open_env.ps1
```

### Connect Notion (once)
1) Create a Notion **internal integration** → copy the secret token.
2) Create two DBs (full-page tables):
   - **Runs**
   - **Ledger Snapshots**
3) Ensure DB properties match `notion\Notion_setup_checklist.md` exactly.
4) Share both DBs with your integration (Share → Invite).

### Test
```powershell
.\win\post_snapshot.ps1
.\win\run_rebalancer.ps1
.\win\run_basis.ps1
```
All three should post rows in your Notion DBs.

---

## Two projects in parallel
Copy this folder to two locations (e.g., `F:\CryptoOps\alpha`, `F:\CryptoOps\beta`), give each a unique `.env` and Notion DB IDs, and run bots in separate PowerShell tabs.

See `docs\multi_project.md` for details.
