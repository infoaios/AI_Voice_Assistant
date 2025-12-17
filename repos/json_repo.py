"""JSON repository for restaurant data"""
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Generator, Tuple


logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """Get project root directory"""
    # This file is in repos/, so project root is parent directory
    current_file = Path(__file__)
    # repos/json_repo.py -> repos/ -> project root
    return current_file.parent.parent  # project root


class JSONRepository:
    """Repository for loading and managing JSON data"""
    
    def __init__(self, data_file: str = None):
        if data_file is None:
            # Default to data folder in project root
            project_root = get_project_root()
            self.data_file = str(project_root / "data" / "restaurant_data.json")
        else:
            self.data_file = data_file
        self.data: Dict[str, Any] = {}
        self.load_data()
    
    def load_data(self) -> bool:
        """Load data from JSON file"""
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            logger.info(f"✅ Loaded JSON successfully from {self.data_file}")
            return True
        except Exception as e:
            logger.error(f"❌ FAILED loading JSON: {e}")
            self.data = {}
            return False
    
    def get_data(self) -> Dict[str, Any]:
        """Get all data"""
        return self.data
    
    def get_restaurant_info(self) -> Dict[str, Any]:
        """Get restaurant information"""
        return self.data.get("restaurant", {})
    
    def get_menu(self) -> list:
        """Get menu data"""
        return self.data.get("menu", [])
    
    def all_menu_items(self) -> Generator[Tuple[Dict, Dict], None, None]:
        """Generator for all menu items"""
        for cat in self.get_menu():
            for item in cat.get("items", []):
                yield cat, item
    
    def find_menu_item_by_name(self, name: str) -> Optional[Tuple[Dict, Dict]]:
        """Find menu item by exact name match"""
        name_low = name.lower()
        for cat, item in self.all_menu_items():
            if item["name"].lower() == name_low:
                return cat, item
        return None

