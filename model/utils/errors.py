"""
Error handling and middleware for consistent error responses.

This module provides error handlers and middleware for consistent
error response formatting across the Flask application.
"""

from flask import jsonify, request
from model.utils.response import APIResponse


def redact_sensitive_fields(data):
    """
    Redact sensitive fields from request/response data for logging.
    
    Args:
        data (dict): The data to redact
        
    Returns:
        dict: A copy of the data with sensitive fields redacted
    """
    if not isinstance(data, dict):
        return data
    
    # Create a copy to avoid modifying the original
    redacted = data.copy()
    
    # List of sensitive field names to redact
    sensitive_fields = {
        'password', 'token', 'secret', 'api_key', 'authorization',
        'auth_token', 'access_token', 'refresh_token', 'jwt', 'credit_card'
    }
    
    # Redact sensitive fields
    for field in sensitive_fields:
        if field in redacted:
            redacted[field] = '***REDACTED***'
    
    return redacted


def register_error_handlers(app):
    """
    Register error handlers for the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors."""
        return APIResponse.bad_request(
            message=error.description or "Bad request - Invalid data provided"
        )

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors."""
        return APIResponse.unauthorized(
            message=error.description or "Unauthorized - Authentication required"
        )

    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors."""
        return APIResponse.forbidden(
            message=error.description or "Forbidden - Insufficient permissions"
        )

    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors."""
        return APIResponse.not_found(
            resource=request.path
        )

    @app.errorhandler(409)
    def conflict(error):
        """Handle 409 Conflict errors."""
        return APIResponse.conflict(
            message=error.description or "Conflict - Resource already exists"
        )

    @app.errorhandler(422)
    def unprocessable_entity(error):
        """Handle 422 Unprocessable Entity errors."""
        return APIResponse.error(
            message="Unprocessable entity - Invalid request data",
            error_code="UNPROCESSABLE_ENTITY",
            status_code=422
        )

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        return APIResponse.error(
            message="Internal server error - Something went wrong on our end",
            error_code="INTERNAL_ERROR",
            status_code=500
        )

    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable errors."""
        return APIResponse.error(
            message="Service unavailable - Please try again later",
            error_code="SERVICE_UNAVAILABLE",
            status_code=503
        )


def log_request(app):
    """
    Middleware to log incoming requests.
    
    Args:
        app: Flask application instance
    """
    
    @app.before_request
    def log_request_info():
        """Log request details before processing."""
        app.logger.debug(f"{request.method} {request.path} - IP: {request.remote_addr}")
        if request.get_json(silent=True):
            # Redact sensitive fields before logging
            request_data = request.get_json()
            redacted_data = redact_sensitive_fields(request_data)
            app.logger.debug(f"Request body: {redacted_data}")

    @app.after_request
    def log_response_info(response):
        """Log response details after processing."""
        app.logger.debug(f"Response status: {response.status_code}")
        return response


def handle_cors(app):
    """
    Configure CORS headers for API requests.
    
    Note: CORS is initialized in __init__.py with flask_cors.
    This function is for additional CORS middleware if needed.
    
    Args:
        app: Flask application instance
    """
    
    @app.after_request
    def after_request(response):
        """Add CORS headers to response."""
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        response.headers.add('Access-Control-Expose-Headers', 'Content-Length, X-JSON-Response-Size')
        return response
