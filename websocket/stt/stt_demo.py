# live_stt_client.py
import asyncio
import websockets
import json
import base64
import logging
import os
import time
import queue
import threading
from dotenv import load_dotenv
from typing import Optional, Callable
import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    logger.warning("Sounddevice/soundfile not installed. Install with: pip install sounddevice soundfile")

class LiveSTTClient:
    def __init__(self, server_url: str, token: str):
        self.server_url = server_url
        self.token = token
        self.is_recording = False
        self.audio_queue = queue.Queue()
        self.samplerate = 16000  # Whisper expects 16kHz
        self.channels = 1
        self.audio_buffer = []
        self.timings = {}
        
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function for sounddevice stream"""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        if self.is_recording:
            # Convert to bytes and add to queue
            audio_data = indata.copy()
            self.audio_queue.put(audio_data.tobytes())
    
    async def record_audio(self, duration: float = 5.0) -> bytes:
        """
        Record audio from microphone
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            bytes: Recorded audio as WAV bytes
        """
        if not AUDIO_CAPTURE_AVAILABLE:
            raise ImportError("Please install sounddevice and soundfile: pip install sounddevice soundfile")
        
        logger.info(f"🎤 Recording audio for {duration} seconds...")
        logger.info("Speak now...")
        
        self.is_recording = True
        self.audio_buffer = []
        
        try:
            # Start recording
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                callback=self._audio_callback,
                dtype='float32'
            ):
                # Record for specified duration
                start_time = time.time()
                while time.time() - start_time < duration:
                    # Collect audio from queue
                    try:
                        audio_chunk = self.audio_queue.get(timeout=0.1)
                        self.audio_buffer.append(audio_chunk)
                    except queue.Empty:
                        continue
                    
                    # Show recording progress
                    elapsed = time.time() - start_time
                    if int(elapsed) != int(elapsed - 0.1):  # Update every second
                        logger.info(f"Recording... {elapsed:.1f}/{duration}s")
                
            self.is_recording = False
            
            # Combine all audio chunks
            if not self.audio_buffer:
                raise ValueError("No audio recorded")
            
            # Convert to numpy array
            audio_bytes = b''.join(self.audio_buffer)
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            
            # Convert to WAV bytes
            wav_io = io.BytesIO()
            sf.write(wav_io, audio_array, self.samplerate, format='WAV')
            wav_bytes = wav_io.getvalue()
            
            logger.info(f"✅ Recording complete: {len(wav_bytes)} bytes")
            return wav_bytes
            
        except Exception as e:
            self.is_recording = False
            logger.error(f"❌ Recording failed: {e}")
            raise
    
    async def record_and_transcribe(self, duration: float = 5.0) -> str:
        """
        Record audio and transcribe it immediately
        
        Args:
            duration: Recording duration in seconds
            
        Returns:
            str: Transcription text
        """
        # Record audio
        audio_bytes = await self.record_audio(duration)
        
        # Transcribe
        transcription = await self.transcribe_audio_bytes(audio_bytes)
        
        return transcription
    
    async def transcribe_audio_bytes(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes (already recorded)
        """
        start_time = time.time()
        
        # Encode to base64
        encode_start = time.time()
        audio_b64 = base64.b64encode(audio_bytes).decode('ascii')
        encode_time = time.time() - encode_start
        
        # Prepare request
        request = {
            "model_id": "whisper",
            "prompt": audio_b64,
            "prompt_id": int(time.time() * 1000)
        }
        
        logger.info(f"📊 Audio size: {len(audio_bytes):,} bytes")
        logger.info(f"⏱️  Encoding time: {encode_time:.3f}s")
        
        # Send to server
        network_start = time.time()
        async with websockets.connect(self.server_url) as websocket:
            # Send
            send_start = time.time()
            await websocket.send(json.dumps(request))
            send_time = time.time() - send_start
            
            # Receive
            receive_start = time.time()
            response = await websocket.recv()
            receive_time = time.time() - receive_start
        
        network_time = time.time() - network_start
        
        # Process response
        process_start = time.time()
        response_data = json.loads(response)
        process_time = time.time() - process_start
        
        total_time = time.time() - start_time
        
        if "error" in response_data:
            raise Exception(f"Server error: {response_data['error']}")
        
        if "text" in response_data:
            transcription = response_data["text"]
            
            # Log timing
            logger.info("\n" + "="*50)
            logger.info("LIVE TRANSCRIPTION COMPLETE")
            logger.info("="*50)
            logger.info(f"📝 Transcription: {transcription}")
            logger.info(f"⏱️  Total processing time: {total_time:.3f}s")
            logger.info(f"🌐 Network time: {network_time:.3f}s")
            logger.info("="*50)
            
            return transcription
        else:
            logger.error(f"Unexpected response: {response_data}")
            return str(response_data)
    
    async def continuous_listening(self, 
                                 callback: Optional[Callable[[str], None]] = None,
                                 silence_threshold: float = 0.01,
                                 min_silence_duration: float = 1.0):
        """
        Continuous listening mode - keeps recording and transcribing
        
        Args:
            callback: Function to call with each transcription
            silence_threshold: Audio level threshold for silence detection
            min_silence_duration: Minimum silence duration to trigger transcription
        """
        if not AUDIO_CAPTURE_AVAILABLE:
            raise ImportError("Please install sounddevice and soundfile")
        
        logger.info("🎤 Starting continuous listening mode...")
        logger.info("Press Ctrl+C to stop")
        logger.info(f"Silence threshold: {silence_threshold}")
        logger.info(f"Min silence duration: {min_silence_duration}s")
        
        try:
            while True:
                # Record until silence is detected
                audio_bytes = await self.record_until_silence(
                    silence_threshold=silence_threshold,
                    min_silence_duration=min_silence_duration
                )
                
                if len(audio_bytes) > 0:
                    # Transcribe
                    try:
                        transcription = await self.transcribe_audio_bytes(audio_bytes)
                        
                        # Call callback if provided
                        if callback:
                            callback(transcription)
                        else:
                            print(f"\n🤖 Assistant heard: {transcription}")
                            
                    except Exception as e:
                        logger.error(f"Transcription failed: {e}")
                
                # Small delay before next recording
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            logger.info("\n🛑 Continuous listening stopped")
        except Exception as e:
            logger.error(f"Continuous listening error: {e}")
    
    async def record_until_silence(self, 
                                  silence_threshold: float = 0.01,
                                  min_silence_duration: float = 1.0,
                                  max_duration: float = 30.0) -> bytes:
        """
        Record audio until silence is detected
        
        Args:
            silence_threshold: Audio level threshold for silence
            min_silence_duration: How long to wait in silence before stopping
            max_duration: Maximum recording duration
            
        Returns:
            bytes: Recorded audio
        """
        if not AUDIO_CAPTURE_AVAILABLE:
            raise ImportError("Please install sounddevice and soundfile")
        
        self.is_recording = True
        self.audio_buffer = []
        
        silence_start_time = None
        recording_start_time = time.time()
        
        try:
            with sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                callback=self._audio_callback,
                dtype='float32'
            ):
                while self.is_recording:
                    # Check for timeout
                    if time.time() - recording_start_time > max_duration:
                        logger.info("⏱️  Maximum recording duration reached")
                        break
                    
                    # Process audio chunks
                    try:
                        audio_chunk = self.audio_queue.get(timeout=0.1)
                        
                        # Convert to numpy array and check volume
                        audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
                        current_volume = np.mean(np.abs(audio_array))
                        
                        if current_volume < silence_threshold:
                            # Silence detected
                            if silence_start_time is None:
                                silence_start_time = time.time()
                                logger.debug("Silence detected...")
                            elif time.time() - silence_start_time > min_silence_duration:
                                # Silence long enough, stop recording
                                logger.info("🔇 Silence detected, stopping recording")
                                break
                        else:
                            # Sound detected, reset silence timer
                            silence_start_time = None
                            logger.debug(f"Sound level: {current_volume:.4f}")
                        
                        self.audio_buffer.append(audio_chunk)
                        
                    except queue.Empty:
                        continue
            
            self.is_recording = False
            
            # Combine audio
            if not self.audio_buffer:
                return b""
            
            audio_bytes = b''.join(self.audio_buffer)
            audio_array = np.frombuffer(audio_bytes, dtype=np.float32)
            
            # Convert to WAV
            wav_io = io.BytesIO()
            sf.write(wav_io, audio_array, self.samplerate, format='WAV')
            
            recording_duration = len(audio_array) / self.samplerate
            logger.info(f"📊 Recorded {recording_duration:.2f}s of audio")
            
            return wav_io.getvalue()
            
        except Exception as e:
            self.is_recording = False
            logger.error(f"Recording failed: {e}")
            raise
    
    def stop_recording(self):
        """Stop any ongoing recording"""
        self.is_recording = False


class VoiceCommandSTT(LiveSTTClient):
    """
    Enhanced STT client for voice commands
    """
    
    def __init__(self, server_url: str, token: str, wake_word: str = "hey assistant"):
        super().__init__(server_url, token)
        self.wake_word = wake_word.lower()
        self.is_awake = False
        self.command_history = []
    
    async def wait_for_wake_word(self):
        """
        Continuously listen for wake word
        """
        logger.info(f"👂 Listening for wake word: '{self.wake_word}'")
        
        def check_wake_word(transcription: str):
            if self.wake_word in transcription.lower():
                logger.info(f"🔔 Wake word detected!")
                self.is_awake = True
                return True
            return False
        
        # Use continuous listening with wake word check
        await self.continuous_listening(callback=check_wake_word)
    
    async def listen_for_command(self) -> str:
        """
        Listen for a voice command after wake word
        """
        logger.info("🎤 Listening for command...")
        
        # Record audio
        audio_bytes = await self.record_audio(duration=5.0)
        
        # Transcribe
        transcription = await self.transcribe_audio_bytes(audio_bytes)
        
        # Add to history
        self.command_history.append({
            "timestamp": time.time(),
            "command": transcription
        })
        
        return transcription
    
    async def voice_assistant_loop(self):
        """
        Complete voice assistant loop: Wake word → Command → Response
        """
        logger.info("🤖 Voice Assistant Starting...")
        
        while True:
            try:
                # Step 1: Wait for wake word
                logger.info("\n" + "="*50)
                logger.info("Waiting for wake word...")
                logger.info("="*50)
                
                # Simple wake word detection (in real app, use dedicated model)
                print(f"\nSay '{self.wake_word}' to activate...")
                
                # Record and check for wake word
                audio_bytes = await self.record_audio(duration=3.0)
                transcription = await self.transcribe_audio_bytes(audio_bytes)
                
                if self.wake_word in transcription.lower():
                    logger.info(f"✅ Wake word detected!")
                    
                    # Step 2: Listen for command
                    logger.info("\n" + "="*50)
                    logger.info("What can I help you with?")
                    logger.info("="*50)
                    print("Listening for command...")
                    
                    command_audio = await self.record_audio(duration=5.0)
                    command_text = await self.transcribe_audio_bytes(command_audio)
                    
                    logger.info(f"🎯 Command: {command_text}")
                    
                    # Here you would process the command with LLM
                    # For now, just echo
                    response = f"I heard you say: {command_text}"
                    print(f"\n🤖 Assistant: {response}")
                    
                    # Wait before listening again
                    await asyncio.sleep(1)
                    
                else:
                    logger.debug(f"Heard: {transcription} (not wake word)")
                    
            except KeyboardInterrupt:
                logger.info("\n👋 Voice assistant stopped")
                break
            except Exception as e:
                logger.error(f"Voice assistant error: {e}")
                await asyncio.sleep(1)


async def main():
    """Main demo function"""
    
    # Configuration
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        raise RuntimeError("SERVER_URL env var is required")

    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN env var is required")
    
    # Check audio dependencies
    if not AUDIO_CAPTURE_AVAILABLE:
        logger.error("❌ Audio capture dependencies not installed.")
        logger.error("Please install: pip install sounddevice soundfile numpy")
        return
    
    # Create client
    client = LiveSTTClient(server_url, token)
    
    print("\n" + "="*60)
    print("LIVE SPEECH-TO-TEXT DEMO")
    print("="*60)
    
    # Test modes
    print("\nChoose mode:")
    print("1. Single recording & transcribe (5 seconds)")
    print("2. Continuous listening")
    print("3. Voice assistant with wake word")
    print("4. Record until silence")
    
    try:
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            # Mode 1: Single recording
            print("\n🎤 Mode 1: Single Recording")
            print("Speak for 5 seconds after the countdown...")
            
            for i in range(3, 0, -1):
                print(f"Starting in {i}...")
                await asyncio.sleep(1)
            
            print("🎤 Recording...")
            transcription = await client.record_and_transcribe(duration=5.0)
            print(f"\n✅ Transcription: {transcription}")
            
        elif choice == "2":
            # Mode 2: Continuous listening
            print("\n🎤 Mode 2: Continuous Listening")
            print("Speak naturally. Press Ctrl+C to stop.")
            
            def print_transcription(text: str):
                print(f"\n📝 Heard: {text}")
            
            await client.continuous_listening(callback=print_transcription)
            
        elif choice == "3":
            # Mode 3: Voice assistant
            print("\n🤖 Mode 3: Voice Assistant")
            voice_assistant = VoiceCommandSTT(server_url, token, wake_word="hey assistant")
            await voice_assistant.voice_assistant_loop()
            
        elif choice == "4":
            # Mode 4: Record until silence
            print("\n🎤 Mode 4: Record Until Silence")
            print("Speak naturally. Recording stops after 1 second of silence.")
            print("Press Ctrl+C to cancel.")
            
            try:
                audio_bytes = await client.record_until_silence(
                    silence_threshold=0.02,
                    min_silence_duration=1.0,
                    max_duration=30.0
                )
                
                if len(audio_bytes) > 0:
                    print("🎯 Transcribing...")
                    transcription = await client.transcribe_audio_bytes(audio_bytes)
                    print(f"\n✅ Transcription: {transcription}")
                else:
                    print("❌ No audio recorded")
                    
            except KeyboardInterrupt:
                print("\n🛑 Recording cancelled")
                
        else:
            print("❌ Invalid choice")
            
    except KeyboardInterrupt:
        print("\n👋 Demo stopped by user")
    except Exception as e:
        logger.error(f"Demo error: {e}")


async def quick_test():
    """Quick test without menu"""
    server_url = os.getenv("SERVER_URL")
    token = os.getenv("TOKEN")
    
    if not AUDIO_CAPTURE_AVAILABLE:
        print("❌ Install dependencies first: pip install sounddevice soundfile numpy")
        return
    
    client = LiveSTTClient(server_url, token)
    
    print("🎤 Quick test - Recording 3 seconds of audio...")
    
    try:
        transcription = await client.record_and_transcribe(duration=3.0)
        print(f"\n✅ You said: {transcription}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    # Run with menu
    asyncio.run(main())
    
    # Or quick test
    # asyncio.run(quick_test())