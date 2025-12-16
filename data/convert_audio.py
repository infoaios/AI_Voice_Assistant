"""Convert M4A audio files to WAV format for TTS compatibility"""
import os
from pathlib import Path

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False
    print("⚠️ pydub not installed. Install it with: pip install pydub")
    print("   Also install ffmpeg: https://ffmpeg.org/download.html")


def convert_m4a_to_wav(input_file: str, output_file: str = None):
    """Convert M4A file to WAV format"""
    if not PYDUB_AVAILABLE:
        print("❌ Cannot convert: pydub is not installed")
        return False
    
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"❌ File not found: {input_file}")
        return False
    
    if output_file is None:
        output_file = str(input_path.with_suffix('.wav'))
    
    try:
        print(f"🔄 Converting {input_path.name} to WAV...")
        audio = AudioSegment.from_file(str(input_path), format="m4a")
        audio.export(output_file, format="wav")
        print(f"✅ Converted successfully: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False


def convert_all_m4a_in_folder(folder_path: str = None):
    """Convert all M4A files in a folder to WAV"""
    if folder_path is None:
        folder_path = Path(__file__).parent / "saved_voices"
    else:
        folder_path = Path(folder_path)
    
    if not folder_path.exists():
        print(f"❌ Folder not found: {folder_path}")
        return
    
    m4a_files = list(folder_path.glob("*.m4a"))
    if not m4a_files:
        print(f"ℹ️ No M4A files found in {folder_path}")
        return
    
    print(f"📁 Found {len(m4a_files)} M4A file(s) to convert")
    for m4a_file in m4a_files:
        convert_m4a_to_wav(str(m4a_file))


if __name__ == "__main__":
    print("=" * 60)
    print("Audio Converter: M4A to WAV")
    print("=" * 60)
    
    # Convert all M4A files in saved_voices folder
    convert_all_m4a_in_folder()
    
    print("\n✅ Conversion complete!")

