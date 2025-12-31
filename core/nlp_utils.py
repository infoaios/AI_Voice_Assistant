import re
from typing import List, Tuple, Optional, Dict, Any
from core.restaurant_data import REST_DATA

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
        "wage option": "veg option",
        "wage options": "veg options",
        "wage option": "vegetarian option",
        "wage dish": "veg dish",
        "wage food": "veg food",
        "wage items": "veg items",
        "what's age": "what's veg",
        "do you have wage": "do you have veg",
        "any wage": "any veg",
        "vegetable option": "vegetarian option",
        "vegetable options": "vegetarian options",
        "vegetarian option": "vegetarian option",
        "vegetarian items": "vegetarian items",
        "main curse": "main course",
        "be average": "beverage",
        "be averages": "beverages",
        "what's in": "what's in",
        "what is in": "what's in",
        "what sin": "what's in",
        "what's the": "what's in the",
        "whats in": "what's in",
        "whats the": "what's in the",
        "whats in the": "what's in the"
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