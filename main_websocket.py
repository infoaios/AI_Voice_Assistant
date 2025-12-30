import asyncio
import base64
import io
import os
import queue
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from dotenv import load_dotenv

import sounddevice as sd
import soundfile as sf

from websocket.stt.stt_websocket import STTPersistentClient
from websocket.ttt.llm_websocket import RestaurantLLM
from websocket.tts.tts_websocket import XTTSPersistentClient
from core.order_manager import EnhancedOrderManager
from core.restaurant_rag import RestaurantRAGSystem


# ---- Keep your existing restaurant logic here ----
# - REST_DATA loading
# - IntentRouter + RAG
# - EnhancedOrderManager
# - RestaurantRAGSystem
# Paste them as-is from your current file.
# ------------------------------------------------

load_dotenv()


SYSTEM_PROMPT = (
    "You are AI Voice assistant, a friendly restaurant receptionist. "
    "Speak ONLY in English. Keep responses very short (1 sentence max). "
    "Be warm, confident, helpful but always professional. "
    "CRITICAL LANGUAGE RULES - YOU MUST FOLLOW THESE: "
    "1. Speak ONLY in English. Never use any other language. "
    "2. If the user speaks in another language, politely ask them to speak in English. "
    "3. Your vocabulary must be restaurant-specific English only. "
    "4. Keep sentences simple and clear. "
    "CRITICAL RULES - YOU MUST FOLLOW THESE: "
    "1. NEVER describe how to make any food, dish, or beverage "
    "2. NEVER list ingredients, recipes, or cooking methods "
    "3. NEVER invent, create, or make up ANY dish names - whether real or fake "
    "4. NEVER describe dishes that are available in our menu - let the system handle that "
    "5. NEVER describe dishes that are NOT available in our menu "
    "6. NEVER include labels like 'System:', 'User:', 'Assistant:', or any text in brackets "
    "7. NEVER make up information about dishes "
    "8. NEVER suggest menu items or create options for the user "
    "9. If asked about ANY food, dishes, ingredients, recipes, or prices, ONLY say: 'Let me check that for you' "
    "10. If asked how to make something, say: 'Sorry, I don't have recipe information' "
    "Your role is ONLY for: greetings, confirmations, general conversation, asking to repeat, ending politely. "
    "If the user asks about food/menu/price/order details, respond exactly: 'Let me check that for you'"
)


class RestaurantVoiceAssistant:
    def __init__(self, server_url: str, token: str, voice_clone_path: Optional[str] = None):
        self.server_url = server_url
        self.token = token
        self.voice_clone_path = voice_clone_path

        # Split clients
        self.tts_client = XTTSPersistentClient(server_url, voice_clone_path)
        self.stt_client = STTPersistentClient(server_url)
        self.llm = RestaurantLLM(server_url, token, SYSTEM_PROMPT)

        # Your existing components (keep these from your original code)
        self.order_manager = EnhancedOrderManager()
        self.rag_system = RestaurantRAGSystem(self.order_manager)

        # Audio capture setup
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.samplerate = 16000

        self.next_prompt_id = 1000
        self.first_interaction = True

    def get_next_prompt_id(self) -> int:
        pid = self.next_prompt_id
        self.next_prompt_id += 1
        return pid

    def _audio_callback(self, indata, frames, time_info, status):
        if self.is_recording:
            self.audio_queue.put(indata.copy().tobytes())

    async def record_until_silence(self) -> Optional[bytes]:
        self.is_recording = True
        audio_chunks = []
        silence_start = None
        has_spoken = False

        with sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            callback=self._audio_callback,
            dtype="float32",
        ):
            start_time = time.time()
            while self.is_recording:
                try:
                    chunk = self.audio_queue.get(timeout=0.1)
                    audio_array = np.frombuffer(chunk, dtype=np.float32)
                    volume = np.mean(np.abs(audio_array))

                    if volume > 0.02:
                        has_spoken = True

                    if volume < 0.02:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > 1.0:
                            self.is_recording = False
                            break
                    else:
                        silence_start = None

                    audio_chunks.append(chunk)

                except queue.Empty:
                    if time.time() - start_time > 30:
                        self.is_recording = False
                        break

        if not audio_chunks or not has_spoken:
            return None

        audio_bytes = b"".join(audio_chunks)
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)

        wav_io = io.BytesIO()
        sf.write(wav_io, audio_array, self.samplerate, format="WAV")
        return wav_io.getvalue()

    async def play_audio(self, audio_bytes: bytes) -> bool:
        try:
            data, samplerate = sf.read(io.BytesIO(audio_bytes))
            sd.play(data, samplerate)
            sd.wait()
            return True
        except Exception as e:
            print(f"Audio playback error: {e}")
            return False

    async def run(self):
        print("🔗 Establishing persistent connections...")
        await self.tts_client.connect()
        await self.stt_client.connect()
        print("✅ LLM ready (connects on first use)")

        try:
            while True:
                prompt_id = self.get_next_prompt_id()

                print("\n🎤 Listening... (Speak now)")
                audio = await self.record_until_silence()
                if not audio:
                    print("No speech detected")
                    continue

                audio_b64 = base64.b64encode(audio).decode("ascii")
                transcription, stt_time = await self.stt_client.transcribe(audio_b64, prompt_id)
                if not transcription:
                    reply = "I'm sorry, I couldn't understand that. Could you please speak in English?"
                    audio_out, _ = await self.tts_client.tts(reply, prompt_id)
                    if audio_out:
                        await self.play_audio(audio_out)
                    continue

                # RAG first
                reply, should_use_llm = self.rag_system.process_with_rag(transcription)

                llm_time = 0.0
                if reply is None and should_use_llm:
                    llm_reply, llm_time = await self.llm.generate_response(transcription, prompt_id)
                    reply = llm_reply or "How can I help you today?"

                if self.first_interaction and reply:
                    # keep your current first greeting logic here if you want
                    self.first_interaction = False

                print(f"🤖 Assistant: {reply}")
                audio_out, tts_time = await self.tts_client.tts(reply, prompt_id)
                if audio_out:
                    await self.play_audio(audio_out)

        except KeyboardInterrupt:
            print("\n👋 Restaurant assistant stopped")
        finally:
            await self.cleanup()

    async def cleanup(self):
        await self.tts_client.close()
        await self.stt_client.close()
        await self.llm.close()
        print("✅ All connections closed")


async def main():
    server_url = os.getenv("SERVER_URL")
    token = os.getenv("TOKEN")
    voice_clone_path = os.getenv("VOICE_CLONE_PATH")

    if not server_url:
        raise RuntimeError("SERVER_URL is required in .env")
    if not token:
        raise RuntimeError("TOKEN is required in .env")

    if voice_clone_path and not Path(voice_clone_path).exists():
        print(f"⚠️ Voice reference file not found: {voice_clone_path}")
        voice_clone_path = None

    assistant = RestaurantVoiceAssistant(server_url, token, voice_clone_path)
    await assistant.run()


if __name__ == "__main__":
    asyncio.run(main())
