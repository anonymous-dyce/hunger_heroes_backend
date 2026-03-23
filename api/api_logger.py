# api_logger.py
"""
API logging system
Logs all requests with timestamp, user, endpoint, method, response status
Supports file, console, and database logging
"""

import logging
import json
from datetime import datetime
from functools import wraps
from flask import request, g
from logging.handlers import RotatingFileHandler
import os


class APILogger:
    """Comprehensive API logging system"""
    
    def __init__(self, app=None, log_file=None, log_level=logging.INFO):
        """
        Initialize API logger
        
        Args:
            app: Flask app instance
            log_file: Path to log file (default: logs/api.log)
            log_level: Python logging level
        """
        self.log_file = log_file or 'logs/api.log'
        self.log_level = log_level
        self.logger = logging.getLogger('api')
        self.setup_logger()
        
        if app:
            self.init_app(app)
    
    def setup_logger(self):
        """Setup logging handlers"""
        # Ensure logs directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Set logger level
        self.logger.setLevel(self.log_level)
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            self.log_file,
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(self.log_level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        # Register request/response hooks
        app.before_request(self.log_request_start)
        app.after_request(self.log_request_end)
    
    def log_request_start(self):
        """Log request start"""
        g.request_start_time = datetime.utcnow()
        g.request_id = self.generate_request_id()
        
        # Log basic request info
        user_id = self.get_user_id()
        method = request.method
        endpoint = request.endpoint or 'unknown'
        
        self.logger.info(
            f'[{g.request_id}] START {method} /{endpoint} - '
            f'User: {user_id} - IP: {self.get_client_ip()}'
        )
    
    def log_request_end(self, response):
        """Log request end"""
        try:
            if not hasattr(g, 'request_start_time'):
                return response
            
            duration = (datetime.utcnow() - g.request_start_time).total_seconds()
            user_id = self.get_user_id()
            method = request.method
            endpoint = request.endpoint or 'unknown'
            status = response.status_code
            
            # Determine log level based on status
            if status >= 500:
                level = logging.ERROR
            elif status >= 400:
                level = logging.WARNING
            else:
                level = logging.INFO
            
            log_message = (
                f'[{g.request_id}] END {method} /{endpoint} - '
                f'Status: {status} - Duration: {duration:.3f}s - '
                f'User: {user_id}'
            )
            
            self.logger.log(level, log_message)
            
            # Log response headers for rate limiting
            if 'X-RateLimit-Remaining' in response.headers:
                self.logger.debug(
                    f'[{g.request_id}] RateLimit - '
                    f'Remaining: {response.headers.get("X-RateLimit-Remaining")} - '
                    f'Reset: {response.headers.get("X-RateLimit-Reset")}'
                )
        
        except Exception as e:
            self.logger.error(f'Error logging request end: {str(e)}')
        
        return response
    
    def log_error(self, error, context=None):
        """
        Log an error with context
        
        Args:
            error: Exception or error message
            context: Additional context dict
        """
        try:
            request_id = getattr(g, 'request_id', 'unknown')
            user_id = self.get_user_id()
            endpoint = request.endpoint or 'unknown'
            
            context_str = json.dumps(context) if context else ''
            
            self.logger.error(
                f'[{request_id}] ERROR in /{endpoint} - '
                f'User: {user_id} - '
                f'Error: {str(error)} - '
                f'Context: {context_str}'
            )
        except Exception as e:
            self.logger.error(f'Error logging error: {str(e)}')
    
    def log_database_operation(self, operation, model, success, duration=None):
        """
        Log database operations
        
        Args:
            operation: CREATE, READ, UPDATE, DELETE
            model: Model name
            success: Boolean success flag
            duration: Operation duration in seconds
        """
        try:
            request_id = getattr(g, 'request_id', 'unknown')
            user_id = self.get_user_id()
            
            status = 'SUCCESS' if success else 'FAILED'
            duration_str = f' ({duration:.3f}s)' if duration else ''
            
            self.logger.info(
                f'[{request_id}] DB {operation} {model} - '
                f'{status} - User: {user_id}{duration_str}'
            )
        except Exception as e:
            self.logger.error(f'Error logging DB operation: {str(e)}')
    
    def log_admin_action(self, action, resource_type, resource_id, details=None):
        """
        Log admin actions
        
        Args:
            action: Action type (CREATE, UPDATE, DELETE, VERIFY, etc)
            resource_type: Type of resource (Donation, Organization, Flag, User)
            resource_id: ID of resource
            details: Additional details dict
        """
        try:
            request_id = getattr(g, 'request_id', 'unknown')
            user_id = self.get_user_id()
            
            details_str = json.dumps(details) if details else ''
            
            self.logger.warning(
                f'[{request_id}] ADMIN_ACTION {action} {resource_type}#{resource_id} - '
                f'Admin: {user_id} - Details: {details_str}'
            )
        except Exception as e:
            self.logger.error(f'Error logging admin action: {str(e)}')
    
    def log_security_event(self, event_type, details=None):
        """
        Log security events
        
        Args:
            event_type: Type of security event (UNAUTHORIZED, FORBIDDEN, RATE_LIMIT, etc)
            details: Additional details dict
        """
        try:
            request_id = getattr(g, 'request_id', 'unknown')
            user_id = self.get_user_id()
            ip = self.get_client_ip()
            endpoint = request.endpoint or 'unknown'
            
            details_str = json.dumps(details) if details else ''
            
            self.logger.warning(
                f'[{request_id}] SECURITY_EVENT {event_type} - '
                f'Endpoint: /{endpoint} - '
                f'User: {user_id} - IP: {ip} - '
                f'Details: {details_str}'
            )
        except Exception as e:
            self.logger.error(f'Error logging security event: {str(e)}')
    
    @staticmethod
    def get_user_id():
        """Get current user ID from request context"""
        if hasattr(g, 'current_user') and g.current_user:
            return f'user_{g.current_user.id}'
        return 'anonymous'
    
    @staticmethod
    def get_client_ip():
        """Get client IP from request"""
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return request.remote_addr or 'unknown'
    
    @staticmethod
    def generate_request_id():
        """Generate unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]


# Global logger instance
api_logger = APILogger()


def log_endpoint_access():
    """
    Decorator to enhance logging for specific endpoints
    
    Usage:
        @app.route('/api/donations')
        @log_endpoint_access()
        def get_donations():
            pass
    """
    def decorator(func):
        @wraps(func)
        def decorated_function(*args, **kwargs):
            request_id = getattr(g, 'request_id', 'unknown')
            
            # Log request details
            if request.is_json:
                try:
                    data = request.get_json()
                    api_logger.logger.debug(
                        f'[{request_id}] Request body: {json.dumps(data)[:500]}'
                    )
                except:
                    pass
            
            # Call the function
            result = func(*args, **kwargs)
            
            # Log response for successful requests
            if isinstance(result, tuple) and len(result) > 1:
                status = result[1]
            else:
                status = 200
            
            if status >= 400:
                api_logger.logger.debug(
                    f'[{request_id}] Response status: {status}'
                )
            
            return result
        
        return decorated_function
    return decorator


def setup_api_logging(app, log_file=None):
    """
    Setup API logging for Flask app
    
    Args:
        app: Flask app instance
        log_file: Path to log file
    """
    global api_logger
    api_logger = APILogger(app=app, log_file=log_file)
    return api_logger
