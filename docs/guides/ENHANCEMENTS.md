# Enhancements: Variants, Addons, and Allergens

## ✅ Implemented Features

### 1. Variants Support
- **Detection**: Automatically detects variant names (e.g., "Large", "Regular", "Boneless") from user input
- **Price Calculation**: Uses variant-specific pricing
- **Order Display**: Shows variant in order description

**Example Usage**:
- User: "I want large paneer tikka"
- System: Adds "Paneer Tikka (Large)" to order with correct price

### 2. Addons Support
- **Detection**: Detects addons from phrases like "with extra cheese", "with raita"
- **Price Calculation**: Automatically adds addon prices to total
- **Order Display**: Shows addons in order description

**Example Usage**:
- User: "Butter chicken with extra gravy"
- System: Adds "Butter Chicken with Extra Gravy" with addon price included

### 3. Allergens Support
- **Storage**: Allergens are stored with each order item
- **Queries**: Users can ask about allergens
- **Order Summary**: Can show all allergens in the order

**Example Usage**:
- User: "Does paneer tikka contain dairy?"
- System: "Paneer Tikka contains: Dairy"

### 4. Enhanced Queries

#### Variant Queries
- "What sizes are available for butter chicken?"
- "What variants does paneer tikka have?"

#### Addon Queries
- "What can I add to paneer tikka?"
- "What extras are available for biryani?"

#### Allergen Queries
- "Does butter chicken contain dairy?"
- "What allergens are in my order?"

## 📝 Code Changes

### Order Entity (`repos/entities/order_entity.py`)
- Enhanced `add_item()` to accept variants, addons, allergens
- Updated `_find_line()` to match items with same variant and addons
- Enhanced `describe_order()` to show variants and addons
- Added `get_allergens_summary()` method

### Dialog Manager (`services/dialog_manager.py`)
- Added `_detect_variant()` method
- Added `_detect_addons()` method
- Added `_get_item_price()` method
- Enhanced item description to show variants, addons, allergens
- Added queries for variants, addons, and allergens

## 🎯 Usage Examples

### Ordering with Variant
```
User: "I want 2 large paneer tikka"
Bot: "Great! I've added 2 Paneer Tikka (Large). Your current order: 2 Paneer Tikka (Large) (600 rupees). Total: 600 rupees."
```

### Ordering with Addons
```
User: "Butter chicken with extra gravy"
Bot: "Great! I've added 1 Butter Chicken with Extra Gravy. Your current order: 1 Butter Chicken with Extra Gravy (400 rupees). Total: 400 rupees."
```

### Querying Variants
```
User: "What sizes are available for paneer tikka?"
Bot: "Paneer Tikka is available in: Regular (220 rupees), Large (300 rupees)."
```

### Querying Allergens
```
User: "Does paneer tikka contain dairy?"
Bot: "Paneer Tikka contains: Dairy."
```

## 🔧 Audio Conversion

### M4A to WAV Converter
A script is provided to convert M4A files to WAV format:

```bash
# Install dependencies
pip install pydub

# Install ffmpeg (required for pydub)
# Download from: https://ffmpeg.org/download.html

# Run converter
cd voice_platform/data
python convert_audio.py
```

The script will automatically convert all M4A files in `saved_voices/` folder to WAV format.

## 📊 JSON Structure Support

The system now fully supports the rich JSON structure:
- ✅ Variants (size options)
- ✅ Addons (extras)
- ✅ Allergens
- ✅ Preparation time (stored, can be queried)
- ✅ Spice level (stored, can be queried)
- ✅ Item IDs
- ✅ Popular flags
- ✅ Chef special flags

## 🚀 Future Enhancements

Potential additions:
1. Preparation time queries ("How long will my order take?")
2. Spice level queries ("Is butter chicken spicy?")
3. Combo deals support
4. Offers/promotions integration
5. Dietary preference filtering (veg/non-veg)

