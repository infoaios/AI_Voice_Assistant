"""
TTT Service (Text-to-Text) with Simplified Latency Tracking
"""

import asyncio
import websockets
import json
import logging
import os
import time
from datetime import timedelta
from dotenv import load_dotenv
from typing import Optional, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class TTTService:
    """
    Text-to-Text service with latency tracking.
    """
    
    def __init__(self, server_url: str, token: str):
        self.server_url = server_url
        self.token = token
        self.model_id = "llama"
        self.prompt_id = 1000
        self.websocket = None
        self.timeout = 30
        self.max_retries = 3
        
    def _get_next_prompt_id(self) -> int:
        self.prompt_id += 1
        return self.prompt_id
    
    async def generate_text(self, prompt: str) -> tuple[str, dict]:
        """
        Generate text from prompt and return response with timing metrics.
        
        Args:
            prompt: Text prompt
            
        Returns:
            tuple: (response_text, timing_metrics)
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")
        
        prompt_id = self._get_next_prompt_id()
        logger.info(f"Generating text for prompt: '{prompt[:50]}...' (ID: {prompt_id})")
        
        # Start timing
        timing = {
            "start_time": time.time(),
            "stages": {}
        }
        
        # Prepare request
        request = {
            "token": self.token,
            "model_id": self.model_id,
            "prompt": prompt,
            "prompt_id": prompt_id
        }
        
        timing["stages"]["request_prepared"] = time.time() - timing["start_time"]
        
        try:
            # Connect to server
            connect_start = time.time()
            async with websockets.connect(
                self.server_url,
                ping_interval=10,
                ping_timeout=20,
                close_timeout=self.timeout
            ) as websocket:
                
                timing["stages"]["connected"] = time.time() - timing["start_time"]
                
                # Send request
                await websocket.send(json.dumps(request))
                timing["stages"]["request_sent"] = time.time() - timing["start_time"]
                
                logger.debug(f"Sent TTT request: {json.dumps(request)[:200]}...")
                
                # Receive response
                response = await websocket.recv()
                timing["stages"]["response_received"] = time.time() - timing["start_time"]
                
                response_data = json.loads(response)
                
                # Check for errors
                if "error" in response_data:
                    error_msg = response_data["error"]
                    logger.error(f"Server returned error: {error_msg}")
                    raise Exception(f"Text generation failed: {error_msg}")
                
                # Extract response text
                response_text = response_data.get("response", "")
                if not response_text:
                    response_text = response_data.get("text", "")
                
                if not response_text:
                    logger.error(f"Server response missing text: {response_data}")
                    raise Exception("Server response missing text data")
                
                # Calculate final timing
                total_time = time.time() - timing["start_time"]
                timing["stages"]["complete"] = total_time
                timing["total_time"] = total_time
                
                # Calculate text statistics
                char_count = len(response_text)
                word_count = len(response_text.split())
                timing["text_stats"] = {
                    "characters": char_count,
                    "words": word_count,
                    "chars_per_sec": char_count / total_time if total_time > 0 else 0,
                    "words_per_sec": word_count / total_time if total_time > 0 else 0
                }
                
                # Extract server timing if available
                if "timing" in response_data:
                    timing["server_timing"] = response_data["timing"]
                
                logger.info(f"✅ Text generated successfully! Response: {word_count} words, {char_count} chars")
                
                return response_text, timing
                
        except Exception as e:
            timing["stages"]["error"] = time.time() - timing["start_time"]
            timing["total_time"] = time.time() - timing["start_time"]
            logger.error(f"Text generation failed: {e}")
            raise
    
    def print_timing_report(self, timing: dict, prompt: str, success: bool = True):
        """
        Print formatted timing report.
        """
        print(f"\n{'='*70}")
        status = "TTT Request" if success else "TTT Request FAILED"
        print(f"⏱️  TIMING REPORT: {status}: '{prompt[:30]}...'")
        print(f"{'='*70}")
        
        # Sort stages by time
        sorted_stages = sorted(timing["stages"].items(), key=lambda x: x[1])
        
        for stage, stage_time in sorted_stages:
            print(f"  {stage:<25} : {stage_time:>8.3f}s")
        
        total = timing["total_time"]
        print(f"{'-'*70}")
        print(f"  {'TOTAL TIME':<25} : {total:>8.3f}s  ({str(timedelta(seconds=total))[2:10]})")
        
        # Show text statistics if available
        if "text_stats" in timing and success:
            stats = timing["text_stats"]
            print(f"\n  {'TEXT STATISTICS':<25}")
            print(f"  {'-'*45}")
            print(f"  Response length: {stats['characters']} chars, {stats['words']} words")
            print(f"  Processing speed: {stats['chars_per_sec']:.1f} chars/sec, {stats['words_per_sec']:.1f} words/sec")
        
        # Show server timing if available
        if "server_timing" in timing:
            print(f"\n  {'SERVER TIMING':<25}")
            print(f"  {'-'*45}")
            for key, value in timing["server_timing"].items():
                if isinstance(value, (int, float)):
                    print(f"  {key:<25} : {value:>8.3f}s")
        
        print(f"{'='*70}\n")
    
    async def single_request(self, prompt: str):
        """
        Make a single TTT request with timing report.
        """
        print(f"\n{'='*60}")
        print(f"📝 TTT SINGLE REQUEST")
        print(f"{'='*60}")
        print(f"Prompt: '{prompt}'")
        print(f"{'-'*60}")
        
        try:
            response, timing = await self.generate_text(prompt)
            self.print_timing_report(timing, prompt, success=True)
            print(f"🤖 Response: {response}")
            return response, timing
            
        except Exception as e:
            print(f"❌ Error: {e}")
            # If we have partial timing from before the error
            if 'timing' in locals():
                self.print_timing_report(timing, prompt, success=False)
            raise
    
    async def test_connection(self) -> tuple[bool, float]:
        """Test server connection and measure latency"""
        start_time = time.time()
        try:
            async with websockets.connect(
                self.server_url,
                ping_interval=5,
                ping_timeout=10,
                close_timeout=10
            ) as websocket:
                latency = time.time() - start_time
                return True, latency
        except Exception as e:
            latency = time.time() - start_time
            logger.debug(f"Connection test failed: {e}")
            return False, latency


async def main():
    """
    Main function to test TTT service with timing.
    """
    # Configuration
    SERVER_URL = os.getenv("SERVER_URL", "ws://localhost:8765")
    TOKEN = os.getenv("TOKEN", "your-secret-token-here")
    
    if not TOKEN or TOKEN == "your-secret-token-here":
        logger.error("Please set TOKEN in .env file")
        return
    
    # Create TTT service
    ttt = TTTService(SERVER_URL, TOKEN)
    
    print(f"\n{'='*60}")
    print("🤖 TTT SERVICE WITH LATENCY TRACKING")
    print(f"{'='*60}")
    
    # Test connection
    print("\n🔌 Testing server connection...")
    is_connected, latency = await ttt.test_connection()
    
    if not is_connected:
        print("❌ Cannot connect to server")
        return
    
    print(f"✅ Server connection successful! Latency: {latency:.3f}s")
    
    # Get prompt from user
    print(f"\n{'='*60}")
    prompt = input("Enter your prompt (or press Enter for default): ").strip()
    
    if not prompt:
        prompt = "Explain artificial intelligence in simple terms."
        print(f"Using default prompt: '{prompt}'")
    
    # Make request
    try:
        response, timing = await ttt.single_request(prompt)
        
        # Calculate and display additional metrics
        total_time = timing["total_time"]
        if "text_stats" in timing:
            stats = timing["text_stats"]
            print(f"\n📊 PERFORMANCE SUMMARY:")
            print(f"  • Total time: {total_time:.3f}s")
            print(f"  • Response: {stats['words']} words, {stats['characters']} characters")
            print(f"  • Speed: {stats['words_per_sec']:.1f} words/sec")
            
            # Performance rating
            if stats['words_per_sec'] > 20:
                rating = "⚡ Excellent"
            elif stats['words_per_sec'] > 10:
                rating = "✅ Good"
            elif stats['words_per_sec'] > 5:
                rating = "⚠️  Acceptable"
            else:
                rating = "❌ Slow"
            
            print(f"  • Rating: {rating}")
        
    except Exception as e:
        print(f"\n❌ Request failed: {e}")


async def quick_test():
    """Quick test function"""
    server_url = os.getenv("SERVER_URL")
    if not server_url:
        raise RuntimeError("SERVER_URL env var is required")

    token = os.getenv("TOKEN")
    if not token:
        raise RuntimeError("TOKEN env var is required")

    SERVER_URL = server_url
    TOKEN = token
    
    client = TTTService(SERVER_URL, TOKEN)
    
    # Quick test
    try:
        response, timing = await client.generate_text("Hello, how are you?")
        print(f"✅ Success! Response: {response[:100]}...")
        client.print_timing_report(timing, "Hello, how are you?", success=True)
        
    except Exception as e:
        print(f"❌ Failed: {e}")


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
    
    # Or for quick test:
    # asyncio.run(quick_test())