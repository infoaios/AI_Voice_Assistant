import asyncio
import websockets
import json
import logging
import os
from dotenv import load_dotenv
import time
from abc import ABC, abstractmethod

# Set up basic logging for better traceability
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env if present
load_dotenv()


class SocketService(ABC):
    """
    Base class for WebSocket services that interact with AI models.
    This class contains all common functionality for WebSocket connections,
    retry logic, and request handling.
    """

    def __init__(self, server_url: str, token: str, model_id: str):
        """
        Initialize the SocketService with the server URL and authentication token.

        Args:
            server_url (str): WebSocket server URL.
            token (str): Authentication token for the server.
            model_id (str): The model identifier (whisper, llama, xtts).
        """
        self.server_url = server_url
        self.token = token
        self.model_id = model_id
        self.prompt_id = 123  # Initial prompt_id value

    async def _send_request(self, data: str) -> str:
        """
        Common method to send a WebSocket request and receive the response from the server.
        This method handles retry logic and connection management.

        Args:
            data (str): The input data (text, prompt, or audio path).

        Returns:
            str: The response from the server.
        """
        retries = 3  # Number of retries for reconnecting
        delay = 2  # Delay between retries (in seconds)

        for attempt in range(retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{retries} to connect to WebSocket for {self.model_id.upper()}...")
                async with websockets.connect(self.server_url) as websocket:
                    # Prepare the request data
                    request_data = self._prepare_request_data(data)
                    logger.debug(f"Sending {self.model_id.upper()} request: {request_data}")
                    
                    # Send the request data
                    await websocket.send(request_data)

                    # Await the server's response
                    response = await websocket.recv()
                    logger.info(f"{self.model_id.upper()} Response: {response}")
                    return response
            except Exception as e:
                logger.error(f"WebSocket error in {self.model_id.upper()} request: {e}, attempt {attempt + 1}/{retries}")
                if attempt < retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise
        # If all attempts fail
        raise Exception(f"Failed to connect to WebSocket after {retries} attempts.")

    @abstractmethod
    def _prepare_request_data(self, data: str) -> str:
        """
        Prepare the request data based on the model type.
        This method must be implemented by each child class.

        Args:
            data (str): The input data (text, prompt, or audio path).

        Returns:
            str: The JSON string representing the request data.
        """
        pass

    def _increment_prompt_id(self):
        """Increment prompt_id after each request."""
        self.prompt_id += 1


class STTService(SocketService):
    """
    A class to interact with Whisper model (STT - Speech-to-Text) via WebSocket.
    This class manages connections to the server for STT operations independently.
    """

    def __init__(self, server_url: str, token: str):
        """
        Initialize the STTService with the server URL and authentication token.

        Args:
            server_url (str): WebSocket server URL.
            token (str): Authentication token for the server.
        """
        super().__init__(server_url, token, "whisper")

    def _prepare_request_data(self, audio_file_path: str) -> str:
        """
        Prepare the request data for Whisper model.

        Args:
            audio_file_path (str): The audio file path.

        Returns:
            str: The JSON string representing the request data.
        """
        if not os.path.exists(audio_file_path):  # Validate the audio file path
            raise ValueError(f"Audio file path '{audio_file_path}' does not exist or is invalid.")
        
        return json.dumps({
            "token": self.token,
            "model_id": self.model_id,
            "text": audio_file_path,  # For Whisper, data is audio path
            "prompt_id": self.prompt_id
        })

    async def stt_request(self, audio_file_path: str) -> str:
        """
        Function to handle STT (Speech-to-Text) request for Whisper model.
        
        Args:
            audio_file_path (str): Path to the audio file to transcribe.
            
        Returns:
            str: The transcribed text response from the server.
        """
        logger.info("Sending STT request to Whisper model...")
        response = await self._send_request(audio_file_path)
        self._increment_prompt_id()
        return response


class TTTService(SocketService):
    """
    A class to interact with Llama model (TTT - Text-to-Text) via WebSocket.
    This class manages connections to the server for TTT operations independently.
    """

    def __init__(self, server_url: str, token: str):
        """
        Initialize the TTTService with the server URL and authentication token.

        Args:
            server_url (str): WebSocket server URL.
            token (str): Authentication token for the server.
        """
        super().__init__(server_url, token, "llama")

    def _prepare_request_data(self, prompt: str) -> str:
        """
        Prepare the request data for Llama model.

        Args:
            prompt (str): The text prompt.

        Returns:
            str: The JSON string representing the request data.
        """
        return json.dumps({
            "token": self.token,
            "model_id": self.model_id,
            "prompt": prompt,  # For Llama, data is a text prompt
            "prompt_id": self.prompt_id
        })

    async def ttt_request(self, prompt: str) -> str:
        """
        Function to handle TTT (Text-to-Text) request for Llama model.
        
        Args:
            prompt (str): The text prompt to send to the model.
            
        Returns:
            str: The text response from the server.
        """
        logger.info("Sending TTT request to Llama model...")
        response = await self._send_request(prompt)
        self._increment_prompt_id()
        return response


class TTSService(SocketService):
    """
    A class to interact with XTTS model (TTS - Text-to-Speech) via WebSocket.
    This class manages connections to the server for TTS operations independently.
    """

    def __init__(self, server_url: str, token: str):
        """
        Initialize the TTSService with the server URL and authentication token.

        Args:
            server_url (str): WebSocket server URL.
            token (str): Authentication token for the server.
        """
        super().__init__(server_url, token, "xtts")

    def _prepare_request_data(self, text: str) -> str:
        """
        Prepare the request data for XTTS model.

        Args:
            text (str): The text to convert to speech.

        Returns:
            str: The JSON string representing the request data.
        """
        return json.dumps({
            "token": self.token,
            "model_id": self.model_id,
            "text": text,  # For XTTS, data is text to convert to speech
            "prompt_id": self.prompt_id
        })

    async def tts_request(self, text: str) -> str:
        """
        Function to handle TTS (Text-to-Speech) request for XTTS model.
        
        Args:
            text (str): The text to convert to speech.
            
        Returns:
            str: The audio response from the server.
        """
        logger.info("Sending TTS request to XTTS model...")
        response = await self._send_request(text)
        self._increment_prompt_id()
        return response


# Main execution: Example usage
async def main():
    """
    Example usage of the separate service classes (STTService, TTTService, TTSService).
    Each service can be used independently.
    """
    # Read server URL and token from environment
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        raise RuntimeError("SERVER_URL env var is required")

    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN env var is required")

    # Initialize each service independently
    # stt_service = STTService(server_url=server_url, token=token)
    ttt_service = TTTService(server_url=server_url, token=token)
    # tts_service = TTSService(server_url=server_url, token=token)

    # Example input for each model request
    # audio_file_path = "data/saved_voices/refe2.wav"  # Replace with actual audio file path for STT
    prompt = "Hello, how are you?"  # Replace with actual Llama prompt
    # text = "Convert this text to speech"  # Replace with actual text for TTS

    # Call each service independently
    # stt_response = await stt_service.stt_request(audio_file_path)
    # logger.info(f"STT Response: {stt_response}")
    
    ttt_response = await ttt_service.ttt_request(prompt)
    logger.info(f"TTT Response: {ttt_response}")
    
    # tts_response = await tts_service.tts_request(text)
    # logger.info(f"TTS Response: {tts_response}")


if __name__ == "__main__":
    asyncio.run(main())
