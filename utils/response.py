"""
Consistent JSON response formatting utilities for the Hunger Heroes API.

This module provides standardized response structures for success, errors,
and validation failures across all API endpoints.
"""

from flask import jsonify
from typing import Any, Dict, Optional, List


class APIResponse:
    """Standardized API response formatter."""

    @staticmethod
    def success(data: Any = None, message: str = "Success", status_code: int = 200) -> tuple:
        """
        Format a successful API response.
        
        Args:
            data: The response data (dict, list, or any JSON-serializable object)
            message: Human-readable success message
            status_code: HTTP status code (default: 200)
            
        Returns:
            Tuple of (jsonified response, status_code)
        """
        response = {
            "success": True,
            "message": message,
            "data": data,
            "status": status_code
        }
        return jsonify(response), status_code

    @staticmethod
    def created(data: Any = None, message: str = "Resource created successfully", resource_id: Optional[str] = None) -> tuple:
        """
        Format a resource creation response (201).
        
        Args:
            data: The created resource data
            message: Human-readable message
            resource_id: ID of the created resource (optional)
            
        Returns:
            Tuple of (jsonified response, 201)
        """
        response = {
            "success": True,
            "message": message,
            "data": data,
            "resource_id": resource_id,
            "status": 201
        }
        return jsonify(response), 201

    @staticmethod
    def error(message: str, error_code: str = "INTERNAL_ERROR", status_code: int = 500, details: Optional[Dict] = None) -> tuple:
        """
        Format an error response.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code (default: 500)
            details: Additional error details (optional)
            
        Returns:
            Tuple of (jsonified response, status_code)
        """
        response = {
            "success": False,
            "message": message,
            "error": error_code,
            "status": status_code
        }
        if details:
            response["details"] = details
            
        return jsonify(response), status_code

    @staticmethod
    def unauthorized(message: str = "Unauthorized - Authentication required") -> tuple:
        """Format an unauthorized (401) response."""
        return APIResponse.error(
            message=message,
            error_code="UNAUTHORIZED",
            status_code=401
        )

    @staticmethod
    def forbidden(message: str = "Forbidden - Insufficient permissions") -> tuple:
        """Format a forbidden (403) response."""
        return APIResponse.error(
            message=message,
            error_code="FORBIDDEN",
            status_code=403
        )

    @staticmethod
    def not_found(resource: str = "Resource") -> tuple:
        """Format a not found (404) response."""
        return APIResponse.error(
            message=f"{resource} not found",
            error_code="NOT_FOUND",
            status_code=404
        )

    @staticmethod
    def bad_request(message: str, errors: Optional[List[str]] = None) -> tuple:
        """
        Format a bad request (400) response.
        
        Args:
            message: Human-readable error message
            errors: List of validation errors (optional)
            
        Returns:
            Tuple of (jsonified response, 400)
        """
        response = {
            "success": False,
            "message": message,
            "error": "VALIDATION_ERROR",
            "status": 400
        }
        if errors:
            response["validation_errors"] = errors
            
        return jsonify(response), 400

    @staticmethod
    def conflict(message: str, resource_id: Optional[str] = None) -> tuple:
        """
        Format a conflict (409) response (e.g., duplicate resource).
        
        Args:
            message: Human-readable error message
            resource_id: ID of the conflicting resource (optional)
            
        Returns:
            Tuple of (jsonified response, 409)
        """
        response = {
            "success": False,
            "message": message,
            "error": "CONFLICT",
            "status": 409
        }
        if resource_id:
            response["resource_id"] = resource_id
            
        return jsonify(response), 409


class ValidationError(Exception):
    """Custom exception for validation errors."""
    
    def __init__(self, message: str, errors: Optional[List[str]] = None):
        self.message = message
        self.errors = errors or []
        super().__init__(self.message)


class AuthError(Exception):
    """Custom exception for authentication errors."""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
