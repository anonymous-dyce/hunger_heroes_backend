"""
Authentication API endpoints for user registration, login, and logout.

Endpoints:
- POST /api/auth/register: Register a new user
- POST /api/auth/login: Login and get JWT token
- POST /api/auth/logout: Logout (optional, handled client-side)
- GET /api/users/me: Get current user profile
"""

from flask import Blueprint, request, jsonify, g, current_app
from services.auth_service import (
    AuthService, 
    token_required, 
    rbac_required,
    AuthError,
    ValidationError
)
from utils.response import APIResponse
from model.user import User
import logging

logger = logging.getLogger(__name__)

# Create Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    
    Request JSON:
    {
        "name": "John Doe",
        "email": "john@example.com", 
        "password": "secure123",
        "role": "Donor",  // optional: User, Donor, Receiver, Volunteer, Admin
        "organization_id": 1  // optional: required if role is Receiver
    }
    
    Returns:
    {
        "success": true,
        "message": "User registered successfully",
        "data": {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "Donor",
            ...
        },
        "status": 201
    }
    """
    try:
        body = request.get_json()
        
        if not body:
            return APIResponse.bad_request("Request body is required")
        
        # Extract fields
        name = body.get('name')
        email = body.get('email')
        password = body.get('password')
        role = body.get('role', 'User')
        organization_id = body.get('organization_id')
        
        # Register user
        user_data = AuthService.register_user(
            name=name,
            email=email,
            password=password,
            role=role,
            organization_id=organization_id
        )
        
        return APIResponse.created(
            data=user_data,
            message="User registered successfully",
            resource_id=str(user_data.get('id'))
        )
        
    except ValidationError as e:
        logger.warning(f"Registration validation error: {e.message}")
        return APIResponse.bad_request(e.message, errors=e.errors)
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return APIResponse.error(
            message=str(e),
            error_code="REGISTRATION_ERROR",
            status_code=500
        )


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user and return JWT token.
    
    Request JSON:
    {
        "email": "john@example.com",
        "password": "secure123"
    }
    
    Returns:
    {
        "success": true,
        "message": "Login successful",
        "data": {
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "role": "Donor"
            }
        },
        "status": 200
    }
    
    Note: Token is also set in httpOnly cookie for standard browser-based requests
    """
    try:
        body = request.get_json()
        
        if not body:
            return APIResponse.bad_request("Email and password are required")
        
        email = body.get('email')
        password = body.get('password')
        
        # Authenticate user
        token = AuthService.login_user(email=email, password=password)
        
        # Get user data
        user = User.query.filter_by(_email=email).first()
        user_data = user.read() if user else {}
        
        # Create response with token in both body and cookie
        response_data = {
            "token": token,
            "user": user_data
        }
        
        response = APIResponse.success(
            data=response_data,
            message="Login successful",
            status_code=200
        )
        
        # Also set token in httpOnly cookie for browser-based clients
        response[0].set_cookie(
            key=current_app.config["JWT_TOKEN_NAME"],
            value=token,
            httponly=True,
            secure=current_app.config.get("SECURE_COOKIES", False),
            samesite='Lax',
            max_age=86400  # 24 hours
        )
        
        return response
        
    except AuthError as e:
        logger.warning(f"Login error: {e.message}")
        return APIResponse.unauthorized(message=e.message)
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return APIResponse.error(
            message=str(e),
            error_code="LOGIN_ERROR",
            status_code=500
        )


@auth_bp.route('/logout', methods=['POST'])
@token_required()
def logout():
    """
    Logout user (optional endpoint for audit purposes).
    
    Client should remove the JWT token cookie after logout.
    
    Returns:
    {
        "success": true,
        "message": "Logged out successfully",
        "status": 200
    }
    """
    try:
        current_user = g.current_user
        AuthService.logout_user(current_user.id)
        
        response = APIResponse.success(
            message="Logged out successfully",
            status_code=200
        )
        
        # Clear token cookie
        response[0].delete_cookie(
            key=current_app.config["JWT_TOKEN_NAME"],
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return APIResponse.error(
            message="Logout failed",
            error_code="LOGOUT_ERROR",
            status_code=500
        )


# Users endpoint for profile access
users_bp = Blueprint('users', __name__, url_prefix='/api/users')


@users_bp.route('/me', methods=['GET'])
@token_required()
def get_current_user():
    """
    Get current authenticated user's profile.
    
    Returns:
    {
        "success": true,
        "message": "User profile retrieved",
        "data": {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "Donor",
            "is_active": true,
            "created_at": "2026-03-05T12:00:00",
            "updated_at": "2026-03-05T12:00:00"
        },
        "status": 200
    }
    """
    try:
        current_user = g.current_user
        user_data = current_user.read()
        
        return APIResponse.success(
            data=user_data,
            message="User profile retrieved",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return APIResponse.error(
            message="Error retrieving user profile",
            error_code="PROFILE_ERROR",
            status_code=500
        )


@users_bp.route('/<int:user_id>', methods=['GET'])
@token_required()
def get_user(user_id: int):
    """
    Get user profile by ID (public endpoint, returns limited data).
    
    Parameters:
        user_id: User ID
    
    Returns:
    {
        "success": true,
        "message": "User profile retrieved",
        "data": {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com",
            "role": "Donor"
        },
        "status": 200
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return APIResponse.not_found(resource="User")
        
        if not user._is_active:
            return APIResponse.not_found(resource="User")
        
        # Return limited public data
        user_data = {
            "id": user.id,
            "name": user._name,
            "role": user._role
        }
        
        # Current user sees more data
        current_user = g.current_user
        if current_user.id == user_id or current_user._role == "Admin":
            user_data["email"] = user._email
            user_data["is_active"] = user._is_active
        
        return APIResponse.success(
            data=user_data,
            message="User profile retrieved",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        return APIResponse.error(
            message="Error retrieving user",
            error_code="PROFILE_ERROR",
            status_code=500
        )


@users_bp.route('/me', methods=['PUT'])
@token_required()
def update_current_user():
    """
    Update current user's profile.
    
    Request JSON:
    {
        "name": "Jane Doe" (optional),
        "password": "newpassword123" (optional),
        "email": "jane@example.com" (optional, only self-update allowed)
    }
    
    Returns:
    {
        "success": true,
        "message": "Profile updated successfully",
        "data": { updated user data },
        "status": 200
    }
    """
    try:
        current_user = g.current_user
        body = request.get_json()
        
        if not body:
            return APIResponse.bad_request("At least one field is required for update")
        
        # Update user
        current_user.update(body)
        
        return APIResponse.success(
            data=current_user.read(),
            message="Profile updated successfully",
            status_code=200
        )
        
    except ValidationError as e:
        return APIResponse.bad_request(e.message, errors=e.errors)
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        return APIResponse.error(
            message="Error updating profile",
            error_code="UPDATE_ERROR",
            status_code=500
        )
