import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# ========== AUDIO TRIMMING FUNCTIONS ==========
def trim_to_5_seconds(input_path, output_path):
    """
    Trim any audio file to first 5 seconds
    
    Args:
        input_path: Path to input audio file
        output_path: Path to output audio file (first 5 seconds)
    """
    try:
        # Construct ffmpeg command to TRIM (not compress)
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file without asking
            '-i', input_path,
            '-t', '5',  # Take only first 5 seconds
            '-filter:a', 'atempo=1.5',  # Speed up by 1.5x
            '-ar', '16000',  # Sample rate 16000 Hz
            '-ac', '1',  # Mono channel
            '-acodec', 'pcm_s16le',  # Audio codec
            '-map_metadata', '-1',  # Remove metadata
            output_path
        ]
        
        print(f"  ↳ Trimming voice reference to 5 seconds with 1.5x speed......")
        
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✓ Voice reference trimmed: {output_path}")
            return True
        else:
            print(f"  ✗ FFmpeg error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("  ✗ Error: ffmpeg not found. Please install ffmpeg.")
        print("    On Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("    On macOS: brew install ffmpeg")
        print("    On Windows: Download from https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def get_audio_duration(input_path):
    """
    Get duration of audio file using ffprobe
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except:
        return None

def process_audio_file_for_voice_reference(input_path):
    """
    Process audio file for voice reference: if >500KB or >10s, trim to 5 seconds
    Returns: (processed_audio_bytes, trimmed_flag)
    """
    try:
        # Check file size
        file_size_bytes = Path(input_path).stat().st_size
        file_size_kb = file_size_bytes / 1024
        
        # Get audio duration
        duration = get_audio_duration(input_path)
        duration_sec = duration if duration else 0
        
        print(f"  ↳ Voice reference file: {file_size_kb:.1f}KB, {duration_sec:.1f}s")
        
        # Check if trimming is needed
        needs_trimming = file_size_bytes > (500 * 1024) or (duration and duration > 10)
        
        if needs_trimming:
            print(f"  ⚠️  Voice reference needs trimming (size: {file_size_kb:.1f}KB, duration: {duration_sec:.1f}s)")
            
            # Create a temporary file for trimmed audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                temp_output = tmp_file.name
            
            # Trim to 5 seconds
            success = trim_to_5_seconds(input_path, temp_output)
            
            if success:
                # Read trimmed audio
                with open(temp_output, 'rb') as f:
                    audio_bytes = f.read()
                
                # Clean up temp file
                try:
                    os.unlink(temp_output)
                except:
                    pass
                
                # Verify trimmed size
                trimmed_kb = len(audio_bytes) / 1024
                trimmed_duration = get_audio_duration(temp_output) if os.path.exists(temp_output) else 0
                
                print(f"  ✓ Trimmed to: {trimmed_kb:.1f}KB, {trimmed_duration:.1f}s")
                return audio_bytes, True
            else:
                # If trimming fails, use original (with warning)
                print(f"  ⚠️  Trimming failed, using original file (may cause issues)")
                with open(input_path, 'rb') as f:
                    return f.read(), False
        else:
            # File is within limits, use as-is
            print(f"  ✓ Voice reference within limits, using as-is")
            with open(input_path, 'rb') as f:
                return f.read(), False
                
    except Exception as e:
        print(f"  ✗ Error processing voice reference: {e}")
        return None, False

