"""Simulate order execution"""
import json
from decimal import Decimal
from datetime import datetime

class OrderSimulator:
    def __init__(self):
        # Load current state
        with open('state/balances.json', 'r') as f:
            self.balances = json.load(f)
        
        self.orders = []
        
    def place_order(self, side, product, size, price=None):
        """Simulate order placement"""
        
        base, quote = product.split('-')
        size = Decimal(str(size))
        
        if side.lower() == 'buy':
            # Buying base with quote
            cost = size * Decimal(str(price or 95000))
            if self.balances.get(quote, 0) >= float(cost):
                self.balances[quote] -= float(cost)
                self.balances[base] = self.balances.get(base, 0) + float(size)
                
                order = {
                    'id': f'sim-{len(self.orders)+1}',
                    'side': side,
                    'product': product,
                    'size': float(size),
                    'price': price,
                    'status': 'filled',
                    'timestamp': datetime.now().isoformat()
                }
                self.orders.append(order)
                
                print(f"✅ Order filled: {side} {size} {base} @ ${price}")
                print(f"   New balances: {base}={self.balances[base]}, {quote}={self.balances[quote]}")
                
                return order
            else:
                print(f"❌ Insufficient {quote}: need {cost}, have {self.balances.get(quote, 0)}")
                return None
                
    def save_state(self):
        """Save simulated state"""
        with open('state/simulated_balances.json', 'w') as f:
            json.dump(self.balances, f, indent=2)
        print(f"💾 Saved simulated state")

# Test it
sim = OrderSimulator()
sim.place_order('buy', 'BTC-USD', 0.001, 95000)
sim.save_state()
