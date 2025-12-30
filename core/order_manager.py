import datetime
import json
import time
from pathlib import Path
from typing import Optional, Tuple


class EnhancedOrderManager:
    """Enhanced order manager with all features"""
    
    def __init__(self):
        self.lines = []
        self.customer = {}
        self.pending_confirmation = None
        self.order_id = None
        self.order_timestamp = None
    
    def _find_line(self, name: str):
        """Find order line by item name"""
        name_low = name.lower()
        for line in self.lines:
            if line["name"].lower() == name_low:
                return line
        return None
    
    def add_item(self, item_name: str, unit_price: float, qty: int = 1):
        """Add items to order"""
        if qty <= 0:
            return
        line = self._find_line(item_name)
        if line:
            line["qty"] += qty
        else:
            self.lines.append({
                "name": item_name,
                "qty": qty,
                "unit_price": float(unit_price),
            })
    
    def remove_item(self, item_name: str, qty=None):
        """Remove items from order"""
        line = self._find_line(item_name)
        if not line:
            return False
        if qty is None or qty >= line["qty"]:
            self.lines = [l for l in self.lines if l is not line]
            return True
        else:
            line["qty"] -= qty
            return True
    
    def update_quantity(self, item_name: str, new_qty: int):
        """Update item quantity to specific amount"""
        if new_qty <= 0:
            return self.remove_item(item_name)
        
        line = self._find_line(item_name)
        if line:
            line["qty"] = new_qty
            return True
        return False
    
    def get_item_quantity(self, item_name: str) -> int:
        """Get current quantity of item"""
        line = self._find_line(item_name)
        return line["qty"] if line else 0
    
    def clear(self):
        """Clear entire order"""
        self.lines = []
        self.customer = {}
        self.pending_confirmation = None
    
    def is_empty(self) -> bool:
        """Check if order is empty"""
        return len(self.lines) == 0
    
    def subtotal(self) -> float:
        """Calculate order total"""
        return sum(l["qty"] * l["unit_price"] for l in self.lines)
    
    def to_json(self) -> dict:
        """Export order as JSON"""
        return {
            "order_id": self.order_id,
            "timestamp": self.order_timestamp,
            "items": self.lines,
            "subtotal": self.subtotal(),
            "customer": self.customer
        }
    
    def describe_order(self) -> str:
        """Generate order description"""
        if self.is_empty():
            return "You don't have any items in your order yet."
        
        parts = []
        for l in self.lines:
            line_total = l["qty"] * l["unit_price"]
            parts.append(f"{l['qty']} {l['name']} ({line_total:.0f} rupees)")
        
        total = self.subtotal()
        items_str = "; ".join(parts)
        return f"Your current order: {items_str}. Total: {total:.0f} rupees."
    
    def add_customer_details(self, name: str = None, phone: str = None):
        """Add customer details to order"""
        if name:
            self.customer["name"] = name
        if phone:
            self.customer["phone"] = phone
    
    def finalize_order(self) -> Tuple[bool, str, Optional[str]]:
        """Finalize order and save to JSON file"""
        if self.is_empty():
            return False, "Your order is empty. Please add items first.", None
        
        # Generate order ID and timestamp
        self.order_id = f"ORD{int(time.time())}"
        self.order_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare order data
        order_data = {
            "order_id": self.order_id,
            "timestamp": self.order_timestamp,
            "items": [line.copy() for line in self.lines],
            "subtotal": self.subtotal(),
            "total": self.subtotal(),  # Add tax if needed
            "customer": self.customer.copy() if self.customer else {}
        }
        
        # Save to file
        try:
            orders_dir = Path("orders")
            orders_dir.mkdir(exist_ok=True)
            
            # Append to orders history
            history_file = orders_dir / "orders_history.json"
            if history_file.exists():
                with open(history_file, 'r') as f:
                    orders_history = json.load(f)
            else:
                orders_history = []
            
            orders_history.append(order_data)
            
            with open(history_file, 'w') as f:
                json.dump(orders_history, f, indent=2)
            
            # Also save individual order file
            order_file = orders_dir / f"{self.order_id}.json"
            with open(order_file, 'w') as f:
                json.dump(order_data, f, indent=2)
            
            # Create success message
            customer_name = self.customer.get("name", "Customer")
            phone = self.customer.get("phone", "N/A")
            total_amount = self.subtotal()
            
            success_msg = (
                f"Perfect! Your order {self.order_id} has been placed successfully! "
                f"Order total: {total_amount:.0f} rupees. "
                f"Thank you for dining with us!"
            )
            
            # Clear the order for next customer
            self.clear()
            
            return True, success_msg, self.order_id
            
        except Exception as e:
            print(f"❌ Error saving order: {e}")
            return False, f"Sorry, there was an error processing your order: {e}", None

