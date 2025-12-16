"""
Dialog manager for conversation state and flow

This manager depends on interfaces, not concrete implementations.
Changes to service implementations won't affect this manager.
"""
import re
from typing import Optional, List, Dict

# Use interfaces for stable contracts
try:
    from core.interfaces import (
        IMenuRepository,
        IOrderManager,
        IEntityService,
        IActionService,
        IPolicyService,
    )
except ImportError:
    # Fallback for backward compatibility
    from repos.json_repo import JSONRepository as IMenuRepository
    from repos.entities.order_entity import OrderManager as IOrderManager
    from services.business.entity_service import EntityService as IEntityService
    from services.business.action_service import ActionService as IActionService
    from services.business.policy_service import PolicyService as IPolicyService


class DialogManager:
    """
    Manages conversation state and dialog flow
    
    Depends on service interfaces, allowing implementations to change without affecting this manager.
    """
    
    def __init__(
        self, 
        menu_repo: IMenuRepository,
        entity_service: IEntityService,
        action_service: IActionService,
        policy_service: IPolicyService
    ):
        """
        Initialize dialog manager with service interfaces
        
        Args:
            menu_repo: Menu repository interface
            entity_service: Entity extraction service interface
            action_service: Action execution service interface
            policy_service: Policy service interface
        """
        self.menu_repo = menu_repo
        self.entity_service = entity_service
        self.action_service = action_service
        self.policy_service = policy_service
    
    def menu_suggestion_string(self, limit_per_category: Optional[int] = None) -> str:
        """Build menu suggestion string"""
        parts = []
        for c in self.menu_repo.get_menu():
            items_list = c.get("items", [])
            if limit_per_category is not None:
                items_list = items_list[:limit_per_category]
            names = ", ".join(i["name"] for i in items_list)
            if names:
                parts.append(f"{c['name']}: {names}")
        return " | ".join(parts) if parts else "our current menu items."
    
    def unavailable_item_fallback(self) -> str:
        """Response when item not found"""
        return f"Sorry, we don't have that item. Could you please specify the exact dish name you want?"
    
    def process_message(self, text: str, order: IOrderManager) -> Optional[str]:
        """
        Process user message and return response.
        Returns None if message should be handled by LLM.
        """
        # Apply phonetic corrections first
        text_low = self.entity_service.apply_phonetic_corrections(text)
        text = text_low  # Use corrected text for processing
        
        rest = self.menu_repo.get_restaurant_info()
        
        # 1. Check restaurant hours
        is_open, closed_msg = self.policy_service.is_restaurant_open()
        if not is_open and any(kw in text_low for kw in ["order", "want", "get", "add"]):
            return closed_msg
        
        # 2. Handle order finalization
        success, msg = self.action_service.finalize_order(order, text)
        if success and msg:
            return msg
        
        # 3. CLEAR ORDER
        if any(p in text_low for p in ["clear order", "reset order", "cancel all", "start over"]):
            order.clear()
            return "I've cleared your entire order. Would you like to start fresh?"
        
        # 4. REMOVE specific items
        if any(p in text_low for p in ["remove", "without", "don't add", "cancel the", "delete"]):
            matches = self.entity_service.find_all_dish_matches(text_low)
            if matches:
                qty = self.entity_service.extract_quantity(text_low, default=None)
                removed = []
                for _, item, _ in matches:
                    order.remove_item(item["name"], qty)
                    removed.append(item["name"])
                
                if order.is_empty():
                    return f"I removed {', '.join(removed)}. Your order is now empty."
                else:
                    return f"I removed {', '.join(removed)}. {order.describe_order()}"
            return "I couldn't find that item in your order."
        
        # 5. UPDATE quantity
        if any(kw in text_low for kw in ["change to", "make it", "update to"]):
            qty = self.entity_service.extract_quantity(text_low)
            matches = self.entity_service.find_all_dish_matches(text_low)
            if matches:
                _, item, _ = matches[0]
                if order.update_quantity(item["name"], qty):
                    return f"Updated {item['name']} to {qty}. {order.describe_order()}"
                else:
                    return f"{item['name']} is not in your order yet. Would you like to add it?"
        
        # 6. ADD items with quantity
        if any(p in text_low for p in ["i want", "i need", "i would like", "can i get", "order", "add", "get me", "put in", "give me"]):
            # Detect if multiple dishes mentioned
            dish_phrases = self.entity_service.detect_multiple_dishes(text_low)
            
            added_names = []
            total_qty = 0
            
            for dish_phrase in dish_phrases:
                # Extract quantity for this specific dish phrase
                qty = self.entity_service.extract_quantity(dish_phrase, default=1)
                
                # Find matches for this specific dish phrase
                matches = self.entity_service.find_all_dish_matches(dish_phrase)
                
                if not matches:
                    # Try without quantity words
                    dish_phrase_clean = re.sub(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+', '', dish_phrase).strip()
                    matches = self.entity_service.find_all_dish_matches(dish_phrase_clean)
                
                if matches:
                    # Take only the best match for this phrase
                    best_match = matches[0]
                    _, item, score = best_match
                    
                    if score >= 0.7:  # Good match threshold
                        # Check availability
                        available, avail_msg = self.policy_service.check_item_availability(item["name"])
                        if not available:
                            return avail_msg
                        
                        # Detect variant (e.g., "large", "regular", "boneless")
                        variant = self._detect_variant(dish_phrase, item)
                        
                        # Detect addons (e.g., "with extra cheese", "with raita")
                        addons = self._detect_addons(dish_phrase, item)
                        
                        # Get price based on variant
                        base_price = self._get_item_price(item, variant)
                        
                        # Calculate total price including addons
                        total_price = base_price
                        if addons:
                            addon_prices = {a["name"]: a["price"] for a in item.get("addons", [])}
                            for addon_name in addons:
                                if addon_name in addon_prices:
                                    total_price += addon_prices[addon_name]
                        
                        # Get allergens
                        allergens = item.get("allergens", [])
                        
                        # Add to order with full details
                        order.add_item(
                            item["name"], 
                            total_price, 
                            qty,
                            variant=variant,
                            addons=addons,
                            allergens=allergens,
                            item_id=item.get("id")
                        )
                        
                        # Build description for confirmation
                        item_desc = item['name']
                        if variant:
                            item_desc += f" ({variant})"
                        if addons:
                            item_desc += f" with {', '.join(addons)}"
                        added_names.append(f"{qty} {item_desc}")
                        total_qty += qty
            
            if not added_names:
                return self.unavailable_item_fallback()
            
            added_str = ", ".join(added_names)
            return f"Great! I've added {added_str}. {order.describe_order()}"
        
        # 7. ORDER SUMMARY / TOTAL
        if any(p in text_low for p in ["total", "bill", "amount", "my order", "cart", "summary"]):
            return order.describe_order()
        
        # Restaurant name
        if ("restaurant" in text_low and "name" in text_low) or "your restaurant" in text_low:
            if rest:
                return f"Our restaurant name is {rest.get('name', 'Infocall Dine')}."

        # Address / location
        if any(k in text_low for k in ["address", "location", "where are you", "where is your restaurant", "address of your restaurant"]):
            if rest:
                return f"We are located at {rest.get('address', 'MG Road, Mumbai')}."

        # Phone / contact
        if any(k in text_low for k in ["phone", "mobile", "contact", "number"]):
            if rest:
                return f"You can reach us at {rest.get('phone', '+91 98765 43210')}."
        
        # 9. Menu queries
        if any(k in text_low for k in ["menu", "dishes", "items", "food list", "what do you have", "what's available"]):
            # Category-specific handling
            for cat in self.json_repo.get_menu():
                cat_name = cat["name"].lower()
                if cat_name in text_low:
                    names = ", ".join(i["name"] for i in cat["items"])
                    return f"{cat['name']}: {names}"
            
            suggestions = self.menu_suggestion_string(limit_per_category=2)
            return "Here's our menu: " + suggestions
        
        # 10. Price queries
        if any(k in text_low for k in ["price", "cost", "rupees", "rs", "₹", "amount for", "rate"]):
            matches = self.entity_service.find_all_dish_matches(text)
            if matches:
                prices = []
                for _, item, score in matches:
                    if score >= 0.7:
                        prices.append(f"{item['name']} costs {item['price']} rupees")
                if prices:
                    return " | ".join(prices)
            return "I'm not sure which dish you're asking about. Could you please say the exact dish name?"
        
        # 11. Dish description (enhanced with variants, addons, allergens)
        if any(k in text_low for k in ["what is", "tell me about", "describe", "what's in"]):
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                desc = item.get("description", "No description available")
                price_info = f"Price: {item['price']} rupees"
                
                # Add variant info if available
                variants = item.get("variants", [])
                if variants:
                    variant_prices = ", ".join([f"{v['name']}: {v['price']} rupees" for v in variants])
                    price_info += f". Available sizes: {variant_prices}"
                
                # Add allergen info
                allergens = item.get("allergens", [])
                allergen_info = ""
                if allergens:
                    allergen_info = f" Contains: {', '.join(allergens)}."
                
                return f"{item['name']}: {desc}. {price_info}.{allergen_info}"
            else:
                return "I don't have information about that dish. Could you ask for something from our menu?"
        
        # 12. HOW TO MAKE queries - CRITICAL TO CATCH THESE
        if any(k in text_low for k in ["how to make", "how do you make", "how is it made", "how it's made", "recipe"]):
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                return "I can tell you we have " + item["name"] + " on our menu, but I don't have the recipe details."
            else:
                return "Sorry, we don't have that item on our menu. Would you like to know about something we do have?"
        
        # 13. Vegetarian / veg options queries
        if any(k in text_low for k in ["veg option", "vegetable option", "vegetarian option", "veg options", "vegetable options"]):
            veg_keywords = ["paneer", "veg", "dal", "aloo", "mushroom", "gobi", "sabzi"]
            veg_items = []

            for _, item in self.menu_repo.all_menu_items():
                name_low = item["name"].lower()
                if any(kw in name_low for kw in veg_keywords):
                    veg_items.append(item["name"])

            if veg_items:
                limited = veg_items[:5]
                return "Some vegetarian options are: " + ", ".join(limited) + "."

            return "We have vegetarian options. You can ask for Paneer dishes, Dal Makhani, or Veg Biryani."
        
        # 14. QUANTITY queries like "On 21 Gulab Jamun" or "21 Gulab Jamun"
        quantity_match = re.search(r'\b(\d+)\s+([a-z\s]+)\b', text_low)
        if quantity_match:
            qty = int(quantity_match.group(1))
            item_text = quantity_match.group(2).strip()
            
            _, item, score = self.entity_service.best_dish_match(item_text)
            if item and score >= 0.7:
                order.add_item(item["name"], item["price"], qty)
                return f"Added {qty} {item['name']} to your order. {order.describe_order()}"
        
        # 15. If user just says a dish name without context
        words = text_low.split()
        if len(words) <= 3:  # Short queries like "Gulab Jamun", "butter chicken"
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                current_qty = order.get_item_quantity(item["name"])
                if current_qty > 0:
                    return f"You have {current_qty} {item['name']} in your order. Would you like to add more?"
                else:
                    return f"Yes, we have {item['name']} for {item['price']} rupees. Would you like to order it?"
        
        # 16. Beverage queries
        if any(k in text_low for k in ["drink", "beverage", "coffee", "tea", "soda", "cold drink"]):
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                return f"Yes, we have {item['name']} for {item['price']} rupees."
        
        # 17. Allergen queries
        if any(k in text_low for k in ["allergen", "allergy", "contains", "dairy", "nuts", "gluten"]):
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                allergens = item.get("allergens", [])
                if allergens:
                    return f"{item['name']} contains: {', '.join(allergens)}."
                else:
                    return f"{item['name']} has no listed allergens."
            else:
                # Check order allergens
                order_allergens = order.get_allergens_summary()
                if order_allergens:
                    return f"Your order contains: {', '.join(order_allergens)}."
                return "I can check allergens for specific dishes. Which dish would you like to know about?"
        
        # 18. Variant queries (e.g., "what sizes are available for butter chicken")
        if any(k in text_low for k in ["size", "variant", "option", "available size", "what size"]):
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                variants = item.get("variants", [])
                if variants:
                    variant_list = ", ".join([f"{v['name']} ({v['price']} rupees)" for v in variants])
                    return f"{item['name']} is available in: {variant_list}."
                else:
                    return f"{item['name']} is available in regular size only."
        
        # 19. Addon queries (e.g., "what can I add to paneer tikka")
        if any(k in text_low for k in ["addon", "extra", "can i add", "what can i add", "add to"]):
            _, item, score = self.entity_service.best_dish_match(text)
            if item and score >= 0.7:
                addons = item.get("addons", [])
                if addons:
                    addon_list = ", ".join([f"{a['name']} (+{a['price']} rupees)" for a in addons])
                    return f"You can add to {item['name']}: {addon_list}."
                else:
                    return f"{item['name']} doesn't have additional addons available."
        
        return None  # Let LLM handle
    
    def _detect_variant(self, text: str, item: Dict) -> Optional[str]:
        """Detect variant from user text (e.g., large, regular, boneless)"""
        text_low = text.lower()
        variants = item.get("variants", [])
        
        for variant in variants:
            variant_name_low = variant["name"].lower()
            if variant_name_low in text_low:
                return variant["name"]
        
        return None
    
    def _detect_addons(self, text: str, item: Dict) -> Optional[List[str]]:
        """Detect addons from user text (e.g., with extra cheese, with raita)"""
        text_low = text.lower()
        addons = item.get("addons", [])
        detected = []
        
        # Common patterns
        if "with" in text_low or "add" in text_low or "extra" in text_low:
            for addon in addons:
                addon_name_low = addon["name"].lower()
                # Check if addon name appears in text
                addon_words = addon_name_low.split()
                if any(word in text_low for word in addon_words if len(word) > 2):  # Ignore short words
                    detected.append(addon["name"])
        
        return detected if detected else None
    
    def _get_item_price(self, item: Dict, variant: Optional[str] = None) -> float:
        """Get item price based on variant"""
        if variant:
            variants = item.get("variants", [])
            for v in variants:
                if v["name"].lower() == variant.lower():
                    return float(v["price"])
        
        # Return base price
        return float(item.get("price", 0))

