"""
Memory Service

Orchestrates session and message memory, linking to CALL and REQUEST entities.
Manages conversation history, context retention, and session state.

This service:
- Manages conversation memory per session/call
- Links messages to CALL and REQUEST entities
- Provides context retrieval for dialog management
- Handles memory persistence and retrieval
"""

from typing import List, Dict, Optional
from datetime import datetime


class MemoryService:
    """
    Service for session/message orchestration and memory management
    
    Links conversation history to CALL and REQUEST entities in the system.
    """
    
    def __init__(self, max_messages: int = 10):
        """
        Initialize memory service
        
        Args:
            max_messages: Maximum number of messages to retain per session
        """
        self.max_messages = max_messages
        self.sessions: Dict[str, List[Dict]] = {}
    
    def add_message(
        self, 
        call_id: str, 
        request_id: str,
        role: str, 
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add message to session memory
        
        Links message to CALL (via call_id) and REQUEST (via request_id) entities.
        
        Args:
            call_id: ID of the CALL entity
            request_id: ID of the REQUEST entity
            role: Message role (user, assistant, system)
            content: Message content
            metadata: Optional metadata dictionary
        """
        if call_id not in self.sessions:
            self.sessions[call_id] = []
        
        message = {
            'request_id': request_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        self.sessions[call_id].append(message)
        
        # Trim to max_messages
        if len(self.sessions[call_id]) > self.max_messages:
            self.sessions[call_id] = self.sessions[call_id][-self.max_messages:]
    
    def get_session_memory(self, call_id: str) -> List[Dict]:
        """
        Get conversation memory for a session
        
        Args:
            call_id: ID of the CALL entity
            
        Returns:
            List of message dictionaries
        """
        return self.sessions.get(call_id, [])
    
    def get_recent_messages(self, call_id: str, n: int = 5) -> List[Dict]:
        """
        Get recent N messages from session
        
        Args:
            call_id: ID of the CALL entity
            n: Number of recent messages to retrieve
            
        Returns:
            List of recent message dictionaries
        """
        messages = self.get_session_memory(call_id)
        return messages[-n:] if len(messages) > n else messages
    
    def clear_session(self, call_id: str) -> None:
        """
        Clear memory for a session
        
        Args:
            call_id: ID of the CALL entity
        """
        if call_id in self.sessions:
            del self.sessions[call_id]
    
    def get_conversation_context(self, call_id: str) -> str:
        """
        Get formatted conversation context for LLM
        
        Args:
            call_id: ID of the CALL entity
            
        Returns:
            Formatted conversation history as string
        """
        messages = self.get_session_memory(call_id)
        context_parts = []
        
        for msg in messages:
            role = msg['role'].capitalize()
            content = msg['content']
            context_parts.append(f"{role}: {content}")
        
        return "\n".join(context_parts)

