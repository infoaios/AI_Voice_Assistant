"""
Helper Service

Utility functions for common operations:
- ID generation (UUIDs, timestamps)
- Timestamp formatting and parsing
- Error handling helpers
- JSON serialization/deserialization utilities

This service provides shared utility functions used across the application.
"""

import uuid
import json
import time
from datetime import datetime
from typing import Any, Optional, Dict
from pathlib import Path


class HelperService:
    """
    Service providing utility functions for IDs, timestamps, errors, and JSON
    
    Centralizes common helper functions to avoid duplication across services.
    """
    
    @staticmethod
    def generate_id(prefix: Optional[str] = None) -> str:
        """
        Generate unique ID
        
        Args:
            prefix: Optional prefix for the ID (e.g., 'CALL', 'REQ')
            
        Returns:
            Unique identifier string
        """
        unique_id = str(uuid.uuid4()).replace('-', '')[:12]
        if prefix:
            return f"{prefix}{unique_id.upper()}"
        return unique_id.upper()
    
    @staticmethod
    def generate_call_id() -> str:
        """Generate CALL entity ID"""
        return HelperService.generate_id('CALL')
    
    @staticmethod
    def generate_request_id() -> str:
        """Generate REQUEST entity ID"""
        return HelperService.generate_id('REQ')
    
    @staticmethod
    def get_timestamp() -> str:
        """
        Get current timestamp in ISO format
        
        Returns:
            ISO formatted timestamp string
        """
        return datetime.now().isoformat()
    
    @staticmethod
    def get_timestamp_unix() -> float:
        """
        Get current Unix timestamp
        
        Returns:
            Unix timestamp as float
        """
        return time.time()
    
    @staticmethod
    def format_timestamp(timestamp: float, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format Unix timestamp to string
        
        Args:
            timestamp: Unix timestamp
            format_str: Format string (default: ISO-like)
            
        Returns:
            Formatted timestamp string
        """
        return datetime.fromtimestamp(timestamp).strftime(format_str)
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> datetime:
        """
        Parse timestamp string to datetime object
        
        Args:
            timestamp_str: ISO formatted timestamp string
            
        Returns:
            Datetime object
        """
        return datetime.fromisoformat(timestamp_str)
    
    @staticmethod
    def safe_json_loads(json_str: str, default: Any = None) -> Any:
        """
        Safely parse JSON string
        
        Args:
            json_str: JSON string to parse
            default: Default value if parsing fails
            
        Returns:
            Parsed JSON object or default value
        """
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError):
            return default
    
    @staticmethod
    def safe_json_dumps(obj: Any, default: str = "{}") -> str:
        """
        Safely serialize object to JSON string
        
        Args:
            obj: Object to serialize
            default: Default JSON string if serialization fails
            
        Returns:
            JSON string or default value
        """
        try:
            return json.dumps(obj, default=str)
        except (TypeError, ValueError):
            return default
    
    @staticmethod
    def load_json_file(file_path: Path, default: Dict = None) -> Dict:
        """
        Load JSON from file
        
        Args:
            file_path: Path to JSON file
            default: Default value if file doesn't exist or parsing fails
            
        Returns:
            Dictionary from JSON file or default value
        """
        if default is None:
            default = {}
        
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default
        except (json.JSONDecodeError, IOError):
            return default
    
    @staticmethod
    def save_json_file(file_path: Path, data: Dict) -> bool:
        """
        Save dictionary to JSON file
        
        Args:
            file_path: Path to save JSON file
            data: Dictionary to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except (IOError, TypeError):
            return False
    
    @staticmethod
    def create_error_response(message: str, error_code: str = "ERROR", details: Optional[Dict] = None) -> Dict:
        """
        Create standardized error response dictionary
        
        Args:
            message: Error message
            error_code: Error code string
            details: Optional additional error details
            
        Returns:
            Error response dictionary
        """
        response = {
            'error': True,
            'error_code': error_code,
            'message': message,
            'timestamp': HelperService.get_timestamp()
        }
        
        if details:
            response['details'] = details
        
        return response
    
    @staticmethod
    def create_success_response(data: Any, message: Optional[str] = None) -> Dict:
        """
        Create standardized success response dictionary
        
        Args:
            data: Response data
            message: Optional success message
            
        Returns:
            Success response dictionary
        """
        response = {
            'success': True,
            'data': data,
            'timestamp': HelperService.get_timestamp()
        }
        
        if message:
            response['message'] = message
        
        return response

