import asyncio
import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple

import websockets


def get_audio_duration(input_path: str) -> Optional[float]:
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except Exception:
        return None


def trim_to_5_seconds(input_path: str, output_path: str) -> bool:
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-t", "5",
            "-ar", "16000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            "-map_metadata", "-1",
            output_path,
        ]
        print("  ↳ Trimming voice reference to 5 seconds...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ Voice reference trimmed: {output_path}")
            return True
        print(f"  ✗ FFmpeg error: {result.stderr}")
        return False
    except FileNotFoundError:
        print("  ✗ Error: ffmpeg not found. Please install ffmpeg.")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def process_audio_file_for_voice_reference(input_path: str) -> Tuple[Optional[bytes], bool]:
    """
    If >500KB or >10s, trim to 5 seconds.
    Returns: (audio_bytes, trimmed_flag)
    """
    try:
        file_size_bytes = Path(input_path).stat().st_size
        file_size_kb = file_size_bytes / 1024
        duration = get_audio_duration(input_path) or 0.0

        print(f"  ↳ Voice reference file: {file_size_kb:.1f}KB, {duration:.1f}s")

        needs_trimming = file_size_bytes > (500 * 1024) or (duration > 10.0)

        if not needs_trimming:
            print("  ✓ Voice reference within limits, using as-is")
            return Path(input_path).read_bytes(), False

        print(f"  ⚠️  Voice reference needs trimming (size: {file_size_kb:.1f}KB, duration: {duration:.1f}s)")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_output = tmp.name

        success = trim_to_5_seconds(input_path, temp_output)
        if not success:
            print("  ⚠️  Trimming failed, using original file (may cause issues)")
            return Path(input_path).read_bytes(), False

        audio_bytes = Path(temp_output).read_bytes()
        try:
            os.unlink(temp_output)
        except Exception:
            pass

        trimmed_kb = len(audio_bytes) / 1024
        print(f"  ✓ Trimmed to: {trimmed_kb:.1f}KB")
        return audio_bytes, True

    except Exception as e:
        print(f"  ✗ Error processing voice reference: {e}")
        return None, False


class XTTSPersistentClient:
    """Persistent WebSocket client for XTTS with auto-reconnect + optional voice cloning"""

    def __init__(self, server_url: str, voice_clone_path: Optional[str] = None):
        self.server_url = server_url
        self.voice_clone_path = voice_clone_path

        self.ws = None
        self.lock = asyncio.Lock()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0

        self.voice_reference_b64 = None
        self.voice_reference_loaded = False
        self.voice_reference_trimmed = False

        if self.voice_clone_path:
            self._preload_voice_reference()

    def _preload_voice_reference(self):
        try:
            voice_path = Path(self.voice_clone_path)
            if not voice_path.exists():
                print(f"⚠️ Voice reference file not found: {self.voice_clone_path}")
                return

            print(f"📁 Loading voice reference: {self.voice_clone_path}")
            audio_bytes, trimmed = process_audio_file_for_voice_reference(self.voice_clone_path)
            if audio_bytes is None:
                print("❌ Failed to load voice reference")
                return

            self.voice_reference_trimmed = trimmed
            self.voice_reference_b64 = base64.b64encode(audio_bytes).decode("ascii")
            self.voice_reference_loaded = True

            b64_size_kb = len(self.voice_reference_b64) / 1024
            audio_size_kb = len(audio_bytes) / 1024
            status = "(trimmed to 5s)" if trimmed else "(original)"
            print(f"✅ Voice reference loaded {status} ({audio_size_kb:.1f}KB audio, {b64_size_kb:.1f}KB base64)")

        except Exception as e:
            print(f"❌ Error loading voice reference: {e}")

    async def connect(self) -> bool:
        async with self.lock:
            if self.connected and self.ws:
                try:
                    if self.ws.state == websockets.protocol.State.OPEN:
                        return True
                except Exception:
                    self.connected = False
                    self.ws = None

            try:
                print("🔗 Connecting to XTTS WebSocket...")
                self.ws = await websockets.connect(
                    self.server_url,
                    ping_interval=10,
                    ping_timeout=20,
                    close_timeout=30,
                    max_size=50 * 1024 * 1024,
                    compression=None,
                )
                self.connected = True
                self.reconnect_attempts = 0
                print("✅ XTTS WebSocket connected")
                return True

            except Exception as e:
                self.connected = False
                self.ws = None
                self.reconnect_attempts += 1

                if self.reconnect_attempts <= self.max_reconnect_attempts:
                    print(
                        f"⚠️ XTTS WebSocket connection failed "
                        f"(attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}): {e}"
                    )
                    await asyncio.sleep(self.reconnect_delay * self.reconnect_attempts)
                    return await self.connect()

                print("❌ Failed to connect to XTTS WebSocket after max attempts")
                return False

    async def ensure_connection(self) -> bool:
        if not self.connected or not self.ws:
            return await self.connect()

        try:
            if self.ws.state != websockets.protocol.State.OPEN:
                print(f"⚠️ XTTS WebSocket state={self.ws.state}, reconnecting...")
                self.connected = False
                self.ws = None
                return await self.connect()
            return True
        except Exception as e:
            print(f"⚠️ XTTS WebSocket check failed: {e}, reconnecting...")
            self.connected = False
            self.ws = None
            return await self.connect()

    async def tts(self, text: str, prompt_id: int) -> Tuple[Optional[bytes], float]:
        start_time = time.time()

        # English-only cleaning
        text_clean = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', " ", text)
        text_clean = re.sub(r"\s+", " ", text_clean).strip()
        if not text_clean:
            text_clean = "Sorry, I didn't get that. Could you please repeat in English?"

        print(f"🎤 TTS Input (cleaned): {text_clean}")

        for attempt in range(3):
            try:
                if not await self.ensure_connection():
                    print("❌ XTTS connection failed, cannot send request")
                    return None, time.time() - start_time

                request = {
                    "model_id": "xtts",
                    "prompt": text_clean,
                    "prompt_id": prompt_id,
                    "language": "en",
                }

                if self.voice_reference_loaded:
                    request["voice_cloning"] = True
                    request["voice_reference"] = self.voice_reference_b64
                    voice_status = "trimmed to 5s" if self.voice_reference_trimmed else "original"
                    print(f"🎤 Voice cloning enabled ({voice_status})")

                await asyncio.wait_for(self.ws.send(json.dumps(request)), timeout=5.0)
                response = await asyncio.wait_for(self.ws.recv(), timeout=30.0)

                response_data = json.loads(response)
                elapsed_time = time.time() - start_time

                if "error" in response_data:
                    print(f"⚠️ XTTS error: {response_data['error']}")
                    if attempt < 2:
                        await asyncio.sleep(1.0)
                        continue
                    return None, elapsed_time

                if "audio_b64" in response_data:
                    return base64.b64decode(response_data["audio_b64"]), elapsed_time

                return None, elapsed_time

            except websockets.exceptions.ConnectionClosed as e:
                print(f"⚠️ XTTS connection closed: {e}, reconnecting...")
                self.connected = False
                self.ws = None
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time

            except asyncio.TimeoutError:
                print(f"⚠️ XTTS timeout on attempt {attempt + 1}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time

            except Exception as e:
                print(f"⚠️ XTTS error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time

        return None, time.time() - start_time

    async def close(self):
        async with self.lock:
            if self.ws:
                try:
                    await self.ws.close()
                    self.connected = False
                    print("🔌 XTTS WebSocket closed")
                except Exception:
                    pass
                finally:
                    self.ws = None
