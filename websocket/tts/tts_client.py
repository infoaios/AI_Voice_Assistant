# tts_client.py
import asyncio
import websockets
import json
import base64
import logging
import os
from typing import Optional
import soundfile as sf
import io
import sounddevice as sd  # Optional: for audio playback
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class TTSClient:
    """
    Text-to-Speech client for your XTTS server
    Works with server expecting: {"model_id": "xtts", "prompt": "text", "prompt_id": 123}
    """
    
    def __init__(self, server_url: str, token: str):
        """
        Initialize TTS client
        
        Args:
            server_url: WebSocket server URL (ws://localhost:8765)
            token: Authentication token (must match server's STATIC_TOKEN)
        """
        self.server_url = server_url
        self.token = token
        self.timeout = 30  # seconds
        self.prompt_counter = 1000  # Starting prompt ID
    
    def _get_next_prompt_id(self) -> int:
        """Generate unique prompt ID"""
        self.prompt_counter += 1
        return self.prompt_counter
    
    async def generate_speech(self, text: str, prompt_id: Optional[int] = None) -> bytes:
        """
        Generate speech from text and return raw audio bytes
        
        Args:
            text: Text to convert to speech
            prompt_id: Optional custom prompt ID (auto-generated if None)
            
        Returns:
            bytes: Raw WAV audio data
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        if prompt_id is None:
            prompt_id = self._get_next_prompt_id()
        
        logger.info(f"Generating speech for text: '{text[:50]}...' (prompt_id: {prompt_id})")
        
        # Prepare request matching your server's protocol
        request = {
            "model_id": "xtts",
            "prompt": text,  # TEXT goes in 'prompt' field for TTS
            "prompt_id": prompt_id
        }
        
        try:
            # Connect to server
            async with websockets.connect(
                self.server_url,
                ping_interval=10,
                ping_timeout=20,
                close_timeout=self.timeout
            ) as websocket:
                
                # Send request
                await websocket.send(json.dumps(request))
                logger.debug(f"Sent TTS request: {json.dumps(request)[:200]}...")
                
                # Receive response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Check for errors
                if "error" in response_data:
                    error_msg = response_data["error"]
                    logger.error(f"Server returned error: {error_msg}")
                    raise Exception(f"TTS generation failed: {error_msg}")
                
                if "audio_b64" not in response_data:
                    logger.error(f"Server response missing audio_b64: {response_data}")
                    raise Exception("Server response missing audio data")
                
                # Decode base64 audio
                audio_b64 = response_data["audio_b64"]
                audio_bytes = base64.b64decode(audio_b64)
                
                logger.info(f"✅ Speech generated successfully! Audio size: {len(audio_bytes)} bytes")
                return audio_bytes
                
        except websockets.exceptions.ConnectionClosedError as e:
            logger.error(f"Connection closed unexpectedly: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            raise
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise
    
    async def generate_and_save(self, text: str, output_path: str, prompt_id: Optional[int] = None) -> str:
        """
        Generate speech and save to WAV file
        
        Args:
            text: Text to convert to speech
            output_path: Path to save WAV file
            prompt_id: Optional custom prompt ID
            
        Returns:
            str: Path to saved audio file
        """
        # Generate audio bytes
        audio_bytes = await self.generate_speech(text, prompt_id)
        
        # Save to file
        try:
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            
            logger.info(f"✅ Audio saved to: {output_path}")
            
            # Verify file can be read
            try:
                data, samplerate = sf.read(io.BytesIO(audio_bytes))
                duration = len(data) / samplerate
                logger.info(f"Audio details: {samplerate}Hz, {duration:.2f}s, {len(data)} samples")
            except Exception as e:
                logger.warning(f"Could not analyze audio: {e}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to save audio: {e}")
            raise
    
    async def generate_and_play(self, text: str, prompt_id: Optional[int] = None):
        """
        Generate speech and play it immediately
        
        Args:
            text: Text to convert to speech
            prompt_id: Optional custom prompt ID
        """
        try:
            # Generate audio bytes
            audio_bytes = await self.generate_speech(text, prompt_id)
            
            # Read audio data
            data, samplerate = sf.read(io.BytesIO(audio_bytes))
            
            logger.info(f"Playing audio: {samplerate}Hz, {len(data)} samples")
            
            # Play audio
            sd.play(data, samplerate)
            sd.wait()  # Wait for playback to finish
            
            logger.info("✅ Audio playback completed")
            
        except ImportError:
            logger.warning("sounddevice not installed. Install with: pip install sounddevice")
            logger.info("Audio generated but not played")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            raise
    
    async def batch_generate(self, texts: list, output_dir: str = "tts_outputs"):
        """
        Generate speech for multiple texts
        
        Args:
            texts: List of texts to convert to speech
            output_dir: Directory to save audio files
            
        Returns:
            list: Paths to saved audio files
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        results = []
        
        for i, text in enumerate(texts, 1):
            try:
                logger.info(f"Processing text {i}/{len(texts)}: '{text[:50]}...'")
                
                # Generate and save
                output_path = os.path.join(output_dir, f"speech_{i:03d}.wav")
                saved_path = await self.generate_and_save(text, output_path)
                
                results.append({
                    "index": i,
                    "text": text,
                    "audio_file": saved_path
                })
                
            except Exception as e:
                logger.error(f"Failed to generate speech for text {i}: {e}")
                results.append({
                    "index": i,
                    "text": text,
                    "error": str(e)
                })
        
        logger.info(f"✅ Batch generation complete: {len([r for r in results if 'audio_file' in r])}/{len(texts)} successful")
        return results
    
    async def test_connection(self) -> bool:
        """Test if server is reachable"""
        try:
            async with websockets.connect(
                self.server_url,
                ping_interval=5,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                # Send test message (server should handle it or close)
                test_msg = {"model_id": "xtts", "prompt": "test", "prompt_id": 999}
                await websocket.send(json.dumps(test_msg))
                
                # Try to get response (server might not respond to invalid token)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    if "error" not in response_data:
                        return True
                except asyncio.TimeoutError:
                    # No response but connection succeeded
                    return True
                    
        except Exception as e:
            logger.debug(f"Connection test failed: {e}")
            return False


class VoiceAssistantTTS(TTSClient):
    """
    Enhanced TTS client with voice assistant features
    """
    
    def __init__(self, server_url: str, token: str, voice_settings: Optional[dict] = None):
        """
        Initialize voice assistant TTS
        
        Args:
            server_url: WebSocket server URL
            token: Authentication token
            voice_settings: Optional voice customization (if server supports it)
        """
        super().__init__(server_url, token)
        self.voice_settings = voice_settings or {
            "speed": 1.0,  # Speaking rate
            "emotion": "neutral",  # Could be happy, sad, excited, etc.
            "pitch": "medium"  # high, medium, low
        }
        
        # Conversation history
        self.conversation_history = []
    
    async def speak_response(self, text: str, save: bool = False) -> Optional[str]:
        """
        Generate and optionally play a response
        
        Args:
            text: Response text to speak
            save: Whether to save the audio file
            
        Returns:
            Optional[str]: Path to saved file if save=True
        """
        logger.info(f"🤖 Assistant: {text}")
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "assistant",
            "text": text,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        try:
            if save:
                # Save to file with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"assistant_response_{timestamp}.wav"
                saved_path = await self.generate_and_save(text, filename)
                return saved_path
            else:
                # Play immediately
                await self.generate_and_play(text)
                return None
                
        except Exception as e:
            logger.error(f"Failed to speak response: {e}")
            # Fallback: just print the text
            print(f"Assistant (text only): {text}")
            return None
    
    async def conversational_tts(self, user_input: str, llm_function=None):
        """
        Full conversational flow: User input → LLM processing → TTS response
        
        Args:
            user_input: User's text input
            llm_function: Optional function that takes text and returns response
                         If None, uses simple echo
        """
        # Add user input to history
        self.conversation_history.append({
            "role": "user",
            "text": user_input,
            "timestamp": asyncio.get_event_loop().time()
        })
        
        logger.info(f"👤 User: {user_input}")
        
        # Process with LLM (or echo)
        if llm_function:
            try:
                response_text = await llm_function(user_input)
            except Exception as e:
                logger.error(f"LLM processing failed: {e}")
                response_text = f"I couldn't process that request. Error: {e}"
        else:
            # Simple echo for testing
            response_text = f"You said: {user_input}"
        
        # Speak the response
        await self.speak_response(response_text, save=True)
    
    def get_conversation_summary(self) -> dict:
        """Get summary of conversation"""
        return {
            "total_messages": len(self.conversation_history),
            "user_messages": len([m for m in self.conversation_history if m["role"] == "user"]),
            "assistant_messages": len([m for m in self.conversation_history if m["role"] == "assistant"]),
            "history": self.conversation_history[-10:]  # Last 10 messages
        }


# Example usage and main function
async def main():
    """Example usage of TTS client"""
    
    # Configuration
    SERVER_URL = os.getenv("SERVER_URL", "ws://localhost:8765")
    TOKEN = os.getenv("TOKEN", "your-secret-token-here")
    
    if not TOKEN or TOKEN == "your-secret-token-here":
        logger.error("Please set TOKEN in .env file or edit this script")
        logger.error("Token must match STATIC_TOKEN in server's .env file")
        return
    
    # Create TTS client
    tts_client = TTSClient(SERVER_URL, TOKEN)
    
    # Test connection
    logger.info("Testing server connection...")
    is_connected = await tts_client.test_connection()
    
    if not is_connected:
        logger.error("❌ Cannot connect to server. Please check:")
        logger.error(f"1. Server URL: {SERVER_URL}")
        logger.error("2. Is the server running?")
        logger.error("3. Token matches server's STATIC_TOKEN")
        logger.error("4. Firewall/network settings")
        return
    
    logger.info("✅ Server connection successful!")
    
    print("\n" + "="*60)
    print("TEXT-TO-SPEECH DEMO")
    print("="*60)
    
    # Example 1: Simple TTS generation
    print("\n1. 📝 Simple TTS Generation")
    print("-"*40)
    
    test_text = "Hello, this is a test of the text to speech system."
    
    try:
        # Generate and save
        output_file = await tts_client.generate_and_save(
            text=test_text,
            output_path="test_output.wav"
        )
        print(f"✅ Generated: {output_file}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Example 2: Batch generation
    print("\n2. 🔄 Batch TTS Generation")
    print("-"*40)
    
    texts_to_speak = [
        "Welcome to our voice assistant system.",
        "The weather today is sunny with a high of 75 degrees.",
        "Your next meeting is at 2 PM in conference room B.",
        "Would you like me to set a reminder for that?",
        "Goodbye and have a great day!"
    ]
    
    try:
        results = await tts_client.batch_generate(
            texts=texts_to_speak,
            output_dir="batch_outputs"
        )
        print(f"✅ Generated {len([r for r in results if 'audio_file' in r])} audio files")
    except Exception as e:
        print(f"❌ Batch generation failed: {e}")
    
    # Example 3: Voice Assistant Demo
    print("\n3. 🤖 Voice Assistant Demo")
    print("-"*40)
    
    voice_assistant = VoiceAssistantTTS(SERVER_URL, TOKEN)
    
    # Simple conversation
    conversation = [
        "Hello, how are you today?",
        "What's the weather like?",
        "Tell me a fun fact",
        "Thank you, goodbye!"
    ]
    
    for i, user_message in enumerate(conversation, 1):
        print(f"\nConversation {i}/4")
        print(f"User: {user_message}")
        
        try:
            # For demo, using simple echo. In real usage, connect to LLM
            await voice_assistant.conversational_tts(user_message)
            print("✅ Assistant responded")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # Pause between messages
        if i < len(conversation):
            await asyncio.sleep(1)
    
    # Show conversation summary
    summary = voice_assistant.get_conversation_summary()
    print(f"\n📊 Conversation Summary: {summary['total_messages']} messages exchanged")
    
    # Example 4: Interactive mode
    print("\n4. 💬 Interactive Mode (Press Ctrl+C to exit)")
    print("-"*40)
    
    try:
        while True:
            user_input = input("\nEnter text to speak (or 'quit' to exit): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            try:
                # Play immediately
                await tts_client.generate_and_play(user_input)
            except ImportError:
                # If sounddevice not available, save instead
                filename = f"interactive_{len(os.listdir('.'))}.wav"
                await tts_client.generate_and_save(user_input, filename)
                print(f"Audio saved to: {filename}")
            except Exception as e:
                print(f"Error: {e}")
                
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"Interactive mode error: {e}")


async def quick_test():
    """Quick test function"""
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        raise RuntimeError("SERVER_URL env var is required")

    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN env var is required")


    SERVER_URL = server_url
    TOKEN = token  # From .env STATIC_TOKEN
    
    client = TTSClient(SERVER_URL, TOKEN)
    
    # Quick test
    try:
        audio_bytes = await client.generate_speech("Hello world")
        print(f"✅ Success! Generated {len(audio_bytes)} bytes of audio")
        
        # Save it
        with open("quick_test.wav", "wb") as f:
            f.write(audio_bytes)
        print("Saved to quick_test.wav")
        
    except Exception as e:
        print(f"❌ Failed: {e}")


if __name__ == "__main__":
    # Run the main demo
    asyncio.run(main())
    
    # Or for quick test:
    # asyncio.run(quick_test())