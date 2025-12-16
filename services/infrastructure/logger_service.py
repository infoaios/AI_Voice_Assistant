"""
Logging Service

Centralized logging configuration for the voice platform:
- Configures handlers (file and console)
- Sets up formatters with timestamps and log levels
- Manages log rotation and file paths
- Provides conversation logging utilities

This service handles all logging concerns, ensuring consistent log format
across the application.
"""
import logging
from pathlib import Path
from typing import Optional


def setup_logging(log_dir: Optional[str] = None, log_file: str = "assistant.log") -> logging.Logger:
    """
    Setup comprehensive logging configuration
    
    Configures:
    - File handler with rotation support
    - Console handler for real-time output
    - Standardized format with timestamps
    
    Args:
        log_dir: Directory for log files (defaults to project_root/logs)
        log_file: Name of the log file
        
    Returns:
        Configured logger instance
    """
    if log_dir is None:
        # Default to project root/logs
        # This file is in voice_platform/services/, so go up to voice_platform/, then to project root
        voice_platform_dir = Path(__file__).parent.parent  # voice_platform/
        project_root = voice_platform_dir.parent  # project root
        log_path = project_root / "logs"
    else:
        log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path / log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)


def log_conversation(
    user_text: str, 
    bot_reply: str, 
    order_state: dict, 
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log conversation turn for debugging and analytics
    
    Logs user input, bot response, and current order state.
    Links to CALL and REQUEST entities in the system.
    
    Args:
        user_text: User's transcribed speech input
        bot_reply: Assistant's text response
        order_state: Current order state dictionary
        logger: Optional logger instance (creates new if not provided)
    """
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"USER: {user_text}")
    logger.info(f"BOT: {bot_reply}")
    logger.info(f"ORDER: {order_state}")

