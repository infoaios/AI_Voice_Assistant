# Data Folder

This folder contains all data files for the voice platform.

## Files

### `restaurant_data.json`
Main restaurant menu data file. Contains:
- Restaurant information (name, address, hours, etc.)
- Menu categories and items
- Item details including:
  - Variants (size options)
  - Addons (extras)
  - Allergens
  - Preparation time
  - Spice level
- Offers and promotions
- Payment methods

### `saved_voices/`
Voice clone files for TTS (Text-to-Speech).

**Supported formats**: WAV (recommended)

**Current files**:
- `refe2.wav` - Primary voice file (configured in code)
- `reference.wav` - Alternative voice file
- `ref1.m4a` - M4A format (needs conversion)

## Audio Conversion

To convert M4A files to WAV format:

```bash
# Install required package
pip install pydub

# Also install ffmpeg from: https://ffmpeg.org/download.html

# Run conversion script
python convert_audio.py
```

Or convert manually:
```python
from pydub import AudioSegment
audio = AudioSegment.from_file("ref1.m4a", format="m4a")
audio.export("ref1.wav", format="wav")
```

## Backup Files

- `restaurant_data_old.json` - Backup of previous menu data
- `restaurant_data_example.json` - Example/template file

## Validation

To validate the JSON structure:
```bash
python validate_json.py
```

