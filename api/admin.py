# admin.py
"""
Admin Panel API
Endpoints for admin-only operations: donations, organizations, flags, users
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime, timedelta
from sqlalchemy import or_, and_
import json

from __init__ import db
from model.user import User
from model.donation import Donation
from model.organization import Organization
from model.flag import Flag
from api.admin_middleware import admin_required


# Create admin blueprint
admin_api = Blueprint('admin_api', __name__, url_prefix='/api/admin')


# ════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ════════════════════════════════════════════════════════════════

def serialize_user(user):
    """Serialize user object with activity metrics."""
    if not user:
        return None
    
    # Calculate activity metrics
    donations_count = len(user.donated) if user.donated else 0
    received_count = len(user.received_donations) if user.received_donations else 0
    
    return {
        'id': user.id,
        'name': user._name,
        'email': user._email,
        'role': user._role,
        'status': 'active' if user.is_active else 'inactive',
        'organization_id': user._organization_id,
        'created_at': user.created_at.isoformat(),
        'last_activity': user.updated_at.isoformat(),
        'activity_metrics': {
            'donations_created': donations_count,
            'donations_received': received_count,
            'account_age_days': (datetime.utcnow() - user.created_at).days
        }
    }


def serialize_donation(donation, include_details=True):
    """Serialize donation object for admin view."""
    if not donation:
        return None
    
    data = {
        'id': donation.id,
        'food_name': donation.food_name,
        'category': donation.category,
        'quantity': donation.quantity,
        'unit': donation.unit,
        'status': donation.status,
        'safety_score': donation.safety_score,
        'requires_review': donation.requires_review,
        'donor_name': donation.donor_name,
        'donor_email': donation.donor_email,
        'expiry_date': donation.expiry_date.isoformat() if donation.expiry_date else None,
        'created_at': donation.created_at.isoformat(),
        'is_flagged': bool(donation.flags),
        'flag_count': len(donation.flags) if donation.flags else 0
    }
    
    if include_details:
        data.update({
            'food_type': donation.food_type,
            'weight_lbs': donation.weight_lbs,
            'storage': donation.storage,
            'allergens': donation.allergens,
            'dietary_tags': donation.dietary_tags,
            'donor_id': donation.donor_id,
            'receiver_id': donation.receiver_id,
            'claimed_at': donation.claimed_at.isoformat() if donation.claimed_at else None,
            'delivered_at': donation.delivered_at.isoformat() if donation.delivered_at else None,
            'confirmed_at': donation.confirmed_at.isoformat() if donation.confirmed_at else None,
            'is_archived': donation.is_archived,
            'flags': [flag.read() for flag in donation.flags] if donation.flags else []
        })
    
    return data


def serialize_organization(org):
    """Serialize organization object for admin view."""
    if not org:
        return None
    
    return {
        'id': org.id,
        'name': org.name,
        'type': org.type,
        'address': org.address,
        'zip_code': org.zip_code,
        'is_verified': org.is_verified,
        'verification_date': org.verification_date.isoformat() if org.verification_date else None,
        'verified_by': org.verified_by,
        'capacity': org.capacity,
        'refrigeration_available': org.refrigeration_available,
        'phone': org.phone,
        'email': org.email,
        'website': org.website,
        'member_count': len(org.members) if org.members else 0,
        'is_active': org.is_active,
        'created_at': org.created_at.isoformat() if hasattr(org, 'created_at') else None
    }


# ════════════════════════════════════════════════════════════════
# DONATIONS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@admin_api.route('/donations', methods=['GET'])
@admin_required
def get_donations():
    """
    GET /api/admin/donations
    List all donations with admin filters
    
    Query Parameters:
        - status: Filter by status (posted, claimed, in_transit, delivered, confirmed, expired, cancelled)
        - safety_score: Filter by safety score (requires_review, high_score, low_score)
        - flagged: Filter flagged donations (true/false)
        - page: Pagination page (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        List of donations with admin filters
    """
    try:
        # Get query parameters
        status = request.args.get('status')
        safety_filter = request.args.get('safety_score')
        flagged = request.args.get('flagged', '').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = Donation.query
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        
        if safety_filter == 'requires_review':
            query = query.filter_by(requires_review=True)
        elif safety_filter == 'low_score':
            query = query.filter(Donation.safety_score < 70)
        elif safety_filter == 'high_score':
            query = query.filter(Donation.safety_score >= 80)
        
        if flagged:
            # Only return donations with flags
            query = query.outerjoin(Flag).filter(Flag.id.isnot(None)).distinct()
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'success': True,
            'message': 'Donations retrieved successfully',
            'data': {
                'donations': [serialize_donation(d, include_details=False) for d in paginated.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated.total,
                    'pages': paginated.pages
                }
            },
            'status': 200
        }, 200
    
    except Exception as e:
        return {
            'success': False,
            'message': 'Error retrieving donations',
            'error': str(e),
            'status': 500
        }, 500


@admin_api.route('/donations/<donation_id>', methods=['PATCH'])
@admin_required
def patch_donation(donation_id):
    """
    PATCH /api/admin/donations/{id}
    Admin override for donation status
    
    Request Body:
        {
            "status": "new_status",
            "safety_score": 85,
            "requires_review": false,
            "admin_notes": "Optional notes"
        }
    
    Returns:
        Updated donation
    """
    try:
        donation = Donation.query.filter_by(id=donation_id).first()
        
        if not donation:
            return {
                'success': False,
                'message': 'Donation not found',
                'status': 404
            }, 404
        
        data = request.get_json()
        
        # Update donation fields
        if 'status' in data:
            donation.status = data['status']
        
        if 'safety_score' in data:
            donation.safety_score = data['safety_score']
        
        if 'requires_review' in data:
            donation.requires_review = data['requires_review']
        
        # Log admin action in donation comments/metadata if needed
        donation.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Donation updated successfully',
            'data': serialize_donation(donation, include_details=True),
            'status': 200
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': 'Error updating donation',
            'error': str(e),
            'status': 500
        }, 500


# ════════════════════════════════════════════════════════════════
# ORGANIZATIONS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@admin_api.route('/organizations', methods=['GET'])
@admin_required
def get_organizations():
    """
    GET /api/admin/organizations
    List all registered organizations with verification status
    
    Query Parameters:
        - verified: Filter by verification status (true/false)
        - type: Filter by organization type (shelter, food_bank, restaurant, temple, community_org)
        - page: Pagination page (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        List of organizations
    """
    try:
        # Get query parameters
        verified = request.args.get('verified', '').lower()
        org_type = request.args.get('type')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = Organization.query
        
        # Apply filters
        if verified in ['true', 'false']:
            query = query.filter_by(is_verified=(verified == 'true'))
        
        if org_type:
            query = query.filter_by(type=org_type)
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'success': True,
            'message': 'Organizations retrieved successfully',
            'data': {
                'organizations': [serialize_organization(o) for o in paginated.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated.total,
                    'pages': paginated.pages
                }
            },
            'status': 200
        }, 200
    
    except Exception as e:
        return {
            'success': False,
            'message': 'Error retrieving organizations',
            'error': str(e),
            'status': 500
        }, 500


@admin_api.route('/organizations/<int:org_id>/verify', methods=['PATCH'])
@admin_required
def patch_organization_verify(org_id):
    """
    PATCH /api/admin/organizations/{id}/verify
    Verify or unverify an organization
    
    Request Body:
        {
            "is_verified": true,
            "verification_notes": "Optional notes"
        }
    
    Returns:
        Updated organization
    """
    try:
        organization = Organization.query.filter_by(id=org_id).first()
        
        if not organization:
            return {
                'success': False,
                'message': 'Organization not found',
                'status': 404
            }, 404
        
        data = request.get_json()
        
        if 'is_verified' not in data:
            return {
                'success': False,
                'message': 'is_verified field is required',
                'status': 400
            }, 400
        
        is_verified = data['is_verified']
        
        # Update verification status
        organization.is_verified = is_verified
        
        if is_verified:
            organization.verification_date = datetime.utcnow()
            organization.verified_by = g.current_user._uid
        else:
            organization.verification_date = None
            organization.verified_by = None
        
        organization.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Organization {"verified" if is_verified else "unverified"} successfully',
            'data': serialize_organization(organization),
            'status': 200
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': 'Error updating organization verification',
            'error': str(e),
            'status': 500
        }, 500


# ════════════════════════════════════════════════════════════════
# FLAGS/ISSUES ENDPOINTS
# ════════════════════════════════════════════════════════════════

@admin_api.route('/flags', methods=['GET'])
@admin_required
def get_flags():
    """
    GET /api/admin/flags
    List all flagged donations and reported issues
    
    Query Parameters:
        - status: Filter by status (open, in_review, resolved, dismissed)
        - severity: Filter by severity (low, medium, high, critical)
        - type: Filter by flag type (safety_concern, donation_issue, organization_issue, user_violation)
        - page: Pagination page (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        List of flags/issues
    """
    try:
        # Get query parameters
        status = request.args.get('status')
        severity = request.args.get('severity')
        flag_type = request.args.get('type')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = Flag.query
        
        # Apply filters
        if status:
            query = query.filter_by(status=status)
        
        if severity:
            query = query.filter_by(severity=severity)
        
        if flag_type:
            query = query.filter_by(flag_type=flag_type)
        
        # Order by severity and creation date
        query = query.order_by(
            # Critical first, then high, medium, low
            (Flag.severity == 'critical').desc(),
            (Flag.severity == 'high').desc(),
            (Flag.severity == 'medium').desc(),
            Flag.created_at.desc()
        )
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'success': True,
            'message': 'Flags retrieved successfully',
            'data': {
                'flags': [flag.read() for flag in paginated.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated.total,
                    'pages': paginated.pages
                },
                'summary': {
                    'total_open': Flag.query.filter_by(status='open').count(),
                    'total_critical': Flag.query.filter_by(severity='critical').count(),
                    'total_high': Flag.query.filter_by(severity='high').count(),
                }
            },
            'status': 200
        }, 200
    
    except Exception as e:
        return {
            'success': False,
            'message': 'Error retrieving flags',
            'error': str(e),
            'status': 500
        }, 500


@admin_api.route('/flags/<int:flag_id>/resolve', methods=['PATCH'])
@admin_required
def patch_flag_resolve(flag_id):
    """
    PATCH /api/admin/flags/{id}/resolve
    Resolve a flagged issue with notes
    
    Request Body:
        {
            "status": "resolved",
            "resolution_notes": "Issue has been addressed. Action taken: ...",
            "action_taken": "Optional description of corrective action"
        }
    
    Returns:
        Updated flag
    """
    try:
        flag = Flag.query.filter_by(id=flag_id).first()
        
        if not flag:
            return {
                'success': False,
                'message': 'Flag not found',
                'status': 404
            }, 404
        
        data = request.get_json()
        
        # Resolve the flag
        resolution_notes = data.get('resolution_notes', '')
        new_status = data.get('status', 'resolved')
        
        flag.status = new_status
        flag.resolution_notes = resolution_notes
        
        if new_status == 'resolved':
            flag.resolved_by = g.current_user.id
            flag.resolved_at = datetime.utcnow()
        
        flag.updated_at = datetime.utcnow()
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Flag resolved successfully',
            'data': flag.read(),
            'status': 200
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': 'Error resolving flag',
            'error': str(e),
            'status': 500
        }, 500


# ════════════════════════════════════════════════════════════════
# USERS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@admin_api.route('/users', methods=['GET'])
@admin_required
def get_users():
    """
    GET /api/admin/users
    List all users with role, status, and activity metrics
    
    Query Parameters:
        - role: Filter by role (Admin, Donor, Receiver, Volunteer, User)
        - status: Filter by status (active, inactive)
        - page: Pagination page (default: 1)
        - per_page: Items per page (default: 20)
    
    Returns:
        List of users with activity metrics
    """
    try:
        # Get query parameters
        role = request.args.get('role')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Build query
        query = User.query
        
        # Apply filters
        if role:
            query = query.filter_by(_role=role)
        
        if status:
            is_active = status.lower() == 'active'
            query = query.filter_by(is_active=is_active)
        
        # Order by creation date (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'success': True,
            'message': 'Users retrieved successfully',
            'data': {
                'users': [serialize_user(u) for u in paginated.items],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': paginated.total,
                    'pages': paginated.pages
                },
                'summary': {
                    'total_users': User.query.count(),
                    'active_users': User.query.filter_by(is_active=True).count(),
                    'admin_count': User.query.filter_by(_role='Admin').count(),
                    'donor_count': User.query.filter_by(_role='Donor').count(),
                    'receiver_count': User.query.filter_by(_role='Receiver').count(),
                    'volunteer_count': User.query.filter_by(_role='Volunteer').count(),
                }
            },
            'status': 200
        }, 200
    
    except Exception as e:
        return {
            'success': False,
            'message': 'Error retrieving users',
            'error': str(e),
            'status': 500
        }, 500


@admin_api.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(user_id):
    """
    GET /api/admin/users/{id}
    Get detailed user information for admin review
    
    Returns:
        Detailed user object with full activity metrics
    """
    try:
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return {
                'success': False,
                'message': 'User not found',
                'status': 404
            }, 404
        
        user_data = serialize_user(user)
        
        # Add organization details if user is receiver
        if user._role == 'Receiver' and user._organization_id:
            org = Organization.query.filter_by(id=user._organization_id).first()
            user_data['organization'] = serialize_organization(org) if org else None
        
        # Add flags count if user has any
        user_flags = Flag.query.filter_by(user_id=user_id).all()
        user_data['flags_count'] = len(user_flags)
        user_data['recent_flags'] = [f.read() for f in user_flags[-5:]]  # Last 5
        
        return {
            'success': True,
            'message': 'User details retrieved successfully',
            'data': user_data,
            'status': 200
        }, 200
    
    except Exception as e:
        return {
            'success': False,
            'message': 'Error retrieving user details',
            'error': str(e),
            'status': 500
        }, 500


@admin_api.route('/users/<int:user_id>/suspend', methods=['PATCH'])
@admin_required
def patch_user_suspend(user_id):
    """
    PATCH /api/admin/users/{id}/suspend
    Suspend or activate a user account
    
    Request Body:
        {
            "is_active": false,
            "reason": "Optional reason for suspension"
        }
    
    Returns:
        Updated user
    """
    try:
        user = User.query.filter_by(id=user_id).first()
        
        if not user:
            return {
                'success': False,
                'message': 'User not found',
                'status': 404
            }, 404
        
        data = request.get_json()
        
        if 'is_active' not in data:
            return {
                'success': False,
                'message': 'is_active field is required',
                'status': 400
            }, 400
        
        user.is_active = data['is_active']
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        action = 'activated' if data['is_active'] else 'suspended'
        
        return {
            'success': True,
            'message': f'User {action} successfully',
            'data': serialize_user(user),
            'status': 200
        }, 200
    
    except Exception as e:
        db.session.rollback()
        return {
            'success': False,
            'message': 'Error updating user status',
            'error': str(e),
            'status': 500
        }, 500


# ════════════════════════════════════════════════════════════════
# DASHBOARD/STATS ENDPOINTS
# ════════════════════════════════════════════════════════════════

@admin_api.route('/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    """
    GET /api/admin/stats
    Get admin dashboard statistics
    
    Returns:
        Platform statistics for dashboard
    """
    try:
        # User statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        
        # Donation statistics
        total_donations = Donation.query.count()
        pending_donations = Donation.query.filter(Donation.status.in_(['posted', 'claimed'])).count()
        flagged_donations = Donation.query.filter_by(requires_review=True).count()
        
        # Safety statistics
        low_safety_donations = Donation.query.filter(Donation.safety_score < 70).count()
        
        # Organization statistics
        total_organizations = Organization.query.count()
        verified_organizations = Organization.query.filter_by(is_verified=True).count()
        
        # Flag statistics
        open_flags = Flag.query.filter_by(status='open').count()
        critical_flags = Flag.query.filter_by(severity='critical').count()
        resolved_flags = Flag.query.filter_by(status='resolved').count()
        
        return {
            'success': True,
            'message': 'Admin statistics retrieved successfully',
            'data': {
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'inactive': total_users - active_users
                },
                'donations': {
                    'total': total_donations,
                    'pending': pending_donations,
                    'flagged': flagged_donations,
                    'low_safety': low_safety_donations
                },
                'organizations': {
                    'total': total_organizations,
                    'verified': verified_organizations,
                    'unverified': total_organizations - verified_organizations
                },
                'flags': {
                    'open': open_flags,
                    'critical': critical_flags,
                    'resolved': resolved_flags,
                    'total': Flag.query.count()
                }
            },
            'status': 200
        }, 200
    
    except Exception as e:
        return {
            'success': False,
            'message': 'Error retrieving admin statistics',
            'error': str(e),
            'status': 500
        }, 500


# Error handler for 404
@admin_api.errorhandler(404)
def not_found(error):
    return {
        'success': False,
        'message': 'Endpoint not found',
        'error': 'Not Found',
        'status': 404
    }, 404


# Error handler for 405
@admin_api.errorhandler(405)
def method_not_allowed(error):
    return {
        'success': False,
        'message': 'Method not allowed',
        'error': 'Method Not Allowed',
        'status': 405
    }, 405
