"""
Rate Limiter Service

Enforces rate limits and writes RateLimitRecord entities.
Applies rate limiting policies to prevent abuse and manage resource usage.

This service:
- Tracks request rates per user/session
- Writes RateLimitRecord entities when limits are exceeded
- Applies configurable rate limiting policies
- Provides rate limit checking and enforcement
"""

from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from global_data import DEFAULT_RATE_LIMIT_PER_MINUTE, DEFAULT_RATE_LIMIT_PER_HOUR


class RateLimiter:
    """
    Service for rate limit enforcement
    
    Tracks request rates and writes RateLimitRecord entities when limits
    are exceeded. Applies configurable policies.
    """
    
    def __init__(
        self,
        requests_per_minute: int = DEFAULT_RATE_LIMIT_PER_MINUTE,
        requests_per_hour: int = DEFAULT_RATE_LIMIT_PER_HOUR
    ):
        """
        Initialize rate limiter
        
        Args:
            requests_per_minute: Maximum requests per minute
            requests_per_hour: Maximum requests per hour
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        
        # Track requests: {identifier: [(timestamp, request_id), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
        self.rate_limit_records: list = []
    
    def check_rate_limit(
        self, 
        identifier: str, 
        request_id: str
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if request exceeds rate limits
        
        Writes RateLimitRecord entity if limit is exceeded.
        
        Args:
            identifier: User/session identifier
            request_id: ID of the REQUEST entity
            
        Returns:
            Tuple of (is_allowed, rate_limit_record)
            - is_allowed: True if request is allowed
            - rate_limit_record: RateLimitRecord dict if limit exceeded, None otherwise
        """
        now = datetime.now()
        
        # Clean old entries (older than 1 hour)
        cutoff = now - timedelta(hours=1)
        self.request_history[identifier] = [
            (ts, req_id) for ts, req_id in self.request_history[identifier]
            if ts > cutoff
        ]
        
        # Add current request
        self.request_history[identifier].append((now, request_id))
        
        # Check per-minute limit
        minute_cutoff = now - timedelta(minutes=1)
        recent_minute = [
            (ts, req_id) for ts, req_id in self.request_history[identifier]
            if ts > minute_cutoff
        ]
        
        if len(recent_minute) > self.requests_per_minute:
            record = self._create_rate_limit_record(
                identifier, request_id, 'per_minute', len(recent_minute)
            )
            self.rate_limit_records.append(record)
            return False, record
        
        # Check per-hour limit
        hour_cutoff = now - timedelta(hours=1)
        recent_hour = [
            (ts, req_id) for ts, req_id in self.request_history[identifier]
            if ts > hour_cutoff
        ]
        
        if len(recent_hour) > self.requests_per_hour:
            record = self._create_rate_limit_record(
                identifier, request_id, 'per_hour', len(recent_hour)
            )
            self.rate_limit_records.append(record)
            return False, record
        
        return True, None
    
    def _create_rate_limit_record(
        self, 
        identifier: str, 
        request_id: str, 
        limit_type: str, 
        current_count: int
    ) -> Dict:
        """
        Create RateLimitRecord entity
        
        Args:
            identifier: User/session identifier
            request_id: ID of the REQUEST entity
            limit_type: Type of limit exceeded ('per_minute' or 'per_hour')
            current_count: Current request count
            
        Returns:
            RateLimitRecord dictionary
        """
        return {
            'request_id': request_id,
            'identifier': identifier,
            'limit_type': limit_type,
            'current_count': current_count,
            'limit': self.requests_per_minute if limit_type == 'per_minute' else self.requests_per_hour,
            'timestamp': datetime.now().isoformat(),
            'action': 'blocked'
        }
    
    def get_rate_limit_records(self, identifier: Optional[str] = None) -> list:
        """
        Get rate limit records
        
        Args:
            identifier: Optional identifier to filter records
            
        Returns:
            List of RateLimitRecord dictionaries
        """
        if identifier:
            return [
                record for record in self.rate_limit_records
                if record.get('identifier') == identifier
            ]
        return self.rate_limit_records

