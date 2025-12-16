"""
Policy Service

Enforces business rules and policies:
- Restaurant hours and availability
- Item availability checks
- LLM query blocking rules
- Business logic validation

This service centralizes all business policy decisions.
"""
import datetime
from typing import Tuple

from global_data import (
    RESTAURANT_OPEN_HOUR,
    RESTAURANT_CLOSE_HOUR,
    OUT_OF_STOCK_ITEMS,
    FOOD_KEYWORDS
)


class PolicyService:
    """
    Service for business rules and policy enforcement
    
    Centralizes all business logic decisions including availability,
    operating hours, and query routing policies.
    """
    
    @staticmethod
    def is_restaurant_open() -> Tuple[bool, str]:
        """
        Check if restaurant is open based on current time
        
        Uses RESTAURANT_OPEN_HOUR and RESTAURANT_CLOSE_HOUR from global_data.
        
        Returns:
            Tuple of (is_open, message)
        """
        now = datetime.datetime.now()
        current_hour = now.hour
        
        if RESTAURANT_OPEN_HOUR <= current_hour < RESTAURANT_CLOSE_HOUR:
            return True, ""
        else:
            return False, f"Sorry, we're currently closed. Our hours are {RESTAURANT_OPEN_HOUR} AM to {RESTAURANT_CLOSE_HOUR} PM."
    
    @staticmethod
    def check_item_availability(item_name: str) -> Tuple[bool, str]:
        """
        Check if item is available
        
        Uses OUT_OF_STOCK_ITEMS from global_data.
        
        Args:
            item_name: Name of the item to check
            
        Returns:
            Tuple of (is_available, message)
        """
        if item_name in OUT_OF_STOCK_ITEMS:
            return False, f"Sorry, {item_name} is currently out of stock."
        
        return True, ""
    
    @staticmethod
    def should_block_llm(text: str) -> bool:
        """
        Return True if query should be blocked from LLM and handled by JSON only.
        
        Uses FOOD_KEYWORDS from global_data to determine if query is food-related.
        
        Args:
            text: User input text to check
            
        Returns:
            True if query should be blocked from LLM
        """
        text_low = text.lower()
        return any(keyword in text_low for keyword in FOOD_KEYWORDS)

