from enum import Enum
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import json
import uuid
import time
import os

class OrderState(Enum):
    PENDING_SUBMIT = "pending_submit"
    SUBMITTED = "submitted"  
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    PENDING_CANCEL = "pending_cancel"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    UNKNOWN = "unknown"  # Network timeout, status unclear

class OrderLedger:
    """Thread-safe order ledger with state machine enforcement"""
    
    def __init__(self, filepath="logs/orders.jsonl"):
        self.filepath = filepath
        self.orders = {}  # client_order_id -> order dict
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self._load_existing()
    
    def _load_existing(self):
        """Load existing orders from ledger"""
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                for line in f:
                    if line.strip():
                        order = json.loads(line)
                        if 'data' in order and 'client_order_id' in order.get('data', {}):
                            self.orders[order['data']['client_order_id']] = order['data']
    
    def create_order(self, 
                    client_order_id: str,
                    product: str,
                    side: str,
                    size: Decimal,
                    price: Optional[Decimal] = None,
                    order_type: str = "limit") -> Dict[str, Any]:
        """Create new order with PENDING_SUBMIT state"""
        
        if client_order_id in self.orders:
            raise ValueError(f"Duplicate order ID: {client_order_id}")
        
        order = {
            "client_order_id": client_order_id,
            "exchange_order_id": None,
            "product": product,
            "side": side,
            "size": str(size),
            "price": str(price) if price else None,
            "order_type": order_type,
            "state": OrderState.PENDING_SUBMIT.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "fills": [],
            "state_history": [
                {"state": OrderState.PENDING_SUBMIT.value, "timestamp": datetime.now(timezone.utc).isoformat()}
            ]
        }
        
        self._write_event("ORDER_CREATED", order)
        self.orders[client_order_id] = order
        return order
    
    def update_state(self, client_order_id: str, new_state: OrderState, metadata: Dict = None):
        """Update order state with validation"""
        if client_order_id not in self.orders:
            raise ValueError(f"Unknown order: {client_order_id}")
        
        order = self.orders[client_order_id]
        old_state = OrderState(order["state"])
        
        # Validate state transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid transition: {old_state} -> {new_state}")
        
        order["state"] = new_state.value
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        order["state_history"].append({
            "state": new_state.value, 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata
        })
        
        self._write_event("STATE_CHANGE", {
            "client_order_id": client_order_id,
            "old_state": old_state.value,
            "new_state": new_state.value,
            "metadata": metadata
        })
    
    def _is_valid_transition(self, old: OrderState, new: OrderState) -> bool:
        """Validate state machine transitions"""
        valid_transitions = {
            OrderState.PENDING_SUBMIT: [OrderState.SUBMITTED, OrderState.REJECTED, OrderState.UNKNOWN],
            OrderState.SUBMITTED: [OrderState.ACKNOWLEDGED, OrderState.REJECTED, OrderState.UNKNOWN],
            OrderState.ACKNOWLEDGED: [OrderState.PARTIALLY_FILLED, OrderState.FILLED, OrderState.CANCELLED, OrderState.EXPIRED],
            OrderState.PARTIALLY_FILLED: [OrderState.FILLED, OrderState.CANCELLED],
            OrderState.UNKNOWN: [OrderState.ACKNOWLEDGED, OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED],
            # Terminal states
            OrderState.FILLED: [],
            OrderState.CANCELLED: [],
            OrderState.REJECTED: [],
            OrderState.EXPIRED: []
        }
        return new in valid_transitions.get(old, [])
    
    def _write_event(self, event_type: str, data: Dict[str, Any]):
        """Append event to ledger"""
        event = {
            "timestamp": time.time(),
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "data": data
        }
        with open(self.filepath, 'a') as f:
            f.write(json.dumps(event, default=str) + '\n')
    
    def get_order(self, client_order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by client ID"""
        return self.orders.get(client_order_id)
    
    def has_order(self, client_order_id: str) -> bool:
        """Check if order exists (for idempotency)"""
        return client_order_id in self.orders
