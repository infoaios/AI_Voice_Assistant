from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any
import re
from core.nlp_utils import extract_quantity
from core.nlp_utils import all_menu_items

# ========== INTENT CLASSIFICATION ==========
class Intent(Enum):
    """Intent types for deterministic routing"""
    SMALL_TALK_GREETING = "greeting"
    SMALL_TALK_AUDIBILITY = "audibility"
    SMALL_TALK_THANKS = "thanks"
    INFO_PRICE = "info_price"
    INFO_MENU = "info_menu"
    INFO_DESCRIPTION = "info_description"
    ORDER_ADD = "order_add"
    ORDER_CONFIRM = "order_confirm"
    ORDER_REMOVE = "order_remove"
    ORDER_UPDATE = "order_update"
    ORDER_SUMMARY = "order_summary"
    ORDER_CLEAR = "order_clear"
    ORDER_FINALIZE = "order_finalize"
    ORDER_BILLING = "order_billing"
    RESTAURANT_INFO = "restaurant_info"
    UNKNOWN = "unknown"

@dataclass
class IntentResult:
    """Intent classification result"""
    intent: Intent
    confidence: float
    slots: Dict[str, Any]
    requires_confirmation: bool = False

class IntentRouter:
    """Deterministic + fallback intent router - FIXED VERSION"""
    
    def __init__(self):
        self.greeting_patterns = [
            "hello", "hi", "hey", "namaste", "good morning", 
            "good afternoon", "good evening", "greetings"
        ]
        self.audibility_patterns = [
            "can you hear me", "are you there", "hello are you", 
            "can you listen", "are you listening"
        ]
        self.thanks_patterns = [
            "thank you", "thanks", "thx", "appreciate it", 
            "thanks a lot", "thank u"
        ]
        self.price_patterns = [
            "price of", "how much is", "cost of", "price for",
            "what's the price", "what is the price", "how much does",
            "rate of", "rate for"
        ]
        self.add_patterns = [
            "i want", "i need", "i would like", "can i get",
            "order", "add", "get me", "give me", "put in"
        ]
        self.confirm_patterns = [
            "yes", "confirm", "okay", "ok", "sure", "proceed",
            "yes please", "that's correct", "correct"
        ]
        self.remove_patterns = [
            "remove", "delete", "cancel", "without", "don't add",
            "take out", "get rid of", "eliminate"
        ]
        self.update_patterns = [
            "update", "change", "modify", "make it", "change to",
            "set to", "adjust", "edit", "alter"
        ]
        self.menu_patterns = [
            "menu", "dishes", "items", "food list", "what do you have",
            "what's available", "today menu", "todays menu", "show menu"
        ]
        self.finalize_patterns = [
            "place order", "finalize", "checkout", "complete order",
            "i'm done", "done ordering", "ready to order", "proceed to checkout"
        ]
        self.billing_patterns = [
            "bill", "billing", "total", "amount", "pay", "payment",
            "check bill", "my bill", "generate bill", "final bill"
        ]
        
    def route(self, text: str, has_pending_confirmation: bool = False) -> IntentResult:
        """Route intent with deterministic rules first - FIXED VERSION"""
        text_low = text.lower().strip()
        
        # PRIORITY 1: Order confirmation (when there's a pending confirmation)
        if has_pending_confirmation:
            # Check for confirmation words at the START of the sentence
            confirm_words_start = ["yes", "yeah", "yep", "sure", "okay", "ok", "confirm", "correct", "please", "add it", "go ahead"]
            # Also check for affirmative patterns within the first few words
            first_words = " ".join(text_low.split()[:3])  # Look at first 3 words
            
            # Check if it starts with a confirmation
            if any(first_words.startswith(word) for word in confirm_words_start):
                return IntentResult(
                    intent=Intent.ORDER_CONFIRM,
                    confidence=1.0,
                    slots={"confirmed": True}
                )
            
            # Also check if any confirmation word appears prominently
            if any(word in text_low for word in confirm_words_start):
                # But make sure it's not a denial pattern like "yes, but remove..."
                if "no" not in text_low and "not" not in text_low and "don't" not in text_low:
                    return IntentResult(
                        intent=Intent.ORDER_CONFIRM,
                        confidence=0.9,
                        slots={"confirmed": True}
                    )
            
            # Check for rejection words
            reject_words = ["no", "nope", "nah", "cancel", "don't", "not", "stop", "wait"]
            if any(word in text_low.split()[:2] for word in reject_words):
                return IntentResult(
                    intent=Intent.ORDER_CONFIRM,
                    confidence=1.0,
                    slots={"confirmed": False}
                )
        
        # 2. Order finalize (place order)
        if any(pattern in text_low for pattern in self.finalize_patterns):
            return IntentResult(
                intent=Intent.ORDER_FINALIZE,
                confidence=0.95,
                slots={"text": text}
            )
        
        # 3. Billing request
        if any(pattern in text_low for pattern in self.billing_patterns):
            return IntentResult(
                intent=Intent.ORDER_BILLING,
                confidence=0.95,
                slots={"text": text}
            )
        
        # 4. Order update (change quantity) - MUST COME BEFORE SUMMARY
        update_keywords = [
            "update", "change", "modify", "make it", "change to",
            "set to", "adjust", "edit", "alter", "only want", "want only",
            "update my order", "change my order"
        ]
        if any(kw in text_low for kw in update_keywords):
            return IntentResult(
                intent=Intent.ORDER_UPDATE,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 5. Order remove - MUST COME BEFORE SUMMARY
        remove_keywords = [
            "remove", "delete", "cancel", "without", "don't add",
            "take out", "get rid of", "eliminate", "remove from my order",
            "delete from my order", "cancel from my order"
        ]
        if any(kw in text_low for kw in remove_keywords):
            return IntentResult(
                intent=Intent.ORDER_REMOVE,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 6. Small talk - Greeting
        if any(pattern in text_low for pattern in self.greeting_patterns):
            # Check if it's combined with a request
            if any(p in text_low for p in self.price_patterns + self.add_patterns + self.update_patterns + self.remove_patterns):
                pass  # Fall through to detect the actual intent
            else:
                return IntentResult(
                    intent=Intent.SMALL_TALK_GREETING,
                    confidence=1.0,
                    slots={}
                )
        
        # 7. Small talk - Audibility
        if any(pattern in text_low for pattern in self.audibility_patterns):
            return IntentResult(
                intent=Intent.SMALL_TALK_AUDIBILITY,
                confidence=1.0,
                slots={}
            )
        
        # 8. Small talk - Thanks
        if any(pattern in text_low for pattern in self.thanks_patterns):
            # Ensure it's not part of a longer sentence asking for something
            if len(text_low.split()) <= 3:
                return IntentResult(
                    intent=Intent.SMALL_TALK_THANKS,
                    confidence=1.0,
                    slots={}
                )
        
        # 9. Order summary - MORE SPECIFIC
        summary_keywords = ["my order", "cart", "summary", "what i have", "what's in my order", 
                          "order summary", "current order", "show order"]
        if any(p in text_low for p in summary_keywords):
            return IntentResult(
                intent=Intent.ORDER_SUMMARY,
                confidence=0.95,
                slots={}
            )
        
        # 10. Order clear
        if any(p in text_low for p in ["clear order", "reset order", "cancel all", "start over", "empty order"]):
            return IntentResult(
                intent=Intent.ORDER_CLEAR,
                confidence=1.0,
                slots={}
            )
        
        # 11. Info - Price (HIGH PRIORITY)
        if any(pattern in text_low for pattern in self.price_patterns):
            return IntentResult(
                intent=Intent.INFO_PRICE,
                confidence=0.95,
                slots={"text": text}
            )
        
        # 12. Info - Menu
        if any(pattern in text_low for pattern in self.menu_patterns):
            return IntentResult(
                intent=Intent.INFO_MENU,
                confidence=0.95,
                slots={"text": text}
            )
        
        # 13. Info - Description
        if any(k in text_low for k in ["what is", "tell me about", "describe", "what's in", "what does"]):
            return IntentResult(
                intent=Intent.INFO_DESCRIPTION,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 14. Order - Add (requires quantity extraction) - IMPROVED
        add_keywords = self.add_patterns + ["add", "want", "need", "like", "get", "give", "order", 
                                          "another", "more", "additional", "extra"]
        
        # Check for quantity patterns first (e.g., "2 cold coffee", "three garlic naan", "another two")
        quantity_pattern = re.search(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|another|more|additional|extra)\s+([a-z\s]+)\b', text_low)
        if quantity_pattern:
            qty = extract_quantity(text_low)
            return IntentResult(
                intent=Intent.ORDER_ADD,
                confidence=0.9,
                slots={"text": text, "quantity": qty},
                requires_confirmation=True
            )
        
        # Then check for add keywords
        if any(pattern in text_low for pattern in add_keywords):
            qty = extract_quantity(text_low)
            return IntentResult(
                intent=Intent.ORDER_ADD,
                confidence=0.85,
                slots={"text": text, "quantity": qty},
                requires_confirmation=True
            )
        
        # 15. Restaurant info
        if any(k in text_low for k in ["address", "location", "phone", "contact", "restaurant name", "your name"]):
            return IntentResult(
                intent=Intent.RESTAURANT_INFO,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 16. Check for dish names with quantities (e.g., "cold coffee 2")
        # This catches patterns that weren't caught by the regex above
        for cat, item in all_menu_items():
            item_low = item["name"].lower()
            if item_low in text_low:
                # Check if there's a number in the text
                if any(char.isdigit() for char in text_low) or any(word in text_low for word in ['one', 'two', 'three', 'four', 'five']):
                    qty = extract_quantity(text_low)
                    return IntentResult(
                        intent=Intent.ORDER_ADD,
                        confidence=0.8,
                        slots={"text": text, "quantity": qty},
                        requires_confirmation=True
                    )
        
        # 17. Single word dish names (short queries)
        words = text_low.split()
        if len(words) <= 3 and not any(p in text_low for p in ["hello", "hi", "thanks", "thank", "okay", "yes", "no"]):
            # Could be asking about a dish
            return IntentResult(
                intent=Intent.INFO_DESCRIPTION,
                confidence=0.6,
                slots={"text": text}
            )
        
        # 18. Check for phrases like "I am" or "As I am" which might be misheard confirmations
        if text_low in ["i am", "as i am", "i am.", "as i am."]:
            return IntentResult(
                intent=Intent.ORDER_CONFIRM,
                confidence=0.7,
                slots={"confirmed": True}
            )
        
        # 19. Check for goodbye phrases
        if any(word in text_low for word in ["bye", "goodbye", "see you", "farewell"]):
            return IntentResult(
                intent=Intent.SMALL_TALK_THANKS,
                confidence=0.8,
                slots={}
            )
        
        # Fallback to unknown
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            slots={"text": text}
        )

