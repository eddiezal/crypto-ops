import os
from libs.dotenv_min import load_dotenv
from libs.notion_client_min import post_snapshot

load_dotenv()

if __name__ == "__main__":
    # placeholder values (adjust later)
    post_snapshot(nav_usd=300000.0, vault_pct=0.50, cash_pct=0.25, trading_pct=0.25, pnl_1d=0.0, fees_1d=0.0)
