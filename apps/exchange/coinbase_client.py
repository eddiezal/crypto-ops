# apps/exchange/coinbase_client.py
from __future__ import annotations
from decimal import Decimal, getcontext
from typing import Dict, Any, Optional
import os, time

getcontext().prec = 28

try:
    from coinbase.rest import RESTClient  # coinbase-advanced-py
    _has_cb = True
except Exception as e:
    RESTClient = None
    _has_cb = False
    _import_err = e

class CoinbaseAdv:
    """
    Minimal read-only wrapper around coinbase-advanced-py RESTClient.
    Targets sandbox or prod based on env.
    """
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        env: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        if not _has_cb:
            raise RuntimeError(f"coinbase-advanced-py not installed: {_import_err}")
        self.api_key   = api_key   or os.environ.get("COINBASE_API_KEY")
        self.api_secret= api_secret or os.environ.get("COINBASE_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Missing COINBASE_API_KEY / COINBASE_API_SECRET")

        self.env      = (env or os.environ.get("COINBASE_ENV", "sandbox")).lower()
        self.base_url = base_url or os.environ.get("COINBASE_BASE_URL")  # allow override

        # Be flexible: try base_url first (sandbox), then fallback
        kwargs = dict(api_key=self.api_key, api_secret=self.api_secret)
        self.client = None
        if self.base_url:
            try:
                self.client = RESTClient(**kwargs, base_url=self.base_url)
            except TypeError:
                pass
        if self.client is None and self.env == "sandbox":
            # Common sandbox domains; we try a couple to avoid library drift.
            for candidate in [
                "https://api-sandbox.coinbase.com",
                "https://api-public.sandbox.pro.coinbase.com",
            ]:
                try:
                    self.client = RESTClient(**kwargs, base_url=candidate)
                    break
                except TypeError:
                    self.client = None
        if self.client is None:
            self.client = RESTClient(**kwargs)  # default (likely prod)

    def get_balances(self) -> Dict[str, Decimal]:
        """
        Returns a mapping like {"USD": Decimal("123.45"), "BTC": Decimal("0.001"), ...}
        Handles both Advanced Trade and (legacy) shapes.
        """
        resp: Any = self.client.get_accounts()
        accounts = None
        if isinstance(resp, dict):
            if "accounts" in resp:
                accounts = resp["accounts"]    # Advanced Trade shape
            elif "data" in resp:
                accounts = resp["data"]
        elif isinstance(resp, list):
            accounts = resp
        if not accounts:
            return {}

        out: Dict[str, Decimal] = {}
        for a in accounts:
            # Advanced Trade shape: available_balance: {"value": "0.00", "currency": "USD"}
            try:
                cur = (a.get("available_balance") or {}).get("currency") or a.get("currency")
                val = (a.get("available_balance") or {}).get("value")    or a.get("balance")
                if cur and val is not None:
                    out[cur] = Decimal(str(val))
                    continue
            except Exception:
                pass
            # Older / fallback
            try:
                cur = a["currency"]
                val = a.get("available", a.get("balance", "0"))
                out[cur] = Decimal(str(val))
            except Exception:
                continue
        return out
