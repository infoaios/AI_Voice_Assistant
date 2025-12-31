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
import uuid

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
            '-filter:a', 'atempo=1.5',  # Speed up by 1.5x
            '-ar', '16000',  # Sample rate 16000 Hz
            '-ac', '1',  # Mono channel
            '-acodec', 'pcm_s16le',  # Audio codec
            '-map_metadata', '-1',  # Remove metadata
            output_path
        ]
        
        print(f"  ↳ Trimming voice reference to 5 seconds with 1.5x speed......")
        
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
                        {"name": "Spring Roll", "price": 180, "description": "Vegetable spring rolls"},
                        {"name": "Gulab Jamun", "price": 80, "description": "Sweet Indian dessert"}
                    ]
                },
                {
                    "name": "Main Course",
                    "items": [
                        {"name": "Butter Chicken", "price": 350, "description": "Chicken in butter sauce"},
                        {"name": "Dal Makhani", "price": 220, "description": "Black lentils"},
                        {"name": "Garlic Naan", "price": 60, "description": "Garlic flavored bread"}
                    ]
                },
                {
                    "name": "Beverages",
                    "items": [
                        {"name": "Cold Coffee", "price": 150, "description": "Iced coffee with cream"},
                        {"name": "Masala Tea", "price": 50, "description": "Spiced Indian tea"}
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
    """Extract quantity from text - IMPROVED VERSION"""
    word_to_num = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'another': 1, 'additional': 1, 'extra': 1, 'more': 1,
        'too': 2, 'to': 2  # Handle misheard "too" as "two"
    }
    
    text_lower = text.lower()
    
    # First, check for specific quantity patterns
    patterns = [
        r'\b(\d+)\s+cold\s+coffee\b',  # "2 cold coffee"
        r'\b(\d+)\s+garlic\s+naan\b',   # "3 garlic naan"
        r'\b(\d+)\s+paneer\s+tikka\b',  # "2 paneer tikka"
        r'\b(\d+)\s+butter\s+chicken\b', # "1 butter chicken"
        r'\b(\d+)\s+spring\s+roll\b',   # "4 spring roll"
        r'\b(\d+)\s+dal\s+makhani\b',   # "2 dal makhani"
        r'\b(\d+)\s+masala\s+tea\b',    # "3 masala tea"
        r'\b(\d+)\s+gulab\s+jamun\b',   # "2 gulab jamun"
        r'\banother\s+(\d+)\b',         # "another 2"
        r'\bmore\s+(\d+)\b',            # "more 3"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return int(match.group(1))
    
    # Look for word numbers
    for word, num in word_to_num.items():
        if word in text_lower:
            # Check if it's part of a phrase like "two cold coffee"
            word_pattern = fr'\b{word}\s+([a-z\s]+)\b'
            if re.search(word_pattern, text_lower):
                return num
    
    # Look for standalone numbers
    tokens = text_lower.split()
    
    # Check for patterns like "cold coffee 2, 3"
    if any(item in text_lower for item in ["cold coffee", "garlic naan", "paneer tikka", "gulab jamun"]):
        # Extract all numbers after the item
        numbers = re.findall(r'\b\d+\b', text_lower)
        if numbers:
            # Take the last number mentioned (most likely the quantity)
            return int(numbers[-1])
    
    # Check for patterns like "coffee 2" or "naan 3"
    for i, token in enumerate(tokens):
        # Clean token of punctuation
        clean_token = re.sub(r'[^\w]', '', token)
        if clean_token.isdigit():
            # Check if previous token is a dish indicator
            if i > 0:
                prev_token = tokens[i-1].lower()
                dish_indicators = ['coffee', 'naan', 'tikka', 'chicken', 'roll', 'dal', 'tea', 'paneer', 'gulab', 'jamun', 'butter', 'masala']
                if any(indicator in prev_token for indicator in dish_indicators):
                    return int(clean_token)
            return int(clean_token)
    
    # Check for quantity in the beginning
    first_token = tokens[0] if tokens else ""
    clean_first = re.sub(r'[^\w]', '', first_token)
    if clean_first.isdigit():
        return int(clean_first)
    
    # Check for "another" or "more" patterns without numbers
    if any(word in text_lower for word in ['another', 'more', 'additional', 'extra']):
        # Look for number after these words
        for i, token in enumerate(tokens):
            if token in ['another', 'more', 'additional', 'extra'] and i + 1 < len(tokens):
                next_token = tokens[i+1]
                clean_next = re.sub(r'[^\w]', '', next_token)
                if clean_next.isdigit():
                    return int(clean_next)
        return 1  # Default to 1 for "another"
    
    # Handle "too" as "two" (common speech recognition error)
    if "too" in text_lower:
        # Check if "too" is followed by a dish name
        too_index = text_lower.find("too")
        if too_index + 4 < len(text_lower):
            following_text = text_lower[too_index + 4:]
            if any(item in following_text for item in ["coffee", "naan", "tikka", "chicken"]):
                return 2
    
    return default

# def menu_suggestion_string(limit_per_category: Optional[int] = None) -> str:
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

def menu_suggestion_string(show_items: bool = False, limit_per_category: Optional[int] = None) -> str:
    """Build menu suggestion string - optionally with or without items"""
    parts = []
    for c in REST_DATA.get("menu", []):
        if show_items:
            items_list = c.get("items", [])
            if limit_per_category is not None:
                items_list = items_list[:limit_per_category]
            names = ", ".join(i["name"] for i in items_list)
            if names:
                parts.append(f"{c['name']}: {names}")
        else:
            # Just show category names
            parts.append(f"{c['name']}")
    
    if show_items:
        return " | ".join(parts) if parts else "our current menu items."
    else:
        return ", ".join(parts) if parts else "our menu categories."

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
        "cold coffee": "cold coffee",
        "cool coffee": "cold coffee",
        "cole coffee": "cold coffee",
        "cold coffe": "cold coffee",
        "pull coffee": "cold coffee",
        "cold coffees": "cold coffee",
        "too cold": "two cold",
        "to cold": "two cold",
        "2-pull": "two cold",
    }
    
    text_lower = text.lower()
    for wrong, correct in corrections.items():
        pattern = r'\b' + re.escape(wrong) + r'\b'
        text_lower = re.sub(pattern, correct, text_lower, flags=re.IGNORECASE)
    
    return text_lower

def detect_multiple_dishes(text: str) -> List[str]:
    """
    Detect if user mentioned multiple dishes using common separators.
    Returns list of dish phrases.
    """
    text_low = text.lower()
    
    # Common separators for multiple items
    separators = [
        ' and ', 
        ',', 
        ' with ', 
        ' plus ', 
        ' along with ',
        ' also '
    ]
    
    # Try to split by separators
    dishes = []
    for sep in separators:
        if sep in text_low:
            parts = text_low.split(sep)
            dishes = [p.strip() for p in parts if p.strip()]
            break
    
    # If no separator found but has multiple quantity words
    if not dishes and ('one' in text_low or 'two' in text_low or 'three' in text_low):
        # Try to split by quantity words
        quantity_pattern = r'\b(one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+([^,]+?)(?=\s+(?:one|two|three|four|five|six|seven|eight|nine|ten|\d+)\s+|\s*$)'
        matches = re.findall(quantity_pattern, text_low)
        if matches:
            dishes = [match[1].strip() for match in matches]
    
    return dishes if dishes else [text_low]

# ========== PERSISTENT STT CLIENT ==========
class STTPersistentClient:
    """Persistent WebSocket client for STT (Whisper) with auto-reconnect"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self.ws = None
        self.lock = asyncio.Lock()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
    
    async def connect(self):
        """Establish WebSocket connection or reconnect if needed"""
        async with self.lock:
            if self.connected and self.ws:
                try:
                    # Check if connection is still alive
                    if self.ws.state == websockets.protocol.State.OPEN:
                        return True
                except:
                    # Connection is dead
                    self.connected = False
                    self.ws = None
            
            try:
                print(f"🔗 Connecting to STT WebSocket...")
                self.ws = await websockets.connect(
                    self.server_url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=30,
                    max_size=50 * 1024 * 1024,  # 50MB max size for audio
                    compression=None  # Lower latency
                )
                
                self.connected = True
                self.reconnect_attempts = 0
                print(f"✅ STT WebSocket connected")
                return True
                
            except Exception as e:
                self.connected = False
                self.ws = None
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts <= self.max_reconnect_attempts:
                    print(f"⚠️ STT WebSocket connection failed (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}): {e}")
                    await asyncio.sleep(self.reconnect_delay * self.reconnect_attempts)
                    return await self.connect()
                else:
                    print(f"❌ Failed to connect to STT WebSocket after {self.max_reconnect_attempts} attempts")
                    return False
    
    async def ensure_connection(self):
        """Ensure we have a valid connection"""
        if not self.connected or not self.ws:
            return await self.connect()
        
        # Check connection state
        try:
            state = self.ws.state
            if state != websockets.protocol.State.OPEN:
                print(f"⚠️ STT WebSocket state is {state}, reconnecting...")
                self.connected = False
                self.ws = None
                return await self.connect()
            return True
        except Exception as e:
            print(f"⚠️ STT WebSocket check failed: {e}, reconnecting...")
            self.connected = False
            self.ws = None
            return await self.connect()
    
    # async def transcribe(self, audio_b64: str, prompt_id: int) -> Tuple[Optional[str], float]:
    #     """Transcribe audio using persistent WebSocket"""
    #     start_time = time.time()
        
    #     # Try with retries
    #     for attempt in range(3):
    #         try:
    #             # Ensure connection
    #             if not await self.ensure_connection():
    #                 print(f"❌ STT connection failed, cannot send request")
    #                 return None, time.time() - start_time
                
    #             # Build request
    #             request = {
    #                 "model_id": "whisper",
    #                 "prompt": audio_b64,
    #                 "prompt_id": prompt_id
    #             }
                
    #             # Send request
    #             await asyncio.wait_for(
    #                 self.ws.send(json.dumps(request)),
    #                 timeout=5.0
    #             )
                
    #             # Receive response
    #             response = await asyncio.wait_for(
    #                 self.ws.recv(),
    #                 timeout=15.0  # Shorter timeout for STT
    #             )
                
    #             response_data = json.loads(response)
    #             elapsed_time = time.time() - start_time
                
    #             if "error" in response_data:
    #                 print(f"⚠️ STT error: {response_data['error']}")
    #                 if attempt < 2:
    #                     await asyncio.sleep(1.0)
    #                     continue
    #                 return None, elapsed_time
                
    #             if "text" in response_data:
    #                 transcription = response_data["text"]
    #                 # PRINT THE TRANSCRIPTION HERE - THIS IS THE FIX
    #                 print(f"📝 You said: {transcription}")
    #                 return transcription, elapsed_time
                
    #             return None, elapsed_time
                
    #         except websockets.exceptions.ConnectionClosed as e:
    #             print(f"⚠️ STT connection closed: {e}, reconnecting...")
    #             self.connected = False
    #             self.ws = None
    #             if attempt < 2:
    #                 await asyncio.sleep(1.0)
    #                 continue
    #             return None, time.time() - start_time
                
    #         except asyncio.TimeoutError:
    #             print(f"⚠️ STT timeout on attempt {attempt + 1}")
    #             if attempt < 2:
    #                 await asyncio.sleep(1.0)
    #                 continue
    #             return None, time.time() - start_time
                
    #         except Exception as e:
    #             print(f"⚠️ STT error on attempt {attempt + 1}: {e}")
    #             if attempt < 2:
    #                 await asyncio.sleep(1.0)
    #                 continue
    #             return None, time.time() - start_time
        
    #     return None, time.time() - start_time
    
    async def transcribe(self, audio_b64: str, prompt_id: int) -> Tuple[Optional[str], float]:
        """Transcribe audio using persistent WebSocket - ENGLISH ONLY"""
        start_time = time.time()
        
        # Try with retries
        for attempt in range(3):
            try:
                # Ensure connection
                if not await self.ensure_connection():
                    print(f"❌ STT connection failed, cannot send request")
                    return None, time.time() - start_time
                
                # Build request - ADD LANGUAGE PARAMETER
                request = {
                    "model_id": "whisper",
                    "prompt": audio_b64,
                    "prompt_id": prompt_id,
                    "language": "en"  # Force English language
                }
                
                # Send request
                await asyncio.wait_for(
                    self.ws.send(json.dumps(request)),
                    timeout=5.0
                )
                
                # Receive response
                response = await asyncio.wait_for(
                    self.ws.recv(),
                    timeout=15.0  # Shorter timeout for STT
                )
                
                response_data = json.loads(response)
                elapsed_time = time.time() - start_time
                
                if "error" in response_data:
                    print(f"⚠️ STT error: {response_data['error']}")
                    if attempt < 2:
                        await asyncio.sleep(1.0)
                        continue
                    return None, elapsed_time
                
                if "text" in response_data:
                    transcription = response_data["text"]
                    # PRINT THE TRANSCRIPTION HERE - THIS IS THE FIX
                    print(f"📝 You said: {transcription}")
                    
                    # CLEAN TRANSCRIPTION - Remove non-English text if any
                    # Keep only English alphabet, numbers, spaces, and basic punctuation
                    transcription = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', '', transcription)
                    transcription = transcription.strip()
                    
                    # If transcription is empty after cleaning, try one more time
                    if not transcription and attempt < 2:
                        print(f"⚠️ Transcription empty after cleaning, retrying...")
                        await asyncio.sleep(1.0)
                        continue
                        
                    return transcription, elapsed_time
                
                return None, elapsed_time
                
            except websockets.exceptions.ConnectionClosed as e:
                print(f"⚠️ STT connection closed: {e}, reconnecting...")
                self.connected = False
                self.ws = None
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
                
            except asyncio.TimeoutError:
                print(f"⚠️ STT timeout on attempt {attempt + 1}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
                
            except Exception as e:
                print(f"⚠️ STT error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
        
        return None, time.time() - start_time

    async def close(self):
        """Close the WebSocket connection"""
        async with self.lock:
            if self.ws:
                try:
                    await self.ws.close()
                    self.connected = False
                    print("🔌 STT WebSocket closed")
                except:
                    pass
                finally:
                    self.ws = None

# ========== PERSISTENT LLM CLIENT ==========
class LLMPersistentClient:
    """Persistent WebSocket client for LLM with auto-reconnect"""
    
    def __init__(self, server_url: str, token: str):
        self.server_url = server_url
        self.token = token
        self.ws = None
        self.lock = asyncio.Lock()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
    
    async def connect(self):
        """Establish WebSocket connection or reconnect if needed"""
        async with self.lock:
            if self.connected and self.ws:
                try:
                    if self.ws.state == websockets.protocol.State.OPEN:
                        return True
                except:
                    self.connected = False
                    self.ws = None
            
            try:
                print(f"🔗 Connecting to LLM WebSocket...")
                self.ws = await websockets.connect(
                    self.server_url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=30,
                    max_size=10 * 1024 * 1024,  # 10MB max size
                    compression=None
                )
                
                self.connected = True
                self.reconnect_attempts = 0
                print(f"✅ LLM WebSocket connected")
                return True
                
            except Exception as e:
                self.connected = False
                self.ws = None
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts <= self.max_reconnect_attempts:
                    print(f"⚠️ LLM WebSocket connection failed (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}): {e}")
                    await asyncio.sleep(self.reconnect_delay * self.reconnect_attempts)
                    return await self.connect()
                else:
                    print(f"❌ Failed to connect to LLM WebSocket after {self.max_reconnect_attempts} attempts")
                    return False
    
    async def ensure_connection(self):
        """Ensure we have a valid connection"""
        if not self.connected or not self.ws:
            return await self.connect()
        
        try:
            state = self.ws.state
            if state != websockets.protocol.State.OPEN:
                print(f"⚠️ LLM WebSocket state is {state}, reconnecting...")
                self.connected = False
                self.ws = None
                return await self.connect()
            return True
        except Exception as e:
            print(f"⚠️ LLM WebSocket check failed: {e}, reconnecting...")
            self.connected = False
            self.ws = None
            return await self.connect()
    
    async def generate(self, prompt: str, prompt_id: int) -> Tuple[Optional[str], float]:
        """Generate response using persistent WebSocket"""
        start_time = time.time()
        
        for attempt in range(3):
            try:
                if not await self.ensure_connection():
                    print(f"❌ LLM connection failed")
                    return None, time.time() - start_time
                
                request = {
                    "model_id": "llama",
                    "prompt": prompt,
                    "prompt_id": prompt_id
                }
                
                await asyncio.wait_for(
                    self.ws.send(json.dumps(request)),
                    timeout=5.0
                )
                
                response = await asyncio.wait_for(
                    self.ws.recv(),
                    timeout=30.0
                )
                
                response_data = json.loads(response)
                elapsed_time = time.time() - start_time
                
                if "error" in response_data:
                    print(f"⚠️ LLM error: {response_data['error']}")
                    if attempt < 2:
                        await asyncio.sleep(1.0)
                        continue
                    return None, elapsed_time
                
                if "text" in response_data:
                    return response_data["text"], elapsed_time
                
                return None, elapsed_time
                
            except websockets.exceptions.ConnectionClosed as e:
                print(f"⚠️ LLM connection closed: {e}, reconnecting...")
                self.connected = False
                self.ws = None
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
                
            except asyncio.TimeoutError:
                print(f"⚠️ LLM timeout on attempt {attempt + 1}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
                
            except Exception as e:
                print(f"⚠️ LLM error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
        
        return None, time.time() - start_time
    
    async def close(self):
        """Close the WebSocket connection"""
        async with self.lock:
            if self.ws:
                try:
                    await self.ws.close()
                    self.connected = False
                    print("🔌 LLM WebSocket closed")
                except:
                    pass
                finally:
                    self.ws = None

# ========== PERSISTENT WEBSOCKET CLIENT FOR XTTS ==========
class XTTSPersistentClient:
    """Persistent WebSocket client for XTTS with auto-reconnect"""
    
    def __init__(self, server_url: str, voice_clone_path: str = None):
        self.server_url = server_url
        self.voice_clone_path = voice_clone_path
        self.ws = None
        self.lock = asyncio.Lock()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0
        
        # Voice cloning cache
        self.voice_reference_b64 = None
        self.voice_reference_loaded = False
        self.voice_reference_trimmed = False
        
        # Preload voice reference if provided
        if self.voice_clone_path:
            self._preload_voice_reference()
    
    def _preload_voice_reference(self):
        """Preload and cache voice reference file"""
        try:
            voice_path = Path(self.voice_clone_path)
            if not voice_path.exists():
                print(f"⚠️ Voice reference file not found: {self.voice_clone_path}")
                return
            
            print(f"📁 Loading voice reference: {self.voice_clone_path}")
            
            # Process the audio file (trim if needed)
            audio_bytes, trimmed = process_audio_file_for_voice_reference(self.voice_clone_path)
            
            if audio_bytes is None:
                print(f"❌ Failed to load voice reference")
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
    
    async def connect(self):
        """Establish WebSocket connection or reconnect if needed"""
        async with self.lock:
            if self.connected and self.ws:
                try:
                    # Check if connection is still alive by trying to get state
                    if self.ws.state == websockets.protocol.State.OPEN:
                        return True
                except:
                    # Connection is dead
                    self.connected = False
                    self.ws = None
            
            try:
                print(f"🔗 Connecting to XTTS WebSocket...")
                self.ws = await websockets.connect(
                    self.server_url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=30,
                    max_size=50 * 1024 * 1024,  # 50MB max size for audio
                    compression=None  # Lower latency
                )
                
                self.connected = True
                self.reconnect_attempts = 0
                print(f"✅ XTTS WebSocket connected")
                return True
                
            except Exception as e:
                self.connected = False
                self.ws = None
                self.reconnect_attempts += 1
                
                if self.reconnect_attempts <= self.max_reconnect_attempts:
                    print(f"⚠️ XTTS WebSocket connection failed (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}): {e}")
                    await asyncio.sleep(self.reconnect_delay * self.reconnect_attempts)
                    return await self.connect()
                else:
                    print(f"❌ Failed to connect to XTTS WebSocket after {self.max_reconnect_attempts} attempts")
                    return False
    
    async def ensure_connection(self):
        """Ensure we have a valid connection"""
        if not self.connected or not self.ws:
            return await self.connect()
        
        # Check connection state
        try:
            # Try to get the state - if it fails, connection is dead
            state = self.ws.state
            if state != websockets.protocol.State.OPEN:
                print(f"⚠️ XTTS WebSocket state is {state}, reconnecting...")
                self.connected = False
                self.ws = None
                return await self.connect()
            return True
        except Exception as e:
            print(f"⚠️ XTTS WebSocket check failed: {e}, reconnecting...")
            self.connected = False
            self.ws = None
            return await self.connect()
    
    # async def tts(self, text: str, prompt_id: int) -> Tuple[Optional[bytes], float]:
    #     """Convert text to speech using persistent WebSocket"""
    #     start_time = time.time()
        
    #     # Try with retries
    #     for attempt in range(3):
    #         try:
    #             # Ensure connection
    #             if not await self.ensure_connection():
    #                 print(f"❌ XTTS connection failed, cannot send request")
    #                 return None, time.time() - start_time
                
    #             # Build request
    #             request = {
    #                 "model_id": "xtts",
    #                 "prompt": text,
    #                 "prompt_id": prompt_id
    #             }
                
    #             # Add voice cloning if available
    #             if self.voice_reference_loaded:
    #                 request["voice_cloning"] = True
    #                 request["voice_reference"] = self.voice_reference_b64
    #                 voice_status = "trimmed to 5s" if self.voice_reference_trimmed else "original"
    #                 print(f"🎤 Voice cloning enabled ({voice_status})")
                
    #             # Send request
    #             await asyncio.wait_for(
    #                 self.ws.send(json.dumps(request)),
    #                 timeout=5.0
    #             )
                
    #             # Receive response
    #             response = await asyncio.wait_for(
    #                 self.ws.recv(),
    #                 timeout=30.0
    #             )
                
    #             response_data = json.loads(response)
    #             elapsed_time = time.time() - start_time
                
    #             if "error" in response_data:
    #                 print(f"⚠️ XTTS error: {response_data['error']}")
    #                 if attempt < 2:
    #                     await asyncio.sleep(1.0)
    #                     continue
    #                 return None, elapsed_time
                
    #             if "audio_b64" in response_data:
    #                 audio_bytes = base64.b64decode(response_data["audio_b64"])
    #                 return audio_bytes, elapsed_time
                
    #             return None, elapsed_time
                
    #         except websockets.exceptions.ConnectionClosed as e:
    #             print(f"⚠️ XTTS connection closed: {e}, reconnecting...")
    #             self.connected = False
    #             self.ws = None
    #             if attempt < 2:
    #                 await asyncio.sleep(1.0)
    #                 continue
    #             return None, time.time() - start_time
                
    #         except asyncio.TimeoutError:
    #             print(f"⚠️ XTTS timeout on attempt {attempt + 1}")
    #             if attempt < 2:
    #                 await asyncio.sleep(1.0)
    #                 continue
    #             return None, time.time() - start_time
                
    #         except Exception as e:
    #             print(f"⚠️ XTTS error on attempt {attempt + 1}: {e}")
    #             if attempt < 2:
    #                 await asyncio.sleep(1.0)
    #                 continue
    #             return None, time.time() - start_time
        
    #     return None, time.time() - start_time
    
    async def tts(self, text: str, prompt_id: int) -> Tuple[Optional[bytes], float]:
        """Convert text to speech using persistent WebSocket - ENGLISH ONLY"""
        start_time = time.time()
        
        # Preprocess text to ensure English only
        # Remove any non-English characters but keep punctuation
        text_clean = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', ' ', text)
        text_clean = re.sub(r'\s+', ' ', text_clean).strip()
        
        # If text becomes empty after cleaning, use a fallback
        if not text_clean:
            text_clean = "Sorry, I didn't get that. Could you please repeat in English?"
        
        print(f"🎤 TTS Input (cleaned): {text_clean}")
        
        # Try with retries
        for attempt in range(3):
            try:
                # Ensure connection
                if not await self.ensure_connection():
                    print(f"❌ XTTS connection failed, cannot send request")
                    return None, time.time() - start_time
                
                # Build request - ADD LANGUAGE PARAMETER
                request = {
                    "model_id": "xtts",
                    "prompt": text_clean,  # Use cleaned text
                    "prompt_id": prompt_id,
                    "language": "en"  # Force English language
                }
                
                # Add voice cloning if available
                if self.voice_reference_loaded:
                    request["voice_cloning"] = True
                    request["voice_reference"] = self.voice_reference_b64
                    voice_status = "trimmed to 5s" if self.voice_reference_trimmed else "original"
                    print(f"🎤 Voice cloning enabled ({voice_status})")
                
                # Send request
                await asyncio.wait_for(
                    self.ws.send(json.dumps(request)),
                    timeout=5.0
                )
                
                # Receive response
                response = await asyncio.wait_for(
                    self.ws.recv(),
                    timeout=30.0
                )
                
                response_data = json.loads(response)
                elapsed_time = time.time() - start_time
                
                if "error" in response_data:
                    print(f"⚠️ XTTS error: {response_data['error']}")
                    if attempt < 2:
                        await asyncio.sleep(1.0)
                        continue
                    return None, elapsed_time
                
                if "audio_b64" in response_data:
                    audio_bytes = base64.b64decode(response_data["audio_b64"])
                    return audio_bytes, elapsed_time
                
                return None, elapsed_time
                
            except websockets.exceptions.ConnectionClosed as e:
                print(f"⚠️ XTTS connection closed: {e}, reconnecting...")
                self.connected = False
                self.ws = None
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
                
            except asyncio.TimeoutError:
                print(f"⚠️ XTTS timeout on attempt {attempt + 1}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
                
            except Exception as e:
                print(f"⚠️ XTTS error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time
        
        return None, time.time() - start_time

    async def close(self):
        """Close the WebSocket connection"""
        async with self.lock:
            if self.ws:
                try:
                    await self.ws.close()
                    self.connected = False
                    print("🔌 XTTS WebSocket closed")
                except:
                    pass
                finally:
                    self.ws = None

# ========== ENHANCED ORDER MANAGER ==========
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
    
# ========== RESTAURANT JSON RAG SYSTEM WITH INTENT ROUTER ==========
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

# ========== RESTAURANT LLM WITH PERSISTENT CONNECTION ==========
class RestaurantLLM:
    """Restaurant LLM with persistent WebSocket connection"""
    
    def __init__(self, server_url: str, token: str, voice_clone_path: str = None):
        self.server_url = server_url
        self.token = token
        self.voice_clone_path = voice_clone_path
        self.llm_client = LLMPersistentClient(server_url, token)
        
        # System prompt
        self.system_prompt = (
            "You are AI Voice assistant, a friendly restaurant receptionist. "
            "Speak ONLY in English. Keep responses very short (1 sentence max). "
            "Be warm, confident, helpful but always professional. "
            
            "CRITICAL LANGUAGE RULES - YOU MUST FOLLOW THESE: "
            "1. Speak ONLY in English. Never use any other language. "
            "2. If the user speaks in another language, politely ask them to speak in English. "
            "3. Your vocabulary must be restaurant-specific English only. "
            "4. Keep sentences simple and clear. "

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
    
    async def generate_response(self, text: str, prompt_id: int) -> Tuple[Optional[str], float]:
        """Generate response using persistent WebSocket LLM"""
        # Build the full prompt
        full_prompt = f"{self.system_prompt}\n\nUser: {text}\nAssistant:"
        
        # Use the persistent LLM client
        response, llm_time = await self.llm_client.generate(full_prompt, prompt_id)
        
        if response:
            # Clean the response
            raw_response = response
            
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
        
        return None, llm_time

# ========== COMPLETE VOICE ASSISTANT WITH ALL PERSISTENT CONNECTIONS ==========
class RestaurantVoiceAssistant:
    """Complete Restaurant Voice Assistant with All Persistent Connections"""
    
    def __init__(self, server_url: str, token: str, voice_clone_path: str = None):
        self.server_url = server_url
        self.token = token
        self.voice_clone_path = voice_clone_path
        
        # Initialize ALL persistent clients
        self.xtts_client = XTTSPersistentClient(server_url, voice_clone_path)
        self.stt_client = STTPersistentClient(server_url)
        self.llm_client = RestaurantLLM(server_url, token, voice_clone_path)  # Updated
        
        # Initialize other components
        self.order_manager = EnhancedOrderManager()
        self.rag_system = RestaurantRAGSystem(self.order_manager)
        
        # Recording setup
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.samplerate = 16000
        
        # Session tracking
        self.session_count = 0
        self.next_prompt_id = 1000
        
        # Conversation context
        self.first_interaction = True
    
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
    
    async def stt_transcribe(self, audio_bytes: bytes, prompt_id: int) -> Tuple[Optional[str], float]:
        """STT: Convert speech to text using persistent WebSocket"""
        # Convert audio to base64
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        
        # Use the persistent STT client
        return await self.stt_client.transcribe(audio_b64, prompt_id)
    
    async def tts_speak(self, text: str, prompt_id: int) -> Tuple[Optional[bytes], float]:
        """TTS: Convert text to speech using persistent WebSocket"""
        # Use the persistent XTTS client
        return await self.xtts_client.tts(text, prompt_id)
    
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
            # Check if transcription failed due to non-English
            print("⚠️ Transcription failed or empty")
            # Use LLM to respond appropriately
            reply = "I'm sorry, I couldn't understand that. Could you please speak in English?"
            audio_response, tts_time = await self.tts_speak(reply, prompt_id)
            if audio_response:
                await self.play_audio(audio_response)
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
            llm_response, llm_time = await self.llm_client.generate_response(transcription, prompt_id)
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
            if not reply.startswith("Hello") and not reply.startswith("Welcome"):
                reply = f"Welcome to {name}!"
                # reply = f"Welcome to {name}! We are located at {addr}. {reply}"
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
        print("🍽️  RESTAURANT VOICE ASSISTANT v5.0 (All Persistent Connections)")
        print("="*60)
        print("✅ Features: Single/Multiple Item Ordering | Add/Update/Delete")
        print("✅ Order Memory | Finalization with JSON Saving | Billing")
        print("✅ Persistent WebSocket: XTTS ✅ | STT ✅ | LLM ✅")
        print("🛑 Press Ctrl+C to exit")
        print("="*60)
        
        try:
            # Initial connection for all services
            print("🔗 Establishing all persistent connections...")
            
            # Connect to XTTS
            xtts_connected = await self.xtts_client.connect()
            
            # Connect to STT
            stt_connected = await self.stt_client.connect()
            
            # Connect to LLM (through the LLM client)
            llm_connected = True  # Will connect on first use
            
            if xtts_connected:
                print("✅ Persistent XTTS connection established")
            else:
                print("⚠️ Failed to establish XTTS connection")
            
            if stt_connected:
                print("✅ Persistent STT connection established")
            else:
                print("⚠️ Failed to establish STT connection")
            
            print("✅ LLM ready (will connect on first use)")
            
            while True:
                await self.single_conversation_session()
                
        except KeyboardInterrupt:
            print("\n👋 Restaurant assistant stopped")
            
            # Show final order status before exit
            if not self.order_manager.is_empty():
                print(f"\n📋 Current Order Status:")
                print(f"   Items: {len(self.order_manager.lines)}")
                print(f"   Total: {self.order_manager.subtotal():.0f} rupees")
                print("⚠️  Order not finalized - will be lost on exit")
        except Exception as e:
            print(f"\n❌ Assistant error: {e}")
            logger.exception("Fatal error in voice assistant")
        finally:
            # Always cleanup connections
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources and close all connections"""
        # Close XTTS connection
        if hasattr(self, 'xtts_client'):
            await self.xtts_client.close()
        
        # Close STT connection
        if hasattr(self, 'stt_client'):
            await self.stt_client.close()
        
        # Close LLM connection if using persistent LLM
        if hasattr(self, 'llm_client') and hasattr(self.llm_client, 'llm_client'):
            await self.llm_client.llm_client.close()
        
        print("✅ All connections closed")

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
    try:
        # Run assistant
        await assistant.run_voice_assistant()
    except KeyboardInterrupt:
        print("\n👋 Restaurant assistant stopped")
    except Exception as e:
        print(f"\n❌ Assistant error: {e}")
        logger.exception("Fatal error in voice assistant")
    finally:
        # Always cleanup connections
        await assistant.cleanup()


if __name__ == "__main__":
    asyncio.run(main())