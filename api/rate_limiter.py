# rate_limiter.py
"""
Rate limiting middleware to prevent API abuse
Tracks requests per user/IP and enforces rate limits
"""

from functools import wraps
from flask import request, g
from datetime import datetime, timedelta
from collections import deque
import threading

# Thread-safe storage for request tracking
_request_history = {}
_lock = threading.RLock()


class RateLimiter:
    """
    Rate limiter that tracks requests per identifier (user ID or IP)
    Uses sliding window algorithm for accurate rate limiting
    """
    
    def __init__(self, requests=100, window_seconds=60):
        """
        Initialize rate limiter
        
        Args:
            requests: Number of requests allowed per window
            window_seconds: Time window in seconds
        """
        self.requests_limit = requests
        self.window_seconds = window_seconds
    
    def is_allowed(self, identifier):
        """
        Check if request is allowed for identifier
        
        Args:
            identifier: User ID or IP address string
        
        Returns:
            Boolean: True if request allowed, False if rate limited
        """
        with _lock:
            now = datetime.utcnow()
            
            # Initialize history for identifier if needed
            if identifier not in _request_history:
                _request_history[identifier] = deque()
            
            request_timestamps = _request_history[identifier]
            
            # Remove old requests outside the window
            window_start = now - timedelta(seconds=self.window_seconds)
            while request_timestamps and request_timestamps[0] < window_start:
                request_timestamps.popleft()
            
            # Check if limit exceeded
            if len(request_timestamps) >= self.requests_limit:
                return False
            
            # Add current request
            request_timestamps.append(now)
            return True
    
    def get_remaining(self, identifier):
        """Get remaining requests for identifier"""
        with _lock:
            now = datetime.utcnow()
            
            if identifier not in _request_history:
                return self.requests_limit
            
            request_timestamps = _request_history[identifier]
            
            # Remove old requests
            window_start = now - timedelta(seconds=self.window_seconds)
            while request_timestamps and request_timestamps[0] < window_start:
                request_timestamps.popleft()
            
            return self.requests_limit - len(request_timestamps)
    
    def get_reset_time(self, identifier):
        """Get when rate limit resets for identifier"""
        with _lock:
            now = datetime.utcnow()
            
            if identifier not in _request_history:
                return now
            
            request_timestamps = _request_history[identifier]
            
            if not request_timestamps:
                return now
            
            # First request in window + window duration
            oldest_request = request_timestamps[0]
            reset_time = oldest_request + timedelta(seconds=self.window_seconds)
            
            return reset_time


# Default rate limiters
default_limiter = RateLimiter(requests=100, window_seconds=60)  # 100 req/min for general
strict_limiter = RateLimiter(requests=10, window_seconds=60)    # 10 req/min for auth endpoints
admin_limiter = RateLimiter(requests=200, window_seconds=60)    # 200 req/min for admin


def get_identifier():
    """
    Get rate limiter identifier from request
    Prefers user ID if authenticated, falls back to IP
    
    Returns:
        String identifying the requester
    """
    if hasattr(g, 'current_user') and g.current_user:
        return f"user_{g.current_user.id}"
    
    # Get client IP (respects X-Forwarded-For header)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    return request.remote_addr or 'unknown'


def rate_limit(limiter=None, custom_limit=None):
    """
    Decorator to apply rate limiting to endpoints
    
    Args:
        limiter: RateLimiter instance (uses default if None)
        custom_limit: Tuple of (requests, window_seconds) to create custom limiter
    
    Usage:
        @app.route('/api/endpoint')
        @rate_limit()  # Uses default_limiter
        def endpoint():
            pass
        
        @app.route('/api/strict')
        @rate_limit(limiter=strict_limiter)
        def strict_endpoint():
            pass
        
        @app.route('/api/custom')
        @rate_limit(custom_limit=(50, 300))  # 50 requests per 5 minutes
        def custom_endpoint():
            pass
    """
    
    # Handle custom limit
    if custom_limit:
        limiter = RateLimiter(requests=custom_limit[0], window_seconds=custom_limit[1])
    
    # Use default if no limiter specified
    if not limiter:
        limiter = default_limiter
    
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            identifier = get_identifier()
            
            # Check rate limit
            if not limiter.is_allowed(identifier):
                remaining = limiter.get_remaining(identifier)
                reset_time = limiter.get_reset_time(identifier)
                reset_timestamp = int(reset_time.timestamp())
                
                return {
                    'success': False,
                    'message': 'Rate limit exceeded',
                    'error': f'Too many requests. Try again after {reset_time}',
                    'data': {
                        'limit': limiter.requests_limit,
                        'remaining': max(0, remaining),
                        'reset': reset_timestamp,
                        'window_seconds': limiter.window_seconds
                    },
                    'status': 429
                }, 429
            
            # Store rate limit info in response headers
            remaining = limiter.get_remaining(identifier)
            reset_time = limiter.get_reset_time(identifier)
            
            g.rate_limit_remaining = remaining
            g.rate_limit_reset = int(reset_time.timestamp())
            
            return func(*args, **kwargs)
        
        return decorated_function
    return decorator


def add_rate_limit_headers(response):
    """
    Add rate limit headers to response
    Should be registered as after_request handler
    """
    if hasattr(g, 'rate_limit_remaining'):
        response.headers['X-RateLimit-Remaining'] = str(g.rate_limit_remaining)
    
    if hasattr(g, 'rate_limit_reset'):
        response.headers['X-RateLimit-Reset'] = str(g.rate_limit_reset)
    
    return response


def cleanup_old_requests():
    """
    Cleanup old request history (should be called periodically)
    Removes entries that are inactive
    """
    with _lock:
        now = datetime.utcnow()
        cutoff_time = now - timedelta(hours=1)
        
        identifiers_to_remove = []
        
        for identifier, timestamps in _request_history.items():
            # Remove old timestamps
            while timestamps and timestamps[0] < cutoff_time:
                timestamps.popleft()
            
            # Remove empty entries
            if not timestamps:
                identifiers_to_remove.append(identifier)
        
        for identifier in identifiers_to_remove:
            del _request_history[identifier]
