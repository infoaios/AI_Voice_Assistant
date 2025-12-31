import json
from pathlib import Path
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

