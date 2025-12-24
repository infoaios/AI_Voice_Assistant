import asyncio
import websockets
import json
import logging
import os
from dotenv import load_dotenv

# Set up basic logging for better traceability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env if present
load_dotenv()


class SocketService:
    """
    A class to interact with various AI models (Whisper, Llama, XTTS) via WebSocket.
    This class manages connections to the server and provides separate methods for STT, TTT, and TTS.
    """
    
    def __init__(self, server_url: str, token: str):
        """
        Initialize the SocketService with the server URL and authentication token.

        Args:
            server_url (str): WebSocket server URL.
            token (str): Authentication token for the server.
        """
        self.server_url = server_url
        self.token = token

    async def stt_request(self, audio_file_path: str) -> str:
        """
        Send a request to the Whisper model for speech-to-text (STT).

        Args:
            audio_file_path (str): Path to the audio file for STT.

        Returns:
            str: The response from the server containing the transcribed text.

        Raises:
            Exception: If WebSocket connection fails.
        """
        logger.info("Sending STT request to Whisper model...")
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                request_data = json.dumps({
                    "token": self.token,
                    "model_id": "whisper",
                    "text": audio_file_path  # For Whisper, data is audio path or raw audio
                })
                await websocket.send(request_data)
                
                # Await the server's response
                response = await websocket.recv()
                logger.info(f"STT (Whisper) response: {response}")
                return response
        except Exception as e:
            logger.error(f"Error in STT request: {e}")
            raise

    async def ttt_request(self, prompt: str) -> str:
        """
        Send a request to the Llama model for text-to-text (TTT/LLM).

        Args:
            prompt (str): The text prompt to generate a response from Llama.

        Returns:
            str: The response from the server containing the generated text.

        Raises:
            Exception: If WebSocket connection fails.
        """
        logger.info("Sending TTT request to Llama model...")
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                request_data = json.dumps({
                    "token": self.token,
                    "model_id": "llama",
                    "prompt": prompt  # For Llama, data is a text prompt
                })
                await websocket.send(request_data)
                
                # Await the server's response
                response = await websocket.recv()
                logger.info(f"TTT (Llama) response: {response}")
                return response
        except Exception as e:
            logger.error(f"Error in TTT request: {e}")
            raise

    async def tts_request(self, text: str) -> str:
        """
        Send a request to the XTTS model for text-to-speech (TTS) conversion.

        Args:
            text (str): The text to convert into speech.

        Returns:
            str: The response from the server containing the generated audio or audio path.

        Raises:
            Exception: If WebSocket connection fails.
        """
        logger.info("Sending TTS request to XTTS model...")
        
        try:
            async with websockets.connect(self.server_url) as websocket:
                request_data = json.dumps({
                    "token": self.token,
                    "model_id": "xtts",
                    "text": text  # For XTTS, data is text to convert to speech
                })
                await websocket.send(request_data)
                
                # Await the server's response
                response = await websocket.recv()
                logger.info(f"TTS (XTTS) response: {response}")
                return response
        except Exception as e:
            logger.error(f"Error in TTS request: {e}")
            raise


# Main execution: Example usage
async def main():
    """
    Example usage of the SocketService class.
    """
    # Read server URL and token from environment
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        raise RuntimeError("SERVER_URL env var is required")

    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN env var is required")

    # Initialize the service with server_url and token
    socket_service = SocketService(server_url=server_url, token=token)

    # Example input for each model request
    audio_file_path = "path_to_audio_file.wav"  # Replace with actual audio file path for STT
    prompt = "Hello, how are you?"  # Replace with actual Llama prompt
    text = "Convert this text to speech"  # Replace with actual text for TTS

    # Call each method separately
    await socket_service.stt_request(audio_file_path)
    await socket_service.ttt_request(prompt)
    await socket_service.tts_request(text)


if __name__ == "__main__":
    asyncio.run(main())
