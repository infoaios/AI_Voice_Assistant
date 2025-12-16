"""
Core Interfaces and Protocols

This module defines stable contracts that minimize coupling between modules.
Implementations can change without affecting dependents, as long as interfaces remain stable.
"""
from abc import ABC, abstractmethod
from typing import Protocol, Dict, Any, Optional, Generator, Tuple, List
from typing_extensions import runtime_checkable


# ========== REPOSITORY INTERFACES ==========

@runtime_checkable
class IMenuRepository(Protocol):
    """Interface for menu data repository - stable contract"""
    
    def get_menu(self) -> List[Dict[str, Any]]:
        """Get menu data"""
        ...
    
    def get_restaurant_info(self) -> Dict[str, Any]:
        """Get restaurant information"""
        ...
    
    def all_menu_items(self) -> Generator[Tuple[Dict, Dict], None, None]:
        """Generator for all menu items"""
        ...


@runtime_checkable
class IOrderRepository(Protocol):
    """Interface for order persistence - stable contract"""
    
    def save_order(self, order_data: Dict[str, Any]) -> bool:
        """Save order to persistent storage"""
        ...
    
    def load_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Load order from persistent storage"""
        ...


# ========== SERVICE INTERFACES ==========

@runtime_checkable
class IEntityService(Protocol):
    """Interface for entity extraction - stable contract"""
    
    def find_all_dish_matches(self, text: str, min_word_sim: float = 0.85, min_coverage: float = 0.5) -> List[Tuple[Dict, Dict, float]]:
        """Find menu items matching text"""
        ...
    
    def best_dish_match(self, text: str) -> Tuple[Optional[Dict], Optional[Dict], float]:
        """Find best matching menu item"""
        ...
    
    def extract_quantity(self, text: str, default: int = 1) -> int:
        """Extract quantity from text"""
        ...
    
    def apply_phonetic_corrections(self, text: str) -> str:
        """Apply phonetic corrections to text"""
        ...


@runtime_checkable
class IPolicyService(Protocol):
    """Interface for business rules - stable contract"""
    
    def is_restaurant_open(self) -> Tuple[bool, str]:
        """Check if restaurant is open"""
        ...
    
    def check_item_availability(self, item_name: str) -> Tuple[bool, str]:
        """Check if item is available"""
        ...
    
    def should_block_llm(self, text: str) -> bool:
        """Check if query should be blocked from LLM"""
        ...


@runtime_checkable
class IActionService(Protocol):
    """Interface for action execution - stable contract"""
    
    def finalize_order(self, order: Any, text: str) -> Tuple[bool, Optional[str]]:
        """Finalize order with customer details"""
        ...


@runtime_checkable
class IDialogService(Protocol):
    """Interface for dialog management - stable contract"""
    
    def process_message(self, text: str, order: Any) -> Optional[str]:
        """Process user message and return response"""
        ...


# ========== LLM SERVICE INTERFACES ==========

@runtime_checkable
class ISTTService(Protocol):
    """Interface for Speech-to-Text - stable contract"""
    
    def transcribe_with_timing(self, audio: Any) -> Tuple[str, float]:
        """Transcribe audio with timing"""
        ...


@runtime_checkable
class ITTTService(Protocol):
    """Interface for Text-to-Text (LLM) - stable contract"""
    
    def chat(self, user_text: str) -> Tuple[str, float]:
        """Generate LLM response"""
        ...
    
    @staticmethod
    def clean_english_reply(raw: str) -> str:
        """Clean LLM output"""
        ...


@runtime_checkable
class ITTSService(Protocol):
    """Interface for Text-to-Speech - stable contract"""
    
    def speak(self, text: str) -> float:
        """Speak text and return generation time"""
        ...


# ========== ORDER ENTITY INTERFACE ==========

@runtime_checkable
class IOrderManager(Protocol):
    """Interface for order management - stable contract"""
    
    def add_item(self, item_name: str, unit_price: float, qty: int = 1, **kwargs) -> None:
        """Add items to order"""
        ...
    
    def remove_item(self, item_name: str, qty: Optional[int] = None) -> None:
        """Remove items from order"""
        ...
    
    def clear(self) -> None:
        """Clear entire order"""
        ...
    
    def is_empty(self) -> bool:
        """Check if order is empty"""
        ...
    
    def subtotal(self) -> float:
        """Calculate order total"""
        ...
    
    def to_json(self) -> Dict[str, Any]:
        """Export order as JSON"""
        ...
    
    def describe_order(self) -> str:
        """Generate order description"""
        ...

