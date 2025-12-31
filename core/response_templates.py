import datetime
import re
from typing import Optional, Dict, Any, List, Tuple

# ========== RESPONSE TEMPLATES ==========
class ResponseTemplates:
    """Deterministic response templates"""
    
    @staticmethod
    def greeting() -> str:
        return "Hello! Welcome to our restaurant. How can I help you today?"
    
    @staticmethod
    def audibility() -> str:
        return "Yes, I can hear you. How can I help?"
    
    @staticmethod
    def thanks() -> str:
        return "You're welcome."
    
    @staticmethod
    def goodbye() -> str:
        return "Goodbye! Thank you for visiting us. Have a great day!"
    
    @staticmethod
    def price_single(item_name: str, price: float) -> str:
        return f"{item_name} costs {price:.0f} rupees"
    
    @staticmethod
    def price_multi(items: List[Tuple[str, float]]) -> str:
        parts = [f"{name} costs {price:.0f} rupees" for name, price in items]
        return " | ".join(parts)
    
    @staticmethod
    def confirmation_required(item_name: str, qty: int, price: float) -> str:
        total = qty * price
        return f"Do you want to add {qty} {item_name} for {total:.0f} rupees to your order?"
    
    @staticmethod
    def item_added(item_name: str, qty: int) -> str:
        return f"Added {qty} {item_name} to your order."
    
    @staticmethod
    def item_not_found() -> str:
        return "Sorry, I couldn't find that item. Could you please say the exact dish name?"
    
    @staticmethod
    def clarification_needed() -> str:
        return "Could you please clarify what you'd like?"
    
    @staticmethod
    def order_cleared() -> str:
        return "I've cleared your entire order. Would you like to start fresh?"
    
    @staticmethod
    def item_removed(item_name: str, qty: int = None) -> str:
        if qty:
            return f"Removed {qty} {item_name} from your order."
        return f"Removed {item_name} from your order."
    
    @staticmethod
    def item_updated(item_name: str, new_qty: int) -> str:
        return f"Updated {item_name} quantity to {new_qty}."
    
    @staticmethod
    def order_finalized(order_id: str, total: float) -> str:
        return f"Your order {order_id} has been placed successfully! Total: {total:.0f} rupees. Thank you!"
    
    @staticmethod
    def update_confirmation(item_name: str, qty: int) -> str:
        return f"Do you want to update {item_name} to {qty}?"
    
    @staticmethod
    def remove_confirmation(item_name: str, qty: int = None) -> str:
        if qty:
            return f"Do you want to remove {qty} {item_name} from your order?"
        return f"Do you want to remove {item_name} from your order?"

    @staticmethod
    def menu_categories(categories_str: str) -> str:
        """Template for menu categories only"""
        return f"We have these categories: {categories_str}. What would you like to know more about?"
    
    @staticmethod
    def menu_items(menu_str: str) -> str:
        """Template for menu items"""
        return f"Here are some items from our menu: {menu_str}"
  