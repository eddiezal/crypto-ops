# CryptoOps

CryptoOps is a quantitative crypto trading framework designed for:
- Multi-asset rebalancing (BTC, ETH, SOL, LINK by default)
- Momentum tilts & volatility-aware banding
- Configurable profiles (`Defensive`, `Balanced`, `Aggressive`)
- Integration with Coinbase API (paper or live)

## Getting Started

### 1. Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
