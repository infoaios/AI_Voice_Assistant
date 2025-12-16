"""
Entity Service

Extracts and matches entities from user input:
- Dish name matching with fuzzy search
- Quantity extraction
- Multiple dish detection
- Phonetic corrections for Indian food terms

This service depends on IMenuRepository interface, not concrete implementation.
Changes to JSONRepository implementation won't affect this service.
"""
import re
from typing import List, Tuple, Optional, Dict

# Use interface for stable contract
try:
    from core.interfaces import IMenuRepository
except ImportError:
    # Fallback for backward compatibility
    from repos.json_repo import JSONRepository as IMenuRepository


class EntityService:
    """
    Service for entity extraction and fuzzy matching
    
    Depends on IMenuRepository interface, allowing any menu repository implementation.
    """
    
    def __init__(self, menu_repo: IMenuRepository):
        """
        Initialize with menu repository (interface, not concrete class)
        
        Args:
            menu_repo: Menu repository implementing IMenuRepository protocol
        """
        self.menu_repo = menu_repo
    
    @staticmethod
    def normalize(word: str) -> str:
        """Normalize word for matching"""
        return "".join(x for x in word.lower() if x.isalpha())
    
    @staticmethod
    def edit_distance(a: str, b: str) -> int:
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
    
    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Calculate similarity score (0.0 to 1.0)"""
        a_norm = EntityService.normalize(a)
        b_norm = EntityService.normalize(b)
        if not a_norm or not b_norm:
            return 0.0
        dist = EntityService.edit_distance(a_norm, b_norm)
        return 1.0 - dist / max(len(a_norm), len(b_norm))
    
    def find_all_dish_matches(
        self,
        text: str,
        min_word_sim: float = 0.85,
        min_coverage: float = 0.5
    ) -> List[Tuple[Dict, Dict, float]]:
        """
        Find menu items matching text, scored by how many name-words match.
        Returns list of (category, item, score) tuples.
        """
        text_low = text.lower()
        text_words = [self.normalize(w) for w in text.split()]
        matches = []
        
        for cat, item in self.menu_repo.all_menu_items():
            name_words = [self.normalize(w) for w in item["name"].split()]
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
                    sim = self.similarity(tw, dw)
                    if sim > max_sim:
                        max_sim = sim
                    if sim >= min_word_sim:
                        matched_name_words.add(dw)

            # No relevant word match → skip this dish
            if not matched_name_words:
                continue

            # Coverage = how many of the dish name's words matched
            coverage = len(matched_name_words) / len(name_words)

            # Filter out extremely weak matches
            if coverage < min_coverage:
                continue
            
            # Penalize matches that are too short
            if len(item["name"].split()) > 2 and coverage < 0.7:
                continue

            # Final score: prioritize coverage, use max_sim as small tie-breaker
            score = coverage + 0.1 * max_sim
            matches.append((cat, item, score))
        
        matches.sort(key=lambda x: x[2], reverse=True)
        return matches
    
    def best_dish_match(self, text: str) -> Tuple[Optional[Dict], Optional[Dict], float]:
        """
        Find the single best matching menu item using the same scoring
        logic as find_all_dish_matches (word coverage based).
        """
        matches = self.find_all_dish_matches(text)
        if not matches:
            return None, None, 0.0
        cat, item, score = matches[0]
        if score < 0.65:
            return None, None, 0.0

        return cat, item, score
    
    @staticmethod
    def extract_quantity(text: str, default: int = 1) -> int:
        """Extract quantity from text"""
        word_to_num = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10
        }

        tokens = text.lower().split()

        # Check for word numbers
        for token in tokens:
            if token in word_to_num:
                return word_to_num[token]
        
        nums = []
        for t in tokens:
            t_clean = "".join(ch for ch in t if ch.isdigit())
            if t_clean.isdigit():
                nums.append(int(t_clean))
        return max(nums) if nums else default
    
    @staticmethod
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
    
    @staticmethod
    def apply_phonetic_corrections(text: str) -> str:
        """
        Fix common speech-to-text errors for Indian food terms.
        Apply this BEFORE processing the text.
        """
        corrections = {
            "how to make": "how to make",
            "how do you make": "how do you make",
            # Bread items
            "button hand": "butter naan",
            "button nan": "butter naan",
            "better nan": "butter naan",
            "butter nan": "butter naan",
            "plane nan": "plain naan",
            "plain nan": "plain naan",
            "garlic nan": "garlic naan",
            "roti": "roti",
            "paratha": "paratha",
            
            # Desserts
            "gulab jamun": "gulab jamun",
            "golub jamun": "gulab jamun",
            "gulab jaman": "gulab jamun",
            "rasgulla": "rasgulla",
            "ras gulla": "rasgulla",
            
            # Main dishes
            "butter chicken": "butter chicken",
            "better chicken": "butter chicken",
            "panel tikka": "paneer tikka",
            "paneer tika": "paneer tikka",
            "biryani": "biryani",
            "biriyani": "biryani",
            "dal makhani": "dal makhani",
            "dhal makhani": "dal makhani",
            "masala chai": "masala chai",
            "masala tea": "masala chai",
            "fresh lime": "fresh lime soda",
            
            # Quantity phrases (Indian English)
            "on 21": "21",  # "On 21 Gulab Jamun" → "21 Gulab Jamun"
            "i want 21": "i want 21",
            "give me 21": "give me 21",
            
            # Common words
            "prize": "price",
            "prise": "price",
            "cost": "price",
            "rupee": "rupees",
            "ruppes": "rupees",
        }
        
        text_lower = text.lower()
        
        # Apply corrections
        for wrong, correct in corrections.items():
            if wrong in text_lower:
                # Use word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(wrong) + r'\b'
                text_lower = re.sub(pattern, correct, text_lower, flags=re.IGNORECASE)
        
        return text_lower

