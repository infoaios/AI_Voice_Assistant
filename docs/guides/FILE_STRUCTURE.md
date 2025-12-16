# File Structure & Storage Locations

This document explains where to store all required files for the voice platform.

## Project Root Structure

```
AI_voice_assistent_final/          # Project root
├── data/                          # ⭐ Data folder (REQUIRED)
│   ├── restaurant_data.json      # ⭐ Restaurant menu data (REQUIRED)
│   └── saved_voices/              # ⭐ Voice clone files (REQUIRED)
│       └── refe2.wav              # Voice clone reference file
├── orders/                        # Auto-created: Order history
│   └── orders_history.json        # Auto-created: Saved orders
├── logs/                          # Auto-created: Application logs
│   └── assistant.log             # Auto-created: Conversation logs
├── tts_output.wav                 # Auto-created: Temporary TTS output
└── voice_platform/                # Application code
    ├── main.py
    ├── services/
    ├── llms/
    └── ...
```

## Required Files

### 1. `restaurant_data.json` 
**Location**: Data folder (`AI_voice_assistent_final/data/restaurant_data.json`)

**Purpose**: Contains restaurant menu, items, prices, and restaurant information.

**Example structure**:
```json
{
  "restaurant": {
    "name": "Infocall Dine",
    "address": "MG Road, Mumbai",
    "phone": "+91 98765 43210"
  },
  "menu": [
    {
      "name": "Starters",
      "items": [
        {
          "name": "Paneer Tikka",
          "price": 250,
          "description": "Grilled cottage cheese with spices"
        }
      ]
    }
  ]
}
```

### 2. Voice Clone File
**Location**: `data/saved_voices/refe2.wav` (relative to project root)

**Purpose**: Reference audio file for voice cloning in TTS.

**Path**: `AI_voice_assistent_final/data/saved_voices/refe2.wav`

**Note**: You can change the filename in `services/config_service.py`:
```python
VOICE_CLONE_WAV = "data/saved_voices/your_voice_file.wav"
```

## Auto-Created Directories

These directories are created automatically when the application runs:

### 1. `orders/`
**Location**: Project root (`AI_voice_assistent_final/orders/`)

**Contents**:
- `orders_history.json` - All finalized orders are appended here

### 2. `logs/`
**Location**: Project root (`AI_voice_assistent_final/logs/`)

**Contents**:
- `assistant.log` - Application logs and conversation history

### 3. `tts_output.wav`
**Location**: Project root (`AI_voice_assistent_final/tts_output.wav`)

**Purpose**: Temporary file for TTS audio generation (overwritten each time)

## Setup Instructions

1. **Create the data folder structure**:
   ```bash
   cd AI_voice_assistent_final
   mkdir data
   mkdir data\saved_voices
   ```

2. **Place your files**:
   - Copy `restaurant_data.json` to `data/` folder
   - Copy your voice clone file (`refe2.wav` or your file) to `data/saved_voices/`

3. **Verify structure**:
   ```
   AI_voice_assistent_final/
   ├── data/
   │   ├── restaurant_data.json   ✅
   │   └── saved_voices/
   │       └── refe2.wav           ✅
   └── voice_platform/
       └── main.py
   ```

## Running the Application

The application will automatically:
- Load `restaurant_data.json` from project root
- Find voice clone file in `saved_voices/`
- Create `orders/` and `logs/` directories if they don't exist
- Save orders to `orders/orders_history.json`
- Save logs to `logs/assistant.log`

## Troubleshooting

### Error: "FAILED loading JSON"
- **Solution**: Ensure `restaurant_data.json` is in the `data/` folder (`data/restaurant_data.json`)

### Error: "Voice file not found"
- **Solution**: 
  1. Create `data/saved_voices/` directory structure
  2. Place your voice file (`refe2.wav`) in `data/saved_voices/`
  3. Or update `VOICE_CLONE_WAV` in `services/config_service.py` to match your file path

### Orders not saving
- **Solution**: Check write permissions in project root directory

