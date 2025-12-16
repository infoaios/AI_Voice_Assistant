"""Order entity for managing restaurant orders"""
from typing import List, Dict, Optional


class OrderManager:
    """Enhanced order manager with variants, addons, and allergens support"""
    
    def __init__(self):
        self.lines: List[Dict] = []
        self.customer: Dict = {}
    
    def _find_line(self, name: str, variant: Optional[str] = None, addons: Optional[List[str]] = None) -> Optional[Dict]:
        """Find order line by item name, variant, and addons"""
        name_low = name.lower()
        for line in self.lines:
            if (line["name"].lower() == name_low and 
                line.get("variant") == variant and 
                set(line.get("addons", [])) == set(addons or [])):
                return line
        return None
    
    def add_item(
        self, 
        item_name: str, 
        unit_price: float, 
        qty: int = 1,
        variant: Optional[str] = None,
        addons: Optional[List[str]] = None,
        allergens: Optional[List[str]] = None,
        item_id: Optional[str] = None
    ):
        """
        Add items to order with support for variants and addons
        
        Args:
            item_name: Name of the item
            unit_price: Base price per unit
            qty: Quantity
            variant: Variant name (e.g., "Large", "Regular")
            addons: List of addon names
            allergens: List of allergens
            item_id: Item ID from menu
        """
        if qty <= 0:
            return
        
        # Calculate total price including variant and addons
        total_price = float(unit_price)
        addon_names = addons or []
        
        line = self._find_line(item_name, variant, addon_names)
        if line:
            line["qty"] += qty
        else:
            line_data = {
                "name": item_name,
                "qty": qty,
                "unit_price": total_price,
                "base_price": float(unit_price),
            }
            
            if item_id:
                line_data["item_id"] = item_id
            if variant:
                line_data["variant"] = variant
            if addon_names:
                line_data["addons"] = addon_names
            if allergens:
                line_data["allergens"] = allergens
            
            self.lines.append(line_data)
    
    def remove_item(self, item_name: str, qty: Optional[int] = None):
        """Remove items from order"""
        line = self._find_line(item_name)
        if not line:
            return
        if qty is None or qty >= line["qty"]:
            self.lines = [l for l in self.lines if l is not line]
        else:
            line["qty"] -= qty
    
    def update_quantity(self, item_name: str, new_qty: int) -> bool:
        """Update item quantity to specific amount"""
        if new_qty <= 0:
            self.remove_item(item_name)
            return True
        
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
    
    def is_empty(self) -> bool:
        """Check if order is empty"""
        return len(self.lines) == 0
    
    def subtotal(self) -> float:
        """Calculate order total"""
        return sum(l["qty"] * l["unit_price"] for l in self.lines)
    
    def to_json(self) -> dict:
        """Export order as JSON"""
        return {
            "items": self.lines,
            "subtotal": self.subtotal(),
            "customer": self.customer
        }
    
    def describe_order(self) -> str:
        """Generate order description with variants and addons"""
        if self.is_empty():
            return "You don't have any items in your order yet."
        
        parts = []
        for l in self.lines:
            item_desc = l['name']
            
            # Add variant if present
            if l.get("variant"):
                item_desc += f" ({l['variant']})"
            
            # Add addons if present
            if l.get("addons"):
                item_desc += f" with {', '.join(l['addons'])}"
            
            line_total = l["qty"] * l["unit_price"]
            parts.append(f"{l['qty']} {item_desc} ({line_total:.0f} rupees)")
        
        total = self.subtotal()
        items_str = "; ".join(parts)
        return f"Your current order: {items_str}. Total: {total:.0f} rupees."
    
    def get_allergens_summary(self) -> List[str]:
        """Get all unique allergens from the order"""
        allergens = set()
        for line in self.lines:
            if line.get("allergens"):
                allergens.update(line["allergens"])
        return sorted(list(allergens))

