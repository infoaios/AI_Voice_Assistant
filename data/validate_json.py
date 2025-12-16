"""Quick validation script for restaurant_data.json"""
import json
import sys
from pathlib import Path

json_file = Path(__file__).parent / "restaurant_data.json"

try:
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("✅ JSON is valid!")
    print(f"Restaurant: {data['restaurant']['name']}")
    print(f"Address: {data['restaurant']['address']}")
    print(f"Menu categories: {len(data['menu'])}")
    
    total_items = sum(len(cat['items']) for cat in data['menu'])
    print(f"Total items: {total_items}")
    
    # Count by category
    print("\nItems by category:")
    for cat in data['menu']:
        print(f"  - {cat['name']}: {len(cat['items'])} items")
    
    # Check for required fields
    required_restaurant_fields = ['name', 'address', 'phone']
    missing = [f for f in required_restaurant_fields if f not in data.get('restaurant', {})]
    if missing:
        print(f"\n⚠️ Missing restaurant fields: {missing}")
    else:
        print("\n✅ All required restaurant fields present")
    
    # Check menu items
    items_without_price = []
    items_without_name = []
    for cat in data['menu']:
        for item in cat.get('items', []):
            if 'name' not in item:
                items_without_name.append(item.get('id', 'unknown'))
            if 'price' not in item:
                items_without_price.append(item.get('name', 'unknown'))
    
    if items_without_name:
        print(f"⚠️ Items without name: {items_without_name}")
    if items_without_price:
        print(f"⚠️ Items without price: {items_without_price}")
    
    if not items_without_name and not items_without_price:
        print("✅ All menu items have name and price")
    
    print("\n✅ Validation complete!")
    
except json.JSONDecodeError as e:
    print(f"❌ JSON is invalid: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

