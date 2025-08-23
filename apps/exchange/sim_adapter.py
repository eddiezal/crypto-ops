from typing import Dict, Any
from decimal import Decimal
import time
import uuid
from apps.exchange.adapter import ExchangeAdapter
from apps.infra import state

class SimulationAdapter(ExchangeAdapter):
    """Simulated exchange for testing"""
    
    def __init__(self):
        self.prices = {
            "BTC-USD": Decimal("95000"),
            "ETH-USD": Decimal("3500")
        }
        self.orders = {}
        
    def get_balances(self) -> Dict[str, Any]:
        """Read balances from state file"""
        balances = state.read_json("state/balances.json", {})
        return {k: Decimal(str(v)) for k, v in balances.items()}
    
    def get_ticker(self, product_id: str) -> Dict[str, Any]:
        """Return simulated price"""
        return {"price": str(self.prices.get(product_id, 0))}
    
    def place_limit_order(self, 
                         product_id: str, 
                         side: str, 
                         size: str, 
                         price: str, 
                         client_order_id: str) -> Dict[str, Any]:
        """Simulate order placement"""
        order_id = str(uuid.uuid4())
        
        # Simulate immediate fill at limit price
        self.orders[order_id] = {
            "id": order_id,
            "client_order_id": client_order_id,
            "product_id": product_id,
            "side": side,
            "size": size,
            "price": price,
            "status": "filled",
            "filled_size": size,
            "executed_value": str(Decimal(size) * Decimal(price)),
            "fill_fees": str(Decimal(size) * Decimal(price) * Decimal("0.001"))  # 0.1% fee
        }
        
        # Update balances (simplified)
        self._update_balances_for_fill(product_id, side, size, price)
        
        return self.orders[order_id]
    
    def _update_balances_for_fill(self, product_id: str, side: str, size: str, price: str):
        """Update state balances after fill"""
        balances = self.get_balances()
        asset = product_id.split("-")[0]
        size_dec = Decimal(size)
        value = Decimal(size) * Decimal(price)
        fee = value * Decimal("0.001")
        
        if side == "buy":
            balances[asset] = balances.get(asset, Decimal(0)) + size_dec
            balances["USD"] = balances.get("USD", Decimal(0)) - value - fee
        else:
            balances[asset] = balances.get(asset, Decimal(0)) - size_dec
            balances["USD"] = balances.get("USD", Decimal(0)) + value - fee
        
        # Write back to state
        state.write_json("state/balances.json", {k: float(v) for k, v in balances.items()})
    
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        return self.orders.get(order_id, {"status": "unknown"})
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Simulate order cancellation"""
        if order_id in self.orders:
            self.orders[order_id]["status"] = "cancelled"
        return {"success": True}
