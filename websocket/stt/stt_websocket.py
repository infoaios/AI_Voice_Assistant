import asyncio
import json
import re
import time
from typing import Optional, Tuple

import websockets


class STTPersistentClient:
    """Persistent WebSocket client for STT (Whisper) with auto-reconnect"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.ws = None
        self.lock = asyncio.Lock()
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0

    async def connect(self) -> bool:
        """Establish WebSocket connection or reconnect if needed"""
        async with self.lock:
            if self.connected and self.ws:
                try:
                    if self.ws.state == websockets.protocol.State.OPEN:
                        return True
                except Exception:
                    self.connected = False
                    self.ws = None

            try:
                print("🔗 Connecting to STT WebSocket...")
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
                print("✅ STT WebSocket connected")
                return True

            except Exception as e:
                self.connected = False
                self.ws = None
                self.reconnect_attempts += 1

                if self.reconnect_attempts <= self.max_reconnect_attempts:
                    print(
                        f"⚠️ STT WebSocket connection failed "
                        f"(attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}): {e}"
                    )
                    await asyncio.sleep(self.reconnect_delay * self.reconnect_attempts)
                    return await self.connect()

                print("❌ Failed to connect to STT WebSocket after max attempts")
                return False

    async def ensure_connection(self) -> bool:
        """Ensure we have a valid connection"""
        if not self.connected or not self.ws:
            return await self.connect()

        try:
            if self.ws.state != websockets.protocol.State.OPEN:
                print(f"⚠️ STT WebSocket state={self.ws.state}, reconnecting...")
                self.connected = False
                self.ws = None
                return await self.connect()
            return True
        except Exception as e:
            print(f"⚠️ STT WebSocket check failed: {e}, reconnecting...")
            self.connected = False
            self.ws = None
            return await self.connect()

    async def transcribe(self, audio_b64: str, prompt_id: int) -> Tuple[Optional[str], float]:
        """Transcribe audio using persistent WebSocket - ENGLISH ONLY"""
        start_time = time.time()

        for attempt in range(3):
            try:
                if not await self.ensure_connection():
                    print("❌ STT connection failed, cannot send request")
                    return None, time.time() - start_time

                request = {
                    "model_id": "whisper",
                    "prompt": audio_b64,
                    "prompt_id": prompt_id,
                    "language": "en",
                }

                await asyncio.wait_for(self.ws.send(json.dumps(request)), timeout=5.0)

                response = await asyncio.wait_for(self.ws.recv(), timeout=15.0)
                response_data = json.loads(response)
                elapsed_time = time.time() - start_time

                if "error" in response_data:
                    print(f"⚠️ STT error: {response_data['error']}")
                    if attempt < 2:
                        await asyncio.sleep(1.0)
                        continue
                    return None, elapsed_time

                if "text" in response_data:
                    transcription = response_data["text"]
                    print(f"📝 You said: {transcription}")

                    # keep only basic English characters + punctuation
                    transcription = re.sub(r'[^a-zA-Z0-9\s.,!?\'"-]', "", transcription).strip()
                    if not transcription and attempt < 2:
                        print("⚠️ Transcription empty after cleaning, retrying...")
                        await asyncio.sleep(1.0)
                        continue

                    return transcription, elapsed_time

                return None, elapsed_time

            except websockets.exceptions.ConnectionClosed as e:
                print(f"⚠️ STT connection closed: {e}, reconnecting...")
                self.connected = False
                self.ws = None
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time

            except asyncio.TimeoutError:
                print(f"⚠️ STT timeout on attempt {attempt + 1}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time

            except Exception as e:
                print(f"⚠️ STT error on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(1.0)
                    continue
                return None, time.time() - start_time

        return None, time.time() - start_time

    async def close(self):
        """Close the WebSocket connection"""
        async with self.lock:
            if self.ws:
                try:
                    await self.ws.close()
                    self.connected = False
                    print("🔌 STT WebSocket closed")
                except Exception:
                    pass
                finally:
                    self.ws = None
