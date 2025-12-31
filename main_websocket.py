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
import logging
import sounddevice as sd
import soundfile as sf
from utility.voice_reference_utils import process_audio_file_for_voice_reference
from websocket.stt.stt_websocket import STTPersistentClient
from websocket.ttt.llm_websocket import RestaurantLLM
from websocket.tts.tts_websocket import XTTSPersistentClient
from core.order_manager import EnhancedOrderManager
from core.restaurant_rag import RestaurantRAGSystem
from core.restaurant_data import REST_DATA  # ✅ REQUIRED
import tempfile

# Setup minimal logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

try:
    import sounddevice as sd
    import soundfile as sf
    import io
    AUDIO_CAPTURE_AVAILABLE = True
except ImportError:
    AUDIO_CAPTURE_AVAILABLE = False
    logger.error("❌ Install: pip install sounddevice soundfile numpy")
    exit(1)

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

# def prepare_processed_voice_clone_path(original_path: str) -> Optional[str]:
#     """
#     Uses utility.voice_reference_utils to trim/compress voice reference if needed,
#     writes processed bytes to a temp wav, returns that temp path.
#     """
#     audio_bytes, trimmed = process_audio_file_for_voice_reference(original_path)
#     if not audio_bytes:
#         return None

#     tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
#     tmp.write(audio_bytes)
#     tmp.flush()
#     tmp.close()

#     print(f"✅ Using processed voice reference ({'trimmed' if trimmed else 'original'}): {tmp.name}")
#     return tmp.name

class RestaurantVoiceAssistant:
    """Complete Restaurant Voice Assistant with All Persistent Connections"""
    
    def __init__(self, server_url: str, token: str, voice_clone_path: str = None):
        self.server_url = server_url
        self.token = token
        self.voice_clone_path = voice_clone_path

        # # ✅ If voice cloning is enabled, preprocess it into a temp wav
        # self.voice_clone_path = None
        # self._voice_tmp_path = None
        # if voice_clone_path and Path(voice_clone_path).exists():
        #     processed = prepare_processed_voice_clone_path(voice_clone_path)
        #     if processed:
        #         self.voice_clone_path = processed
        #         self._voice_tmp_path = processed
        
        # Initialize ALL persistent clients
        self.xtts_client = XTTSPersistentClient(server_url, voice_clone_path)
        self.stt_client = STTPersistentClient(server_url)
        self.llm_client = RestaurantLLM(server_url, token, SYSTEM_PROMPT)  # ✅ FIXED  # Updated
        
        # Initialize other components
        self.order_manager = EnhancedOrderManager()
        self.rag_system = RestaurantRAGSystem(self.order_manager)
        
        # Recording setup
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.samplerate = 16000
        
        # Session tracking
        self.session_count = 0
        self.next_prompt_id = 1000
        
        # Conversation context
        self.first_interaction = True
    
    def get_next_prompt_id(self) -> int:
        """Get next prompt ID for session"""
        current_id = self.next_prompt_id
        self.next_prompt_id += 1
        return current_id
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Audio input callback"""
        if self.is_recording:
            self.audio_queue.put(indata.copy().tobytes())
    
    async def record_until_silence(self) -> Optional[bytes]:
        """Record audio until 1 second of silence"""
        if not AUDIO_CAPTURE_AVAILABLE:
            raise ImportError("Install: pip install sounddevice soundfile numpy")
        
        self.is_recording = True
        audio_chunks = []
        silence_start = None
        has_spoken = False
        
        with sd.InputStream(samplerate=self.samplerate, channels=1, 
                          callback=self._audio_callback, dtype='float32'):
            
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
        
        audio_bytes = b''.join(audio_chunks)
        audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
        
        wav_io = io.BytesIO()
        sf.write(wav_io, audio_array, self.samplerate, format='WAV')
        
        return wav_io.getvalue()
    
    async def stt_transcribe(self, audio_bytes: bytes, prompt_id: int) -> Tuple[Optional[str], float]:
        """STT: Convert speech to text using persistent WebSocket"""
        # Convert audio to base64
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        
        # Use the persistent STT client
        return await self.stt_client.transcribe(audio_b64, prompt_id)
    
    async def tts_speak(self, text: str, prompt_id: int) -> Tuple[Optional[bytes], float]:
        """TTS: Convert text to speech using persistent WebSocket"""
        # Use the persistent XTTS client
        return await self.xtts_client.tts(text, prompt_id)
    
    async def play_audio(self, audio_bytes: bytes):
        """Play audio without saving to file"""
        try:
            data, samplerate = sf.read(io.BytesIO(audio_bytes))
            sd.play(data, samplerate)
            sd.wait()
            return True
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            return False
    
    def display_latency_summary(self, prompt_id: int, stt_time: float, rag_time: float, 
                              llm_time: float, tts_time: float, total_time: float, 
                              intent: str, used_llm: bool):
        """Display enhanced latency summary with intent info"""
        brain_time = rag_time + llm_time
        
        summary = f"[Latency Summary Prompt ID: {prompt_id}]"
        print(summary)
        print(f"  Intent: {intent} | Used LLM: {used_llm}")
        print(f"  STT: {stt_time:.2f}s | Brain: {brain_time:.2f}s (JSON={rag_time:.2f}s, LLM={llm_time:.2f}s) | TTS: {tts_time:.2f}s")
        print(f"  TOTAL: {total_time:.2f}s\n")
    
    async def single_conversation_session(self):
        """Complete session: Listen → Intent Route → RAG/LLM → Speak"""
        self.session_count += 1
        prompt_id = self.get_next_prompt_id()
        
        # Step 1: Record audio
        print("\n🎤 Listening... (Speak now)")
        audio = await self.record_until_silence()
        
        if not audio:
            print("No speech detected")
            return
        
        # Step 2: STT (Transcribe)
        transcription, stt_time = await self.stt_transcribe(audio, prompt_id)
        
        if not transcription:
            # Check if transcription failed due to non-English
            print("⚠️ Transcription failed or empty")
            # Use LLM to respond appropriately
            reply = "I'm sorry, I couldn't understand that. Could you please speak in English?"
            audio_response, tts_time = await self.tts_speak(reply, prompt_id)
            if audio_response:
                await self.play_audio(audio_response)
            return
        
        # Step 3: RAG Processing with Intent Routing
        rag_start_time = time.time()
        reply, should_use_llm = self.rag_system.process_with_rag(transcription)
        rag_time = time.time() - rag_start_time
        
        llm_time = 0.0
        used_llm = False
        detected_intent = "RAG_HANDLED"
        
        # Get detected intent from conversation history
        if self.rag_system.conversation_history:
            last_entry = self.rag_system.conversation_history[-1]
            detected_intent = last_entry.get("intent", "unknown")
        
        # Step 4: LLM Processing (only if RAG didn't handle it)
        if reply is None and should_use_llm:
            llm_response, llm_time = await self.llm_client.generate_response(transcription, prompt_id)
            if llm_response:
                reply = llm_response
                used_llm = True
                detected_intent = "LLM_FALLBACK"
            else:
                reply = "How can I help you today?"
        
        # Add restaurant greeting on first interaction
        if self.first_interaction and reply:
            rest = REST_DATA.get("restaurant", {})
            name = rest.get("name", "our restaurant")
            addr = rest.get("address", "our location")
            # Don't add greeting if it's already a greeting response
            if not reply.startswith("Hello") and not reply.startswith("Welcome"):
                reply = f"Welcome to {name}!"
                # reply = f"Welcome to {name}! We are located at {addr}. {reply}"
            self.first_interaction = False
        
        # Print assistant response
        if reply:
            print(f"🤖 Assistant: {reply}")
        
        # Step 5: TTS (Speak)
        audio_response, tts_time = await self.tts_speak(reply, prompt_id)
        
        if audio_response:
            await self.play_audio(audio_response)
        
        # Calculate total time
        total_time = stt_time + rag_time + llm_time + tts_time
        
        # Display enhanced latency summary
        self.display_latency_summary(prompt_id, stt_time, rag_time, llm_time, tts_time, 
                                    total_time, detected_intent, used_llm)
    
    async def run_voice_assistant(self):
        """Main voice assistant loop"""
        print("\n" + "="*60)
        print("🍽️  RESTAURANT VOICE ASSISTANT v5.0 (All Persistent Connections)")
        print("="*60)
        print("✅ Features: Single/Multiple Item Ordering | Add/Update/Delete")
        print("✅ Order Memory | Finalization with JSON Saving | Billing")
        print("✅ Persistent WebSocket: XTTS ✅ | STT ✅ | LLM ✅")
        print("🛑 Press Ctrl+C to exit")
        print("="*60)
        
        try:
            # Initial connection for all services
            print("🔗 Establishing all persistent connections...")
            
            # Connect to XTTS
            xtts_connected = await self.xtts_client.connect()
            
            # Connect to STT
            stt_connected = await self.stt_client.connect()
            
            # Connect to LLM (through the LLM client)
            llm_connected = True  # Will connect on first use
            
            if xtts_connected:
                print("✅ Persistent XTTS connection established")
            else:
                print("⚠️ Failed to establish XTTS connection")
            
            if stt_connected:
                print("✅ Persistent STT connection established")
            else:
                print("⚠️ Failed to establish STT connection")
            
            print("✅ LLM ready (will connect on first use)")
            
            while True:
                await self.single_conversation_session()
                
        except KeyboardInterrupt:
            print("\n👋 Restaurant assistant stopped")
            
            # Show final order status before exit
            if not self.order_manager.is_empty():
                print(f"\n📋 Current Order Status:")
                print(f"   Items: {len(self.order_manager.lines)}")
                print(f"   Total: {self.order_manager.subtotal():.0f} rupees")
                print("⚠️  Order not finalized - will be lost on exit")
        except Exception as e:
            print(f"\n❌ Assistant error: {e}")
            logger.exception("Fatal error in voice assistant")
        finally:
            # Always cleanup connections
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources and close all connections"""
        # Close XTTS connection
        if hasattr(self, 'xtts_client'):
            await self.xtts_client.close()
        
        # Close STT connection
        if hasattr(self, 'stt_client'):
            await self.stt_client.close()
        
        # Close LLM connection if using persistent LLM
        if hasattr(self, 'llm_client') and hasattr(self.llm_client, 'llm_client'):
            await self.llm_client.llm_client.close()
        
        print("✅ All connections closed")

async def main():
    """Main function"""
    
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        print("❌ SERVER_URL environment variable is required")
        print("Create a .env file with:")
        print("SERVER_URL=ws://localhost:8765")
        print("TOKEN=your-secret-token")
        return
    
    token = os.getenv("TOKEN")
    if not token:
        print("❌ TOKEN environment variable is required")
        return
    
    # Voice cloning path (optional)
    voice_clone_path = os.getenv("VOICE_CLONE_PATH")
    
    # Check if voice file exists
    if voice_clone_path:
        if Path(voice_clone_path).exists():
            print(f"📁 Found voice reference file: {voice_clone_path}")
            print("ℹ️  Large files (>500KB) will be automatically trimmed to 5 seconds")
        else:
            print(f"⚠️  Voice reference file not found: {voice_clone_path}")
            voice_clone_path = None
    else:
        print("ℹ️  Voice cloning not enabled (no path provided)")

    # Create and run assistant
    assistant = RestaurantVoiceAssistant(server_url, token, voice_clone_path)
    try:
        # Run assistant
        await assistant.run_voice_assistant()
    except KeyboardInterrupt:
        print("\n👋 Restaurant assistant stopped")
    except Exception as e:
        print(f"\n❌ Assistant error: {e}")
        logger.exception("Fatal error in voice assistant")
    finally:
        # Always cleanup connections
        await assistant.cleanup()


if __name__ == "__main__":
    asyncio.run(main())