import datetime
import re
from typing import Optional, Tuple, Dict, Any, List
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
    all_menu_items,
    similarity
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
            # Check for category-specific queries first
            for cat in REST_DATA["menu"]:
                cat_name = cat["name"].lower()
                # Check for patterns like "main course menu", "beverage menu", etc.
                category_patterns = [
                    f"{cat_name} menu",
                    f"{cat_name} items", 
                    f"items in {cat_name}",
                    f"dishes in {cat_name}",
                    f"{cat_name} dishes",
                    f"what's in {cat_name}",
                    f"what is in {cat_name}",
                    f"show me {cat_name}",
                    f"tell me about {cat_name}"
                ]
                
                if any(pattern in text_corrected for pattern in category_patterns):
                    names = ", ".join(i["name"] for i in cat["items"])
                    if len(cat["items"]) <= 5:
                        return f"{cat['name']} includes: {names}.", False
                    else:
                        # If many items, list first 3-4
                        first_items = ", ".join([i["name"] for i in cat["items"][:4]])
                        return f"{cat['name']} includes items like: {first_items}, and more.", False
            
            # Check if user specifically asks for ITEMS (not just categories)
            items_keywords = ["items", "dishes", "foods", "list of items", "show me items", "what items"]
            if any(word in text_corrected for word in items_keywords):
                suggestions = menu_suggestion_string(show_items=True, limit_per_category=2)
                return "Here are some items from our menu: " + suggestions, False
            
            # Check if user specifically asks for "today's menu" or "menu today"
            today_keywords = ["today menu", "todays menu", "menu today", "today's menu"]
            if any(word in text_corrected for word in today_keywords):
                categories = menu_suggestion_string(show_items=False)
                return f"Our menu today includes: {categories}. What would you like to know more about?", False
            
            # Check if user wants detailed items (asked "show me" or "what do you have")
            if any(word in text_corrected for word in ["show me", "what do you have", "what's available", "what can i get"]):
                suggestions = menu_suggestion_string(show_items=True, limit_per_category=2)
                return "Here are some items from our menu: " + suggestions, False
            
            # DEFAULT: Show only categories (not items)
            categories = menu_suggestion_string(show_items=False)
            return f"Our menu includes: {categories}. What would you like to know more about?", False
        
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
        
        # 16. INFO - CATEGORY SPECIFIC ITEMS (what's in main course?)
        if intent_result.intent == Intent.INFO_CATEGORY_ITEMS:
            category_name = intent_result.slots.get("category", "")
            
            # Find the category
            found_category = None
            for cat in REST_DATA.get("menu", []):
                if cat["name"].lower() == category_name.lower():
                    found_category = cat
                    break
            
            if found_category:
                items = found_category.get("items", [])
                if items:
                    item_names = ", ".join([item["name"] for item in items])
                    if len(items) <= 5:
                        return f"{found_category['name']} includes: {item_names}.", False
                    else:
                        # If many items, list first 3-4
                        first_items = ", ".join([item["name"] for item in items[:4]])
                        return f"{found_category['name']} includes items like: {first_items}, and more.", False
                else:
                    return f"{found_category['name']} doesn't have any items listed.", False
            else:
                # Fall back to showing all categories
                categories = menu_suggestion_string(show_items=False)
                return f"We have these categories: {categories}. Which category would you like to know about?", False
            
        # 17. Handle quantity-only phrases like "Cold coffee 2, 3"
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
        
        # 18. Handle "I want to add more" without specifying item
        if text_corrected in ["i want to add more", "add more", "more"]:
            if self.order.is_empty():
                return "Your order is empty. What would you like to add?", False
            else:
                return "What item would you like to add more of?", False
        
        # 19. Handle goodbye/exit
        if any(word in text_corrected for word in ["bye", "goodbye", "see you", "farewell", "bye-bye"]):
            return self.templates.goodbye(), False
        
        # 20. Handle "okay" without context
        if text_corrected in ["okay", "ok", "okay."]:
            if self.order.pending_confirmation:
                # Treat as confirmation
                return self.process_with_rag("yes")
            else:
                return "How can I help you?", False
        
        # 21. UNKNOWN - Let LLM handle but with strict constraints
        if intent_result.intent == Intent.UNKNOWN:
            # Check if it should be blocked from LLM
            food_keywords = [
                "coffee", "naan", "tikka", "chicken", "paneer", "dal",
                "tea", "roll", "butter", "garlic", "cold", "masala",
                "gulab", "jamun", "spring", "biryani",
                "menu", "order", "food", "dish", "item", "spicy", 
                "sweet", "drink", "beverage", "meal", "lunch", "dinner",
                "breakfast", "snack", "spice", "curry", "rice", "bread",
                "dessert", "sauce", "gravy", "fried", "grilled", "roasted"
            ]
            
            # Convert text to lowercase for case-insensitive matching
            text_lower = text_corrected.lower()
            
            # STRICT CHECK: If ANY food-related keyword is found, block LLM completely
            if any(keyword in text_lower for keyword in food_keywords):
                # This is food-related, don't use LLM
                return "I can only help with food items from our current menu. Could you please clarify what specific menu item you'd like to order?", False
            
            # Additional safety check - if user mentions ordering/eating but we don't recognize
            ordering_patterns = [
                "i want to order", "i'd like to order", "can i get", 
                "i need", "give me", "i'll have", "i'll take",
                "can you bring me", "bring me", "serve me"
            ]
            
            if any(pattern in text_lower for pattern in ordering_patterns):
                return "I can only take orders for items on our current menu. Please check our menu and specify what you'd like to order.", False
            
            # Only use LLM for very general, non-food related conversations
            if intent_result.confidence < 0.3:  # Even stricter confidence threshold
                # Double-check it's not food-related
                if not any(food_word in text_lower for food_word in ["eat", "hungry", "thirsty", "restaurant", "cafe"]):
                    return None, True
            
            # Default fallback for UNKNOWN intent
            return "I'm here to help you with food orders. Could you please specify what you'd like from our menu?", False

        # 22. VEGETARIAN OPTIONS QUERY
        if intent_result.intent == Intent.VEGETARIAN_OPTIONS:
            veg_items = []
            for cat, item in all_menu_items():
                name_low = item["name"].lower()
                
                # Check for vegetarian indicators
                is_veg = False
                veg_indicators = ["paneer", "dal", "aloo", "mushroom", "gobi", "sabzi", 
                                "vegetable", "makhani", "tadka", "palak", "gulab", "jamun",
                                "veg biryani", "masala", "naan", "roti", "rice", "tea", "coffee"]
                
                # Non-veg indicators (to exclude)
                non_veg_indicators = ["chicken", "mutton", "fish", "prawn", "egg", "meat", "lamb"]
                
                # Check name - if contains any veg indicator and NO non-veg indicators
                if any(indicator in name_low for indicator in veg_indicators):
                    if not any(non_veg in name_low for non_veg in non_veg_indicators):
                        is_veg = True
                
                # Check description if available
                desc = item.get("description", "").lower()
                if ("vegetarian" in desc or "veg" in desc) and not any(non_veg in desc for non_veg in non_veg_indicators):
                    is_veg = True
                
                if is_veg:
                    veg_items.append(item["name"])
            
            if veg_items:
                # Group by category for better response
                veg_by_cat = {}
                for cat, item in all_menu_items():
                    if item["name"] in veg_items:
                        cat_name = cat.get("name", "Other")
                        if cat_name not in veg_by_cat:
                            veg_by_cat[cat_name] = []
                        veg_by_cat[cat_name].append(item["name"])
                
                response_parts = []
                for cat_name, items in veg_by_cat.items():
                    if items:
                        # Limit to 3 items per category for readability
                        response_parts.append(f"{cat_name}: {', '.join(items[:3])}")
                
                if response_parts:
                    response = "We have these vegetarian options: " + "; ".join(response_parts)
                    return response, False
                else:
                    return "We have vegetarian dishes like Paneer Tikka, Dal Makhani, Garlic Naan, and Gulab Jamun.", False
            
            return "We have vegetarian dishes like Paneer Tikka, Dal Makhani, Garlic Naan, and Gulab Jamun.", False
                
        # Default fallback
        return self.templates.clarification_needed(), False