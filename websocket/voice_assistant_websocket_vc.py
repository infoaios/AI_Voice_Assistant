# My restaurant_voice_assistant_websocket_voice_cloning.py
# batch for compress voice - 5 second audio
# ffmpeg -i data/saved_voices/refe2.wav -t 8 -ar 16000 -ac 1 -acodec pcm_s16le data/saved_voices/refe2_compressed.wav

import asyncio
import websockets
import json
import base64
import os
import time
import queue
import numpy as np
import logging
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv
import datetime
import re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import subprocess
import tempfile

# Setup minimal logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

try:
    import sounddevice as sd
    import soundfile as sf
    import io
    AUDIO_CAPTURE_AVAILABLE = True
except ImportError:
    AUDIO_CAPTURE_AVAILABLE = False
    logger.error("❌ Install: pip install sounddevice soundfile numpy")
    exit(1)

# ========== AUDIO TRIMMING FUNCTIONS ==========
def trim_to_5_seconds(input_path, output_path):
    """
    Trim any audio file to first 5 seconds
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output audio file (first 5 seconds)
    """
    try:
        # Construct ffmpeg command to TRIM (not compress)
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file without asking
            '-i', input_path,
            '-t', '5',  # Take only first 5 seconds
            '-ar', '16000',  # Sample rate 16000 Hz
            '-ac', '1',  # Mono channel
            '-acodec', 'pcm_s16le',  # Audio codec
            '-map_metadata', '-1',  # Remove metadata
            output_path
        ]
        
        print(f"  ↳ Trimming voice reference to 5 seconds...")
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✓ Voice reference trimmed: {output_path}")
            return True
        else:
            print(f"  ✗ FFmpeg error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("  ✗ Error: ffmpeg not found. Please install ffmpeg.")
        print("    On Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("    On macOS: brew install ffmpeg")
        print("    On Windows: Download from https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def get_audio_duration(input_path):
    """
    Get duration of audio file using ffprobe
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except:
        return None

def process_audio_file_for_voice_reference(input_path):
    """
    Process audio file for voice reference: if >500KB or >10s, trim to 5 seconds
    Returns: (processed_audio_bytes, trimmed_flag)
    """
    try:
        # Check file size
        file_size_bytes = Path(input_path).stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        # Get audio duration
        duration = get_audio_duration(input_path)
        duration_sec = duration if duration else 0
        
        print(f"  ↳ Voice reference file: {file_size_kb:.1f}KB, {duration_sec:.1f}s")
        
        # Check if trimming is needed
        needs_trimming = file_size_bytes > (500 * 1024) or (duration and duration > 10)
        
        if needs_trimming:
            print(f"  ⚠️  Voice reference needs trimming (size: {file_size_kb:.1f}KB, duration: {duration_sec:.1f}s)")
            
            # Create a temporary file for trimmed audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_output = tmp_file.name
            
            # Trim to 5 seconds
            success = trim_to_5_seconds(input_path, temp_output)
            
            if success:
                # Read trimmed audio
                with open(temp_output, 'rb') as f:
                    audio_bytes = f.read()
                
                # Clean up temp file
                try:
                    os.unlink(temp_output)
                except:
                    pass
                
                # Verify trimmed size
                trimmed_kb = len(audio_bytes) / 1024
                trimmed_duration = get_audio_duration(temp_output) if os.path.exists(temp_output) else 0
                
                print(f"  ✓ Trimmed to: {trimmed_kb:.1f}KB, {trimmed_duration:.1f}s")
                return audio_bytes, True
            else:
                # If trimming fails, use original (with warning)
                print(f"  ⚠️  Trimming failed, using original file (may cause issues)")
                with open(input_path, 'rb') as f:
                    return f.read(), False
        else:
            # File is within limits, use as-is
            print(f"  ✓ Voice reference within limits, using as-is")
            with open(input_path, 'rb') as f:
                return f.read(), False
                
    except Exception as e:
        print(f"  ✗ Error processing voice reference: {e}")
        return None, False

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
    ORDER_SUMMARY = "order_summary"
    ORDER_CLEAR = "order_clear"
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
    """Deterministic + fallback intent router"""
    
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
            "remove", "delete", "cancel", "without", "don't add"
        ]
        self.menu_patterns = [
            "menu", "dishes", "items", "food list", "what do you have",
            "what's available", "today menu", "todays menu", "show menu"
        ]
        
    def route(self, text: str, has_pending_confirmation: bool = False) -> IntentResult:
        """Route intent with deterministic rules first"""
        text_low = text.lower().strip()
        
        # PRIORITY 1: Order confirmation (when there's a pending confirmation)
        # This must come FIRST before any other checks
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
        
        # 2. Small talk - Greeting
        if any(pattern in text_low for pattern in self.greeting_patterns):
            # Check if it's combined with a request
            if any(p in text_low for p in self.price_patterns + self.add_patterns):
                pass  # Fall through to detect the actual intent
            else:
                return IntentResult(
                    intent=Intent.SMALL_TALK_GREETING,
                    confidence=1.0,
                    slots={}
                )
        
        # 3. Small talk - Audibility
        if any(pattern in text_low for pattern in self.audibility_patterns):
            return IntentResult(
                intent=Intent.SMALL_TALK_AUDIBILITY,
                confidence=1.0,
                slots={}
            )
        
        # 4. Small talk - Thanks
        if any(pattern in text_low for pattern in self.thanks_patterns):
            # Ensure it's not part of a longer sentence asking for something
            if len(text_low.split()) <= 3:
                return IntentResult(
                    intent=Intent.SMALL_TALK_THANKS,
                    confidence=1.0,
                    slots={}
                )
        
        # 5. Order summary
        if any(p in text_low for p in ["total", "bill", "amount", "my order", "cart", "summary"]):
            return IntentResult(
                intent=Intent.ORDER_SUMMARY,
                confidence=0.95,
                slots={}
            )
        
        # 6. Order clear
        if any(p in text_low for p in ["clear order", "reset order", "cancel all", "start over"]):
            return IntentResult(
                intent=Intent.ORDER_CLEAR,
                confidence=1.0,
                slots={}
            )
        
        # 7. Order remove
        if any(p in text_low for p in self.remove_patterns):
            return IntentResult(
                intent=Intent.ORDER_REMOVE,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 8. Info - Price (HIGH PRIORITY)
        if any(pattern in text_low for pattern in self.price_patterns):
            return IntentResult(
                intent=Intent.INFO_PRICE,
                confidence=0.95,
                slots={"text": text}
            )
        
        # 9. Info - Menu
        if any(pattern in text_low for pattern in self.menu_patterns):
            return IntentResult(
                intent=Intent.INFO_MENU,
                confidence=0.95,
                slots={"text": text}
            )
        
        # 10. Info - Description
        if any(k in text_low for k in ["what is", "tell me about", "describe", "what's in"]):
            return IntentResult(
                intent=Intent.INFO_DESCRIPTION,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 11. Order - Add (requires quantity extraction)
        if any(pattern in text_low for pattern in self.add_patterns):
            # Check if quantity is mentioned
            qty = extract_quantity(text_low)
            return IntentResult(
                intent=Intent.ORDER_ADD,
                confidence=0.85,
                slots={"text": text, "quantity": qty},
                requires_confirmation=True
            )
        
        # 12. Quantity pattern (e.g., "21 gulab jamun", "two coffee")
        quantity_match = re.search(r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+([a-z\s]+)\b', text_low)
        if quantity_match:
            return IntentResult(
                intent=Intent.ORDER_ADD,
                confidence=0.9,
                slots={"text": text, "quantity": extract_quantity(text_low)},
                requires_confirmation=True
            )
        
        # 13. Restaurant info
        if any(k in text_low for k in ["address", "location", "phone", "contact", "restaurant name"]):
            return IntentResult(
                intent=Intent.RESTAURANT_INFO,
                confidence=0.9,
                slots={"text": text}
            )
        
        # 14. Single word dish names (short queries)
        words = text_low.split()
        if len(words) <= 3 and not any(p in text_low for p in ["hello", "hi", "thanks", "thank"]):
            # Could be asking about a dish
            return IntentResult(
                intent=Intent.INFO_DESCRIPTION,
                confidence=0.6,
                slots={"text": text}
            )
        
        # Fallback to unknown
        return IntentResult(
            intent=Intent.UNKNOWN,
            confidence=0.0,
            slots={"text": text}
        )

# ========== LOAD RESTAURANT DATA ==========
try:
    possible_paths = [
        "restaurant_data.json",
        "data/restaurant_data.json",
        "../data/restaurant_data.json",
        "./data/restaurant_data.json"
    ]
    
    data_loaded = False
    for data_path in possible_paths:
        try:
            if Path(data_path).exists():
                with open(data_path, "r", encoding="utf-8") as f:
                    REST_DATA = json.load(f)
                data_loaded = True
                break
        except Exception as e:
            continue
    
    if not data_loaded:
        REST_DATA = {
            "restaurant": {
                "name": "Infocall Dine",
                "address": "MG Road, Mumbai",
                "phone": "+91 98765 43210"
            },
            "menu": [
                {
                    "name": "Starters",
                    "items": [
                        {"name": "Paneer Tikka", "price": 250, "description": "Grilled cottage cheese"},
                        {"name": "Spring Roll", "price": 180, "description": "Vegetable spring rolls"}
                    ]
                },
                {
                    "name": "Main Course",
                    "items": [
                        {"name": "Butter Chicken", "price": 350, "description": "Chicken in butter sauce"},
                        {"name": "Dal Makhani", "price": 220, "description": "Black lentils"}
                    ]
                }
            ]
        }
except Exception as e:
    REST_DATA = {}

def all_menu_items():
    """Generator for all menu items"""
    for cat in REST_DATA.get("menu", []):
        for item in cat.get("items", []):
            yield cat, item

# ========== FUZZY MATCHING FUNCTIONS ==========
def normalize(w: str) -> str:
    """Normalize word for matching"""
    return "".join(x for x in w.lower() if x.isalpha())

def edit_dist(a: str, b: str) -> int:
    """Calculate Levenshtein distance"""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        ndp = [i]
        for j, cb in enumerate(b, 1):
            ndp.append(min(
                dp[j] + 1,
                ndp[-1] + 1,
                dp[j - 1] + (ca != cb),
            ))
        dp = ndp
    return dp[-1]

def similarity(a: str, b: str) -> float:
    """Calculate similarity score (0.0 to 1.0)"""
    a, b = normalize(a), normalize(b)
    if not a or not b:
        return 0.0
    dist = edit_dist(a, b)
    return 1.0 - dist / max(len(a), len(b))

def find_all_dish_matches(text: str, min_word_sim: float = 0.85, min_coverage: float = 0.5):
    """Find menu items matching text"""
    text = text.lower()
    text_words = [normalize(w) for w in text.split()]
    matches = []
    
    for cat, item in all_menu_items():
        name_words = [normalize(w) for w in item["name"].split()]
        if not name_words:
            continue

        matched_name_words = set()
        max_sim = 0.0

        for dw in name_words:
            if not dw:
                continue
            for tw in text_words:
                if not tw:
                    continue
                sim = similarity(tw, dw)
                if sim > max_sim:
                    max_sim = sim
                if sim >= min_word_sim:
                    matched_name_words.add(dw)

        if not matched_name_words:
            continue

        coverage = len(matched_name_words) / len(name_words)

        if coverage < min_coverage:
            continue
        
        if len(item["name"].split()) > 2 and coverage < 0.7:
            continue

        score = coverage + 0.1 * max_sim
        matches.append((cat, item, score))
    
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches

def extract_quantity(text: str, default: int = 1) -> int:
    """Extract quantity from text"""
    word_to_num = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
    }
    
    tokens = text.lower().split()
    
    for token in tokens:
        if token in word_to_num:
            return word_to_num[token]
    
    nums = []
    for t in tokens:
        t_clean = "".join(ch for ch in t if ch.isdigit())
        if t_clean.isdigit():
            nums.append(int(t_clean))
    return max(nums) if nums else default

def menu_suggestion_string(limit_per_category: Optional[int] = None) -> str:
    """Build menu suggestion string"""
    parts = []
    for c in REST_DATA.get("menu", []):
        items_list = c.get("items", [])
        if limit_per_category is not None:
            items_list = items_list[:limit_per_category]
        names = ", ".join(i["name"] for i in items_list)
        if names:
            parts.append(f"{c['name']}: {names}")
    return " | ".join(parts) if parts else "our current menu items."

def apply_phonetic_corrections(text: str) -> str:
    """Fix common speech-to-text errors for Indian food terms"""
    corrections = {
        "button hand": "butter naan",
        "button nan": "butter naan",
        "better nan": "butter naan",
        "butter nan": "butter naan",
        "plane nan": "plain naan",
        "plain nan": "plain naan",
        "garlic nan": "garlic naan",
        "gulab jamun": "gulab jamun",
        "golub jamun": "gulab jamun",
        "gulab jaman": "gulab jamun",
        "rasgulla": "rasgulla",
        "ras gulla": "rasgulla",
        "butter chicken": "butter chicken",
        "better chicken": "butter chicken",
        "panel tikka": "paneer tikka",
        "paneer tika": "paneer tikka",
        "biryani": "biryani",
        "biriyani": "biryani",
        "dal makhani": "dal makhani",
        "dhal makhani": "dal makhani",
        "prize": "price",
        "prise": "price",
    }
    
    text_lower = text.lower()
    for wrong, correct in corrections.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'
        text_lower = re.sub(pattern, correct, text_lower, flags=re.IGNORECASE)
    
    return text_lower

# ========== IMPROVED ORDER MANAGER ==========
class ImprovedOrderManager:
    """Enhanced order manager with all features"""
    
    def __init__(self):
        self.lines = []
        self.customer = {}
        self.pending_confirmation = None
    
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
            return
        if qty is None or qty >= line["qty"]:
            self.lines = [l for l in self.lines if l is not line]
        else:
            line["qty"] -= qty
    
    def update_quantity(self, item_name: str, new_qty: int):
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

# ========== RESPONSE TEMPLATES ==========
class ResponseTemplates:
    """Deterministic response templates"""
    
    @staticmethod
    def greeting() -> str:
        return "Hello! How can I help you today?"
    
    @staticmethod
    def audibility() -> str:
        return "Yes, I can hear you. How can I help?"
    
    @staticmethod
    def thanks() -> str:
        return "You're welcome."
    
    @staticmethod
    def price_single(item_name: str, price: float) -> str:
        return f"{item_name} price {price:.0f} rupees"
    
    @staticmethod
    def price_multi(items: List[Tuple[str, float]]) -> str:
        parts = [f"{name} price {price:.0f} rupees" for name, price in items]
        return " | ".join(parts)
    
    @staticmethod
    def confirmation_required(item_name: str, qty: int, price: float) -> str:
        total = qty * price
        return f"Do you want to add {qty} {item_name} ({total:.0f} rupees) to your order?"
    
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

# ========== RESTAURANT JSON RAG SYSTEM WITH INTENT ROUTER ==========
class RestaurantRAGSystem:
    """Restaurant JSON-based RAG System with Intent Router"""
    
    def __init__(self, order_manager: ImprovedOrderManager):
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
    
    def process_with_rag(self, text: str) -> Tuple[Optional[str], bool]:
        """
        Process query using restaurant JSON RAG with intent routing
        Returns: (response, should_use_llm)
        """
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
        if intent_result.intent in [Intent.ORDER_ADD, Intent.ORDER_CONFIRM]:
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
        
        # 4. ORDER - CONFIRM (pending confirmation)
        if intent_result.intent == Intent.ORDER_CONFIRM:
            if self.order.pending_confirmation:
                confirmed = intent_result.slots.get("confirmed", True)
                
                if confirmed:
                    item_name = self.order.pending_confirmation["item"]
                    qty = self.order.pending_confirmation["qty"]
                    price = self.order.pending_confirmation["price"]
                    
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
                return "What would you like to confirm?", False
        
        # 5. ORDER - SUMMARY
        if intent_result.intent == Intent.ORDER_SUMMARY:
            return self.order.describe_order(), False
        
        # 6. ORDER - CLEAR
        if intent_result.intent == Intent.ORDER_CLEAR:
            self.order.clear()
            return self.templates.order_cleared(), False
        
        # 7. ORDER - REMOVE
        if intent_result.intent == Intent.ORDER_REMOVE:
            matches = find_all_dish_matches(text_corrected)
            if matches:
                qty = extract_quantity(text_corrected, default=None)
                removed = []
                for _, item, _ in matches:
                    self.order.remove_item(item["name"], qty)
                    removed.append(item["name"])
                
                if self.order.is_empty():
                    return f"I removed {', '.join(removed)}. Your order is now empty.", False
                else:
                    return f"I removed {', '.join(removed)}. {self.order.describe_order()}", False
            return "I couldn't find that item in your order.", False
        
        # 8. INFO - PRICE (NO ORDER MUTATION)
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
        
        # 9. INFO - MENU
        if intent_result.intent == Intent.INFO_MENU:
            # Check for category-specific
            for cat in REST_DATA["menu"]:
                cat_name = cat["name"].lower()
                if cat_name in text_corrected:
                    names = ", ".join(i["name"] for i in cat["items"])
                    return f"{cat['name']}: {names}", False
            
            suggestions = menu_suggestion_string(limit_per_category=2)
            return "Here's our menu: " + suggestions, False
        
        # 10. INFO - DESCRIPTION
        if intent_result.intent == Intent.INFO_DESCRIPTION:
            matches = find_all_dish_matches(text_corrected)
            if matches:
                _, item, score = matches[0]
                if score >= 0.7:
                    desc = item.get("description", "No description available")
                    return f"{item['name']}: {desc}. Price: {item['price']} rupees.", False
            
            return "I don't have information about that dish. Could you ask about something from our menu?", False
        
        # 11. ORDER - ADD (REQUIRES CONFIRMATION)
        if intent_result.intent == Intent.ORDER_ADD:
            qty = intent_result.slots.get("quantity", 1)
            
            matches = find_all_dish_matches(text_corrected)
            if not matches:
                return self.templates.item_not_found(), False
            
            _, item, score = matches[0]
            
            if score < 0.7:
                return self.templates.item_not_found(), False
            
            # Check availability
            available, avail_msg = self.check_item_availability(item["name"])
            if not available:
                return avail_msg, False
            
            # Set pending confirmation
            self.order.pending_confirmation = {
                "item": item["name"],
                "qty": qty,
                "price": item["price"]
            }
            
            return self.templates.confirmation_required(item["name"], qty, item["price"]), False
        
        # 12. RESTAURANT INFO
        if intent_result.intent == Intent.RESTAURANT_INFO:
            if "name" in text_corrected or "restaurant" in text_corrected:
                return f"Our restaurant name is {rest.get('name', 'Infocall Dine')}.", False
            if any(k in text_corrected for k in ["address", "location"]):
                return f"We are located at {rest.get('address', 'MG Road, Mumbai')}.", False
            if any(k in text_corrected for k in ["phone", "contact", "number"]):
                return f"You can reach us at {rest.get('phone', '+91 98765 43210')}.", False
        
        # 13. UNKNOWN - Let LLM handle but with strict constraints
        if intent_result.intent == Intent.UNKNOWN:
            if intent_result.confidence < 0.5:
                # Very low confidence, use LLM for general conversation
                return None, True
        
        # Default fallback
        return self.templates.clarification_needed(), False

# ========== RESTAURANT LLM (WebSocket Version) ==========
class RestaurantLLM:
    """Restaurant LLM with proper WebSocket connection management"""
    
    def __init__(self, server_url: str, token: str, voice_clone_path: str = None):
        self.server_url = server_url
        self.token = token
        self.voice_clone_path = voice_clone_path
        self.timeout = 30
        self.next_prompt_id = 4000
        self.connection_pool_size = 1
        self.retry_attempts = 3
        self.retry_delay = 1.0
        
    async def _create_websocket_connection(self):
        """Create a new WebSocket connection with proper settings"""
        try:
            ws = await websockets.connect(
                self.server_url,
                ping_interval=10,
                ping_timeout=20,
                close_timeout=self.timeout,
                max_size=10 * 1024 * 1024,  # 10MB max message size
                compression=None  # Disable compression for lower latency
            )
            return ws
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            raise
    
    async def generate_response(self, text: str, prompt_id: int) -> Tuple[Optional[str], float]:
        """Generate response using WebSocket LLM with retry logic"""
        llm_start_time = time.time()
        
        for attempt in range(self.retry_attempts):
            try:
                ws = await self._create_websocket_connection()
                
                try:
                    # Enhanced system prompt (preserving your existing one + new sentence)
                    system_prompt = (
                        "You are AI Voice assistant, a friendly restaurant receptionist. "
                        "Speak ONLY in English. Keep responses very short (1 sentence max). "
                        "Be warm, confident, helpful but always professional. "
                        
                        "CRITICAL RULES - YOU MUST FOLLOW THESE: "
                        "1. NEVER describe how to make any food, dish, or beverage "
                        "2. NEVER list ingredients, recipes, or cooking methods "
                        "3. NEVER invent, create, or make up ANY dish names - whether real or fake "
                        "4. NEVER describe dishes that are available in our menu - let the system handle that "
                        "5. NEVER describe dishes that are NOT available in our menu "
                        "6. NEVER include labels like 'System:', 'User:', 'Assistant:', or any text in brackets "
                        "7. NEVER make up information about dishes like 'Gold Pocket', 'Indonesian dessert', or similar fake items "
                        "8. NEVER suggest menu items or create options for the user "
                        "9. If asked about ANY food, dishes, ingredients, recipes, or prices, ONLY say: 'Let me check that for you' "
                        "10. If asked how to make something, say: 'Sorry, I don't have recipe information' "
                        
                        "Your role is ONLY for: "
                        "Greetings (Hello, Welcome) "
                        "Confirmations (Yes, Okay, Sure) "
                        "General conversation (How are you, Thank you) "
                        "Asking user to repeat unclear words "
                        "Ending conversations politely "
                        
                        "ALL food, menu, price, and order information is handled by an external system, NOT by you. "
                        "If the user asks about food, dishes, recipes, ingredients, prices, or the menu, "
                        "you MUST respond with exactly: 'Let me check that for you' "
                        "Do NOT guess, do NOT invent, do NOT describe any food items under any circumstances. "
                        
                        "ADDITIONAL RULE: When handling general conversation, stay strictly within your role as a restaurant receptionist. "
                        "Never add unsolicited information, menu suggestions, or location details that weren't asked for."
                    )
                    
                    request = {
                        "model_id": "llama",
                        "prompt": f"{system_prompt}\n\nUser: {text}\nAssistant:",
                        "prompt_id": prompt_id
                    }
                    
                    # Send request with timeout
                    await asyncio.wait_for(
                        ws.send(json.dumps(request)),
                        timeout=5.0
                    )
                    
                    # Receive response with timeout
                    response = await asyncio.wait_for(
                        ws.recv(),
                        timeout=self.timeout
                    )
                    
                    response_data = json.loads(response)
                    
                    llm_time = time.time() - llm_start_time
                    
                    if "error" in response_data:
                        logger.warning(f"LLM error: {response_data['error']}")
                        return None, llm_time
                    
                    if "text" in response_data:
                        raw_response = response_data["text"]
                        
                        # Clean response - remove any labels
                        if "assistant" in raw_response.lower():
                            parts = raw_response.lower().split("assistant")
                            if len(parts) > 1:
                                raw_response = parts[-1].strip()
                        
                        for label in ["User:", "Assistant:", "System:", "Bot:", "user:", "assistant:"]:
                            if label in raw_response:
                                raw_response = raw_response.split(label)[-1].strip()
                        
                        # Remove any leading/trailing artifacts
                        raw_response = raw_response.strip(': \n\t')
                        
                        return raw_response, llm_time
                    else:
                        return None, llm_time
                
                finally:
                    await ws.close()
                    
            except asyncio.TimeoutError:
                logger.warning(f"LLM timeout on attempt {attempt + 1}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return None, time.time() - llm_start_time
                
            except Exception as e:
                logger.error(f"LLM error on attempt {attempt + 1}: {e}")
                if attempt < self.retry_attempts - 1:
                    await asyncio.sleep(self.retry_delay)
                    continue
                return None, time.time() - llm_start_time
        
        return None, time.time() - llm_start_time

# ========== COMPLETE VOICE ASSISTANT ==========
class RestaurantVoiceAssistant:
    """Complete Restaurant Voice Assistant with Intent Router"""
    
    def __init__(self, server_url: str, token: str, voice_clone_path: str = None):
        self.server_url = server_url
        self.token = token
        self.voice_clone_path = voice_clone_path
        
        # Voice cloning cache
        self.voice_reference_b64 = None
        self.voice_reference_loaded = False
        self.voice_reference_trimmed = False  # Track if voice was trimmed

        # Initialize components
        self.order_manager = ImprovedOrderManager()
        self.rag_system = RestaurantRAGSystem(self.order_manager)
        self.llm = RestaurantLLM(server_url, token, voice_clone_path)
        
        # Recording setup
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.samplerate = 16000
        
        # Session tracking
        self.session_count = 0
        self.next_prompt_id = 1000
        
        # Conversation context
        self.first_interaction = True
        
        # WebSocket connection pool
        self.ws_connections = {}

        # Preload voice reference if path provided
        if self.voice_clone_path:
            self._preload_voice_reference()
    
    def _load_voice_reference(self) -> Optional[str]:
        """Load and encode voice reference file"""
        if not self.voice_clone_path:
            return None
        
        try:
            voice_path = Path(self.voice_clone_path)
            if not voice_path.exists():
                logger.warning(f"Voice reference file not found: {self.voice_clone_path}")
                return None
            
            # Process the audio file (trim if needed)
            audio_bytes, trimmed = process_audio_file_for_voice_reference(self.voice_clone_path)
            
            if audio_bytes is None:
                print("  ✗ Failed to process voice reference")
                return None
            
            # Update tracking
            self.voice_reference_trimmed = trimmed
            
            # Encode to base64
            voice_b64 = base64.b64encode(audio_bytes).decode('ascii')
            return voice_b64
            
        except Exception as e:
            logger.error(f"Error loading voice reference: {e}")
            return None
        
    def get_next_prompt_id(self) -> int:
        """Get next prompt ID for session"""
        current_id = self.next_prompt_id
        self.next_prompt_id += 1
        return current_id
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Audio input callback"""
        if self.is_recording:
            self.audio_queue.put(indata.copy().tobytes())
    
    async def record_until_silence(self) -> Optional[bytes]:
        """Record audio until 1 second of silence"""
        if not AUDIO_CAPTURE_AVAILABLE:
            raise ImportError("Install: pip install sounddevice soundfile numpy")
        
        self.is_recording = True
        audio_chunks = []
        silence_start = None
        has_spoken = False
        
        with sd.InputStream(samplerate=self.samplerate, channels=1, 
                          callback=self._audio_callback, dtype='float32'):
            
            start_time = time.time()
            
            while self.is_recording:
                try:
                    chunk = self.audio_queue.get(timeout=0.1)
                    audio_array = np.frombuffer(chunk, dtype=np.float32)
                    volume = np.mean(np.abs(audio_array))
                    
                    if volume > 0.02:
                        has_spoken = True
                    
                    if volume < 0.02:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > 1.0:
                            self.is_recording = False
                            break
                    else:
                        silence_start = None
                    
                    audio_chunks.append(chunk)
                    
                except queue.Empty:
                    if time.time() - start_time > 30:
                        self.is_recording = False
                        break
        
        if not audio_chunks or not has_spoken:
            return None
        
        audio_bytes = b''.join(audio_chunks)
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        
        wav_io = io.BytesIO()
        sf.write(wav_io, audio_array, self.samplerate, format='WAV')
        
        return wav_io.getvalue()
    
    def _preload_voice_reference(self):
        """Preload and cache voice reference file"""
        try:
            voice_path = Path(self.voice_clone_path)
            if not voice_path.exists():
                print(f"⚠️ Voice reference file not found: {self.voice_clone_path}")
                self.voice_reference_loaded = False
                return
            
            print(f"📁 Loading voice reference: {self.voice_clone_path}")
            
            # Process the audio file (trim if needed)
            audio_bytes, trimmed = process_audio_file_for_voice_reference(self.voice_clone_path)
            
            if audio_bytes is None:
                print(f"❌ Failed to load voice reference")
                self.voice_reference_loaded = False
                return
            
            # Update tracking
            self.voice_reference_trimmed = trimmed
            
            # Encode to base64 and cache
            self.voice_reference_b64 = base64.b64encode(audio_bytes).decode('ascii')
            self.voice_reference_loaded = True
            
            # Log size information
            b64_size_kb = len(self.voice_reference_b64) / 1024
            audio_size_kb = len(audio_bytes) / 1024
            status = "(trimmed to 5s)" if trimmed else "(original)"
            print(f"✅ Voice reference loaded {status} ({audio_size_kb:.1f}KB audio, "
                  f"{b64_size_kb:.1f}KB base64)")
            
        except Exception as e:
            print(f"❌ Error loading voice reference: {e}")
            self.voice_reference_loaded = False

    async def _websocket_request(self, model_id: str, prompt: str, prompt_id: int, 
                                 is_audio: bool = False) -> Tuple[Optional[Any], float]:
        """Generic WebSocket request handler with connection management"""
        start_time = time.time()
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                ws = await websockets.connect(
                    self.server_url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=30,
                    max_size=10 * 1024 * 1024
                )
                
                try:
                    # Build request according to server-side JSON format
                    request = {
                        "model_id": model_id,
                        "prompt": prompt,
                        "prompt_id": prompt_id
                    }

                    # Add voice cloning parameters for TTS model
                    if model_id == "xtts" and self.voice_reference_loaded:
                        # Use cached voice reference
                        request["voice_cloning"] = True
                        request["voice_reference"] = self.voice_reference_b64
                        voice_status = "trimmed to 5s" if self.voice_reference_trimmed else "original"
                        print(f"🎤 Voice cloning enabled ({voice_status})")
                    elif model_id == "xtts" and self.voice_clone_path and not self.voice_reference_loaded:
                        # Try to load voice reference on the fly if not cached
                        print(f"🔄 Loading voice reference on demand...")
                        voice_b64 = self._load_voice_reference()
                        if voice_b64:
                            self.voice_reference_b64 = voice_b64
                            self.voice_reference_loaded = True
                            request["voice_cloning"] = True
                            request["voice_reference"] = voice_b64
                            voice_status = "trimmed to 5s" if self.voice_reference_trimmed else "original"
                            print(f"✅ Voice reference loaded on demand ({voice_status})")
                        else:
                            print(f"⚠️ Voice reference not available, using default voice")

                    await asyncio.wait_for(ws.send(json.dumps(request)), timeout=5.0)
                    response = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    response_data = json.loads(response)
                    
                    elapsed_time = time.time() - start_time
                    
                    if "error" in response_data:
                        logger.warning(f"{model_id} error: {response_data['error']}")
                        return None, elapsed_time
                    
                    return response_data, elapsed_time
                
                finally:
                    await ws.close()
                    
            except websockets.exceptions.ConnectionClosed as e:
                if e.code == 1009:  # Message too big
                    print(f"❌ {model_id}: Message too big (code 1009). Reducing voice reference size...")
                    # Try without voice cloning on next attempt
                    if model_id == "xtts" and self.voice_reference_loaded:
                        self.voice_reference_loaded = False
                        print("🔄 Disabling voice cloning for this session")
                elif attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return None, time.time() - start_time
                    
            except asyncio.TimeoutError:
                logger.warning(f"{model_id} timeout on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return None, time.time() - start_time
                
            except Exception as e:
                logger.error(f"{model_id} error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return None, time.time() - start_time
        
        return None, time.time() - start_time
    
    async def stt_transcribe(self, audio_bytes: bytes, prompt_id: int) -> Tuple[Optional[str], float]:
        """STT: Convert speech to text"""
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        response_data, stt_time = await self._websocket_request("whisper", audio_b64, prompt_id, is_audio=True)
        
        if response_data and "text" in response_data:
            transcription = response_data["text"]
            print(f"📝 You said: {transcription}")
            return transcription, stt_time
        
        return None, stt_time
    
    async def tts_speak(self, text: str, prompt_id: int) -> Tuple[Optional[bytes], float]:
        """TTS: Convert text to speech"""
        response_data, tts_time = await self._websocket_request("xtts", text, prompt_id)
        
        if response_data and "audio_b64" in response_data:
            audio_bytes = base64.b64decode(response_data["audio_b64"])
            return audio_bytes, tts_time
        
        return None, tts_time
    
    async def play_audio(self, audio_bytes: bytes):
        """Play audio without saving to file"""
        try:
            data, samplerate = sf.read(io.BytesIO(audio_bytes))
            sd.play(data, samplerate)
            sd.wait()
            return True
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            return False
    
    def display_latency_summary(self, prompt_id: int, stt_time: float, rag_time: float, 
                              llm_time: float, tts_time: float, total_time: float, 
                              intent: str, used_llm: bool):
        """Display enhanced latency summary with intent info"""
        brain_time = rag_time + llm_time
        
        summary = f"[Latency Summary Prompt ID: {prompt_id}]"
        print(summary)
        print(f"  Intent: {intent} | Used LLM: {used_llm}")
        print(f"  STT: {stt_time:.2f}s | Brain: {brain_time:.2f}s (JSON={rag_time:.2f}s, LLM={llm_time:.2f}s) | TTS: {tts_time:.2f}s")
        print(f"  TOTAL: {total_time:.2f}s\n")
    
    async def single_conversation_session(self):
        """Complete session: Listen → Intent Route → RAG/LLM → Speak"""
        self.session_count += 1
        prompt_id = self.get_next_prompt_id()
        
        # Step 1: Record audio
        print("\n🎤 Listening... (Speak now)")
        audio = await self.record_until_silence()
        
        if not audio:
            print("No speech detected")
            return
        
        # Step 2: STT (Transcribe)
        transcription, stt_time = await self.stt_transcribe(audio, prompt_id)
        
        if not transcription:
            return
        
        # Step 3: RAG Processing with Intent Routing
        rag_start_time = time.time()
        reply, should_use_llm = self.rag_system.process_with_rag(transcription)
        rag_time = time.time() - rag_start_time
        
        llm_time = 0.0
        used_llm = False
        detected_intent = "RAG_HANDLED"
        
        # Get detected intent from conversation history
        if self.rag_system.conversation_history:
            last_entry = self.rag_system.conversation_history[-1]
            detected_intent = last_entry.get("intent", "unknown")
        
        # Step 4: LLM Processing (only if RAG didn't handle it)
        if reply is None and should_use_llm:
            llm_response, llm_time = await self.llm.generate_response(transcription, prompt_id)
            if llm_response:
                reply = llm_response
                used_llm = True
                detected_intent = "LLM_FALLBACK"
            else:
                reply = "How can I help you today?"
        
        # Add restaurant greeting on first interaction
        if self.first_interaction and reply:
            rest = REST_DATA.get("restaurant", {})
            name = rest.get("name", "our restaurant")
            addr = rest.get("address", "our location")
            # Don't add greeting if it's already a greeting response
            if not reply.startswith("Hello"):
                reply = f"Welcome to {name}! We are located at {addr}. {reply}"
            self.first_interaction = False
        
        # Print assistant response
        if reply:
            print(f"🤖 Assistant: {reply}")
        
        # Step 5: TTS (Speak)
        audio_response, tts_time = await self.tts_speak(reply, prompt_id)
        
        if audio_response:
            await self.play_audio(audio_response)
        
        # Calculate total time
        total_time = stt_time + rag_time + llm_time + tts_time
        
        # Display enhanced latency summary
        self.display_latency_summary(prompt_id, stt_time, rag_time, llm_time, tts_time, 
                                    total_time, detected_intent, used_llm)
    
    async def run_voice_assistant(self):
        """Main voice assistant loop"""
        print("\n" + "="*60)
        print("🍽️  RESTAURANT VOICE ASSISTANT v2.0 (Intent Router Enabled)")
        print("="*60)
        print("🛑 Press Ctrl+C to exit")
        print("="*60)
        
        try:
            while True:
                await self.single_conversation_session()
                
        except KeyboardInterrupt:
            print("\n👋 Restaurant assistant stopped")
        except Exception as e:
            print(f"\n❌ Assistant error: {e}")
            logger.exception("Fatal error in voice assistant")

async def main():
    """Main function"""
    
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        print("❌ SERVER_URL environment variable is required")
        print("Create a .env file with:")
        print("SERVER_URL=ws://localhost:8765")
        print("TOKEN=your-secret-token")
        return
    
    token = os.getenv("TOKEN")
    if not token:
        print("❌ TOKEN environment variable is required")
        return
    
    # Voice cloning path (optional)
    voice_clone_path = os.getenv("VOICE_CLONE_PATH")
    
    # Check if voice file exists
    if voice_clone_path:
        if Path(voice_clone_path).exists():
            print(f"📁 Found voice reference file: {voice_clone_path}")
            print("ℹ️  Large files (>500KB) will be automatically trimmed to 5 seconds")
        else:
            print(f"⚠️  Voice reference file not found: {voice_clone_path}")
            voice_clone_path = None
    else:
        print("ℹ️  Voice cloning not enabled (no path provided)")

    # Create and run assistant
    assistant = RestaurantVoiceAssistant(server_url, token, voice_clone_path)
    await assistant.run_voice_assistant()


if __name__ == "__main__":
    asyncio.run(main())