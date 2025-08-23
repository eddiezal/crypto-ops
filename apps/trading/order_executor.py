"""Order Execution Engine"""
import json
import time
from decimal import Decimal
from datetime import datetime
from typing import Dict, List
import uuid

class OrderExecutor:
    """Simulates order execution"""
    
    def __init__(self, mode="simulate"):
        self.mode = mode
        self.orders = []
        self.fills = []
        
        with open("state/balances.json", "r") as f:
            self.balances = {k: Decimal(str(v)) for k, v in json.load(f).items()}
    
    def execute_order(self, order: Dict) -> Dict:
        """Execute a single order"""
        order_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().isoformat()
        
        product = order["product"]
        base, quote = product.split("-")
        size = Decimal(str(order["size"]))
        price = Decimal(str(order["price"]))
        side = order["side"].lower()
        
        value = size * price
        
        # Check balance
        if side == "buy":
            if self.balances.get(quote, 0) < value:
                return {
                    "id": order_id,
                    "status": "rejected",
                    "reason": f"Insufficient {quote}",
                    "timestamp": timestamp
                }
        else:
            if self.balances.get(base, 0) < size:
                return {
                    "id": order_id,
                    "status": "rejected",
                    "reason": f"Insufficient {base}",
                    "timestamp": timestamp
                }
        
        # Simulate fill
        if side == "buy":
            self.balances[quote] -= value
            self.balances[base] = self.balances.get(base, Decimal(0)) + size
        else:
            self.balances[base] -= size
            self.balances[quote] = self.balances.get(quote, Decimal(0)) + value
        
        fill = {
            "id": order_id,
            "status": "filled",
            "product": product,
            "side": side,
            "size": float(size),
            "price": float(price),
            "timestamp": timestamp,
            "balances_after": {k: float(v) for k, v in self.balances.items()}
        }
        
        self.fills.append(fill)
        return fill

if __name__ == "__main__":
    print("Order Executor ready!")
    executor = OrderExecutor()
    print(f"Current balances: {dict(executor.balances)}")
