import datetime
import re
from typing import Optional, Tuple

from core.order_manager import EnhancedOrderManager
from core.intent_router import Intent, IntentRouter
from core.response_templates import ResponseTemplates
from core.restaurant_data import REST_DATA
from core.nlp_utils import (
    apply_phonetic_corrections,
    detect_multiple_dishes,
    extract_quantity,
    find_all_dish_matches,
    menu_suggestion_string,
    normalize,
    edit_dist,
    similarity,
    all_menu_items
)

class RestaurantRAGSystem:
    """Restaurant JSON-based RAG System with Intent Router - FIXED VERSION"""
    
    def __init__(self, order_manager: EnhancedOrderManager):
        self.order = order_manager
        self.first_greeting = True
        self.conversation_history = []
        self.intent_router = IntentRouter()
        self.templates = ResponseTemplates()
        
    def is_restaurant_open(self) -> Tuple[bool, str]:
        """Check if restaurant is open"""
        now = datetime.datetime.now()
        current_hour = now.hour
        
        if 11 <= current_hour < 23:
            return True, ""
        else:
            return False, "Sorry, we're currently closed. Our hours are 11 AM to 11 PM."
    
    def check_item_availability(self, item_name: str) -> Tuple[bool, str]:
        """Check if item is available"""
        out_of_stock = ["Ice Cream", "Special Dessert"]
        
        if item_name in out_of_stock:
            return False, f"Sorry, {item_name} is currently out of stock."
        
        return True, ""
    
    def extract_customer_details(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract customer name and phone from text"""
        text_low = text.lower()
        name = None
        phone = None
        
        # Extract name
        if "my name is" in text_low:
            name = text_low.split("my name is")[1].split()[0].strip().title()
        elif "i am" in text_low or "i'm" in text_low:
            parts = text_low.replace("i'm", "i am").split("i am")
            if len(parts) > 1:
                name = parts[1].strip().split()[0].title()
        
        # Extract phone
        phone_match = re.search(r'\b\d{10}\b', text)
        if phone_match:
            phone = phone_match.group(0)
        
        return name, phone
    
    def is_english_text(self, text: str, threshold: float = 0.7) -> bool:
        """Check if text is primarily English"""
        # Count English alphabet characters
        english_chars = len(re.findall(r'[a-zA-Z\s]', text))
        total_chars = len(text) if text else 1
        
        ratio = english_chars / total_chars
        return ratio >= threshold
    
    def process_with_rag(self, text: str) -> Tuple[Optional[str], bool]:
        """
        Process query using restaurant JSON RAG with intent routing
        Returns: (response, should_use_llm)
        """

         # First, check if text is in English
        if not self.is_english_text(text):
            # If not English, ask to speak in English
            return "I'm sorry, I only understand English. Could you please speak in English?", False
        
        text_corrected = apply_phonetic_corrections(text.lower())
        rest = REST_DATA.get("restaurant", {})
        
        # Route intent first - PASS pending confirmation state
        has_pending = self.order.pending_confirmation is not None
        intent_result = self.intent_router.route(text_corrected, has_pending_confirmation=has_pending)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user", 
            "content": text,
            "intent": intent_result.intent.value,
            "confidence": intent_result.confidence
        })
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)
        
        # Check restaurant hours for order intents
        if intent_result.intent in [Intent.ORDER_ADD, Intent.ORDER_CONFIRM, Intent.ORDER_FINALIZE, 
                                   Intent.ORDER_UPDATE, Intent.ORDER_REMOVE]:
            is_open, closed_msg = self.is_restaurant_open()
            if not is_open:
                return closed_msg, False
        
        # Handle intents with deterministic responses
        
        # 1. SMALL TALK - GREETING
        if intent_result.intent == Intent.SMALL_TALK_GREETING:
            return self.templates.greeting(), False
        
        # 2. SMALL TALK - AUDIBILITY
        if intent_result.intent == Intent.SMALL_TALK_AUDIBILITY:
            return self.templates.audibility(), False
        
        # 3. SMALL TALK - THANKS
        if intent_result.intent == Intent.SMALL_TALK_THANKS:
            return self.templates.thanks(), False
        
        # 4. ORDER - CONFIRM (pending confirmation) - IMPROVED
        if intent_result.intent == Intent.ORDER_CONFIRM:
            if self.order.pending_confirmation:
                confirmed = intent_result.slots.get("confirmed", True)
                
                if confirmed:
                    pending = self.order.pending_confirmation
                    
                    # Check if this is an update/remove confirmation
                    if "action" in pending:
                        action = pending["action"]
                        item_name = pending["item"]
                        qty = pending["qty"]
                        
                        if action == "update":
                            if self.order.update_quantity(item_name, qty):
                                return self.templates.item_updated(item_name, qty) + f" {self.order.describe_order()}", False
                            else:
                                return f"{item_name} is not in your order.", False
                        elif action == "remove":
                            if self.order.remove_item(item_name, qty):
                                if self.order.is_empty():
                                    return self.templates.item_removed(item_name, qty) + " Your order is now empty.", False
                                else:
                                    return self.templates.item_removed(item_name, qty) + f" {self.order.describe_order()}", False
                            else:
                                return f"{item_name} is not in your order.", False
                    
                    # Handle multiple items
                    if isinstance(pending, list):
                        added_items = []
                        for item_conf in pending:
                            item_name = item_conf["item"]
                            qty = item_conf["qty"]
                            price = item_conf["price"]
                            
                            # Check availability
                            available, avail_msg = self.check_item_availability(item_name)
                            if not available:
                                self.order.pending_confirmation = None
                                return avail_msg, False
                            
                            self.order.add_item(item_name, price, qty)
                            added_items.append(f"{qty} {item_name}")
                        
                        self.order.pending_confirmation = None
                        response = f"Added {', '.join(added_items)}. {self.order.describe_order()}"
                        return response, False
                    else:
                        # Single item confirmation
                        item_name = pending["item"]
                        qty = pending["qty"]
                        price = pending["price"]
                        
                        # Check availability
                        available, avail_msg = self.check_item_availability(item_name)
                        if not available:
                            self.order.pending_confirmation = None
                            return avail_msg, False
                        
                        self.order.add_item(item_name, price, qty)
                        self.order.pending_confirmation = None
                        
                        # Return both confirmation and order summary
                        response = f"Added {qty} {item_name}. {self.order.describe_order()}"
                        return response, False
                else:
                    # User rejected
                    self.order.pending_confirmation = None
                    return "Okay, not adding it. What else would you like?", False
            else:
                # Handle "I am" as confirmation when there's no pending confirmation
                if text_corrected in ["i am", "as i am", "i am.", "as i am."]:
                    return "What would you like to add to your order?", False
                return "What would you like to confirm?", False
        
        # 5. ORDER - SUMMARY
        if intent_result.intent == Intent.ORDER_SUMMARY:
            return self.order.describe_order(), False
        
        # 6. ORDER - CLEAR
        if intent_result.intent == Intent.ORDER_CLEAR:
            self.order.clear()
            return self.templates.order_cleared(), False
        
        # 7. ORDER - REMOVE - FIXED LOGIC
        if intent_result.intent == Intent.ORDER_REMOVE:
            # First find all dish matches
            matches = find_all_dish_matches(text_corrected)
            
            if not matches:
                # Check if user mentioned items already in order
                order_items = [line["name"].lower() for line in self.order.lines]
                for item_name in order_items:
                    if item_name in text_corrected:
                        # Found item in order, ask for confirmation
                        qty = extract_quantity(text_corrected, default=None)
                        display_name = item_name.title()
                        
                        self.order.pending_confirmation = {
                            "item": display_name,
                            "qty": qty,
                            "action": "remove"
                        }
                        
                        if qty:
                            return self.templates.remove_confirmation(display_name, qty), False
                        else:
                            return self.templates.remove_confirmation(display_name), False
                
                return "I couldn't find that item in your order. Please specify which item you want to remove.", False
            
            # Use the best match
            _, item, score = matches[0]
            if score >= 0.7:
                qty = extract_quantity(text_corrected, default=None)
                
                # Check if item is in order
                if self.order.get_item_quantity(item["name"]) > 0:
                    # Item exists, ask for confirmation
                    self.order.pending_confirmation = {
                        "item": item["name"],
                        "qty": qty,
                        "action": "remove"
                    }
                    
                    if qty:
                        return self.templates.remove_confirmation(item["name"], qty), False
                    else:
                        return self.templates.remove_confirmation(item["name"]), False
                else:
                    return f"{item['name']} is not in your order.", False
            
            return "I couldn't find that item in your order.", False
        
        # 8. ORDER - UPDATE - FIXED LOGIC
        if intent_result.intent == Intent.ORDER_UPDATE:
            # Extract quantity
            qty = extract_quantity(text_corrected)
            
            # Find dish matches
            matches = find_all_dish_matches(text_corrected)
            
            if not matches:
                # Check if user mentioned items already in order
                order_items = [line["name"].lower() for line in self.order.lines]
                for item_name in order_items:
                    if item_name in text_corrected:
                        # Found item in order, ask for confirmation
                        display_name = item_name.title()
                        
                        self.order.pending_confirmation = {
                            "item": display_name,
                            "qty": qty,
                            "action": "update"
                        }
                        
                        return self.templates.update_confirmation(display_name, qty), False
                
                return "I couldn't find that item to update. Please specify which item you want to update.", False
            
            # Use the best match
            _, item, score = matches[0]
            if score >= 0.7:
                # Check if item is in order
                if self.order.get_item_quantity(item["name"]) > 0:
                    # Item exists, ask for confirmation
                    self.order.pending_confirmation = {
                        "item": item["name"],
                        "qty": qty,
                        "action": "update"
                    }
                    
                    return self.templates.update_confirmation(item["name"], qty), False
                else:
                    return f"{item['name']} is not in your order yet. Would you like to add it?", False
            
            return "I couldn't find that item to update.", False
        
        # 9. INFO - PRICE (NO ORDER MUTATION)
        if intent_result.intent == Intent.INFO_PRICE:
            # Detect multiple items
            separators = [' and ', ',', ' with ']
            items_to_check = [text_corrected]
            
            for sep in separators:
                if sep in text_corrected:
                    items_to_check = [p.strip() for p in text_corrected.split(sep) if p.strip()]
                    break
            
            prices = []
            for item_text in items_to_check:
                matches = find_all_dish_matches(item_text)
                if matches:
                    _, item, score = matches[0]
                    if score >= 0.7:
                        prices.append((item["name"], item["price"]))
            
            if prices:
                if len(prices) == 1:
                    return self.templates.price_single(prices[0][0], prices[0][1]), False
                else:
                    return self.templates.price_multi(prices), False
            
            return self.templates.item_not_found(), False
        
        # 10. INFO - MENU
        if intent_result.intent == Intent.INFO_MENU:
            # Check for category-specific
            for cat in REST_DATA["menu"]:
                cat_name = cat["name"].lower()
                if cat_name in text_corrected:
                    names = ", ".join(i["name"] for i in cat["items"])
                    return f"{cat['name']}: {names}", False
            
            # suggestions = menu_suggestion_string(limit_per_category=2)
            # return "Here's our menu: " + suggestions, False
            # Check if user wants to see items (asked "what items" or "what dishes")
            if any(word in text_corrected for word in ["items", "dishes", "foods", "options", "list"]):
                suggestions = menu_suggestion_string(show_items=True, limit_per_category=2)
                return "Here are some items from our menu: " + suggestions, False
            else:
                # Default: Just show categories
                categories = menu_suggestion_string(show_items=False)
                return f"We have these categories: {categories}. What would you like to know more about?", False
        
        # 11. INFO - DESCRIPTION
        if intent_result.intent == Intent.INFO_DESCRIPTION:
            matches = find_all_dish_matches(text_corrected)
            if matches:
                _, item, score = matches[0]
                if score >= 0.7:
                    desc = item.get("description", "No description available")
                    return f"{item['name']}: {desc}. Price: {item['price']} rupees.", False
            
            return "I don't have information about that dish. Could you ask about something from our menu?", False
        
        # 12. ORDER - ADD (REQUIRES CONFIRMATION)
        if intent_result.intent == Intent.ORDER_ADD:
            qty = intent_result.slots.get("quantity", 1)
            
            # Detect multiple dishes
            dish_phrases = detect_multiple_dishes(text_corrected)
            pending_items = []
            
            for dish_phrase in dish_phrases:
                # Extract quantity for this specific dish phrase
                item_qty = extract_quantity(dish_phrase, default=qty if len(dish_phrases) == 1 else 1)
                
                # Find matches for this specific dish phrase
                matches = find_all_dish_matches(dish_phrase)
                
                if not matches:
                    # Try without quantity words
                    dish_phrase_clean = re.sub(r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+', '', dish_phrase).strip()
                    matches = find_all_dish_matches(dish_phrase_clean)
                
                if matches:
                    # Take only the best match for this phrase
                    best_match = matches[0]
                    _, item, score = best_match
                    
                    if score >= 0.7:  # Good match threshold
                        pending_items.append({
                            "item": item["name"],
                            "qty": item_qty,
                            "price": item["price"]
                        })
            
            if not pending_items:
                return self.templates.item_not_found(), False
            
            if len(pending_items) == 1:
                # Single item - set pending confirmation
                item = pending_items[0]
                self.order.pending_confirmation = item
                return self.templates.confirmation_required(item["item"], item["qty"], item["price"]), False
            else:
                # Multiple items - set pending confirmation list
                self.order.pending_confirmation = pending_items
                
                # Create confirmation message for multiple items
                item_descriptions = []
                for item in pending_items:
                    total = item["qty"] * item["price"]
                    item_descriptions.append(f"{item['qty']} {item['item']} ({total:.0f} rupees)")
                
                confirmation_msg = f"Do you want to add: {', '.join(item_descriptions)} to your order?"
                return confirmation_msg, False
        
        # 13. ORDER - FINALIZE
        if intent_result.intent == Intent.ORDER_FINALIZE:
            if self.order.is_empty():
                return "Your order is empty. Please add items first.", False
            
            # Extract customer details if mentioned
            name, phone = self.extract_customer_details(text)
            if name or phone:
                self.order.add_customer_details(name, phone)
            
            # Finalize order
            success, message, order_id = self.order.finalize_order()
            if success:
                return message, False
            else:
                return message, False
        
        # 14. ORDER - BILLING
        if intent_result.intent == Intent.ORDER_BILLING:
            if self.order.is_empty():
                return "Your order is empty. Please add items first.", False
            
            # Generate bill summary
            total = self.order.subtotal()
            return f"Your bill total is {total:.0f} rupees. Would you like to place the order?", False
        
        # 15. RESTAURANT INFO
        if intent_result.intent == Intent.RESTAURANT_INFO:
            if "name" in text_corrected or "restaurant" in text_corrected:
                return f"Our restaurant name is {rest.get('name', 'Infocall Dine')}.", False
            if any(k in text_corrected for k in ["address", "location"]):
                return f"We are located at {rest.get('address', 'MG Road, Mumbai')}.", False
            if any(k in text_corrected for k in ["phone", "contact", "number"]):
                return f"You can reach us at {rest.get('phone', '+91 98765 43210')}.", False
        
        # 16. Handle quantity-only phrases like "Cold coffee 2, 3"
        # Check if this looks like a quantity update for an existing item
        if len(text_corrected.split()) <= 3 and any(char.isdigit() for char in text_corrected):
            # Check if it mentions any menu items
            for cat, item in all_menu_items():
                item_low = item["name"].lower()
                if item_low in text_corrected:
                    # This is likely a quantity specification for an item
                    qty = extract_quantity(text_corrected)
                    
                    if self.order.get_item_quantity(item["name"]) > 0:
                        # Item exists in order, ask if they want to update
                        self.order.pending_confirmation = {
                            "item": item["name"],
                            "qty": qty,
                            "price": item["price"],
                            "action": "update"
                        }
                        return self.templates.update_confirmation(item["name"], qty), False
                    else:
                        # Item not in order, ask if they want to add
                        self.order.pending_confirmation = {
                            "item": item["name"],
                            "qty": qty,
                            "price": item["price"],
                            "action": "add"
                        }
                        return self.templates.confirmation_required(item["name"], qty, item["price"]), False
        
        # 17. Handle "I want to add more" without specifying item
        if text_corrected in ["i want to add more", "add more", "more"]:
            if self.order.is_empty():
                return "Your order is empty. What would you like to add?", False
            else:
                return "What item would you like to add more of?", False
        
        # 18. Handle goodbye/exit
        if any(word in text_corrected for word in ["bye", "goodbye", "see you", "farewell", "bye-bye"]):
            return self.templates.goodbye(), False
        
        # 19. Handle "okay" without context
        if text_corrected in ["okay", "ok", "okay."]:
            if self.order.pending_confirmation:
                # Treat as confirmation
                return self.process_with_rag("yes")
            else:
                return "How can I help you?", False
        
        # 20. UNKNOWN - Let LLM handle but with strict constraints
        if intent_result.intent == Intent.UNKNOWN:
            # Check if it should be blocked from LLM
            food_keywords = [
                "coffee", "naan", "tikka", "chicken", "paneer", "dal",
                "tea", "roll", "butter", "garlic", "cold", "masala",
                "gulab", "jamun", "spring", "biryani"
            ]
            
            if any(keyword in text_corrected for keyword in food_keywords):
                # This is food-related, don't use LLM
                return "Could you please clarify what you'd like to order?", False
            
            if intent_result.confidence < 0.5:
                # Very low confidence, use LLM for general conversation
                return None, True
        
        # Default fallback
        return self.templates.clarification_needed(), False


