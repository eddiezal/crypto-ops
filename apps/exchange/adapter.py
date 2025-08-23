from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

class ExchangeAdapter(ABC):
    """Base interface for all exchange adapters"""
    
    @abstractmethod
    def get_balances(self) -> Dict[str, Any]:
        """Get current balances"""
        pass
    
    @abstractmethod
    def get_ticker(self, product_id: str) -> Dict[str, Any]:
        """Get current price for a product"""
        pass
    
    @abstractmethod
    def place_limit_order(self, 
                         product_id: str, 
                         side: str, 
                         size: str, 
                         price: str, 
                         client_order_id: str) -> Dict[str, Any]:
        """Place a limit order"""
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        pass
