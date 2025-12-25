import asyncio
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
import json
import logging
import os
from dotenv import load_dotenv
import time

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

    async def _send_request(self, model_id: str, data: str) -> str:
        """
        Common method to send a WebSocket request and receive the response from the server.

        Args:
            model_id (str): The model identifier (whisper, llama, xtts).
            data (str): The input data (text, prompt, or audio path).

        Returns:
            str: The response from the server.
        """
        retries = 3  # Number of retries for reconnecting
        delay = 2  # Delay between retries (in seconds)
        
        for attempt in range(retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{retries} to connect to WebSocket...")
                async with websockets.connect(self.server_url) as websocket:
                    # Send a basic "ping" to the server to keep the connection alive
                    await websocket.ping()

                    # Prepare the request data
                    request_data = self._prepare_request_data(model_id, data)
                    logger.debug(f"Sending request to {model_id}: {request_data}")
                    
                    # Send the request data
                    await websocket.send(request_data)

                    # Await the server's response
                    response = await websocket.recv()
                    logger.info(f"Response from {model_id}: {response}")
                    return response
            except (ConnectionClosedOK, ConnectionClosedError) as e:
                logger.error(f"WebSocket closed unexpectedly: {e}, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
            except Exception as e:
                logger.error(f"Error in {model_id} request: {e}")
                raise
        # If all attempts fail
        raise Exception(f"Failed to connect to WebSocket after {retries} attempts.")

    def _prepare_request_data(self, model_id: str, data: str) -> str:
        """
        Prepare the request data based on the model type (whisper, llama, xtts).

        Args:
            model_id (str): The model identifier.
            data (str): The input data (text, prompt, or audio path).

        Returns:
            str: The JSON string representing the request data.
        """
        if model_id == "whisper":
            return json.dumps({
                "token": self.token,
                "model_id": model_id,
                "text": data  # For Whisper, data is audio path or raw audio
            })
        elif model_id == "llama":
            return json.dumps({
                "token": self.token,
                "model_id": model_id,
                "prompt": data  # For Llama, data is a text prompt
            })
        elif model_id == "xtts":
            return json.dumps({
                "token": self.token,
                "model_id": model_id,
                "text": data  # For XTTS, data is text to convert to speech
            })
        else:
            logger.error(f"Invalid model_id: {model_id}")
            raise ValueError(f"Invalid model_id: {model_id}")

    async def stt_request(self, audio_file_path: str) -> str:
        """Function to handle STT (Speech-to-Text) request for Whisper model."""
        logger.info("Sending STT request to Whisper model...")
        return await self._send_request("whisper", audio_file_path)

    async def ttt_request(self, prompt: str) -> str:
        """Function to handle TTT (Text-to-Text) request for Llama model."""
        logger.info("Sending TTT request to Llama model...")
        return await self._send_request("llama", prompt)

    async def tts_request(self, text: str) -> str:
        """Function to handle TTS (Text-to-Speech) request for XTTS model."""
        logger.info("Sending TTS request to XTTS model...")
        return await self._send_request("xtts", text)


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
    audio_file_path = "data/saved_voices/refe2.wav"  # Replace with actual audio file path for STT
    prompt = "Hello, how are you?"  # Replace with actual Llama prompt
    text = "Convert this text to speech"  # Replace with actual text for TTS

    # Call each method separately
    await socket_service.stt_request(audio_file_path)
    await socket_service.ttt_request(prompt)
    await socket_service.tts_request(text)


if __name__ == "__main__":
    asyncio.run(main())
