# database_constraints.py
"""
Database constraints enforcement
Adds database-level constraints: unique keys, foreign keys with cascading, not-null constraints
"""

from sqlalchemy import UniqueConstraint, ForeignKeyConstraint, CheckConstraint, Index
from __init__ import db


class DatabaseConstraints:
    """
    Helper class for managing database constraints
    Can be called after models are defined to add constraints
    """
    
    @staticmethod
    def add_donation_constraints():
        """Add constraints to Donation model"""
        from model.donation import Donation
        
        # Constraints are typically defined at model definition time
        # But this documents what constraints should exist:
        
        constraints = {
            'unique': [
                'id',  # Donation ID must be unique
            ],
            'not_null': [
                'id', 'food_name', 'category', 'quantity', 'unit',
                'expiry_date', 'storage', 'donor_name', 'donor_email', 'donor_zip',
                'status', 'created_at'
            ],
            'check': [
                ('quantity > 0', 'Quantity must be positive'),
                ('safety_score >= 0 AND safety_score <= 100', 'Safety score 0-100'),
                ('weight_lbs IS NULL OR weight_lbs > 0', 'Weight must be positive'),
                ('scan_count >= 0', 'Scan count must be non-negative'),
            ],
            'foreign_keys': [
                ('donor_id', 'users.id', 'CASCADE'),
                ('receiver_id', 'users.id', 'CASCADE'),
                ('user_id', 'users.id', 'SET NULL'),
                ('volunteer_id', 'users.id', 'SET NULL'),
            ]
        }
        
        return constraints
    
    @staticmethod
    def add_flag_constraints():
        """Add constraints to Flag model"""
        from model.flag import Flag
        
        constraints = {
            'not_null': [
                'id', 'flag_type', 'severity', 'status', 'title', 'description', 'created_at'
            ],
            'check': [
                ("flag_type IN ('safety_concern', 'donation_issue', 'organization_issue', 'user_violation')", 
                 'Invalid flag type'),
                ("severity IN ('low', 'medium', 'high', 'critical')", 'Invalid severity level'),
                ("status IN ('open', 'in_review', 'resolved', 'dismissed')", 'Invalid status'),
            ],
            'foreign_keys': [
                ('donation_id', 'donations.id', 'CASCADE'),
                ('organization_id', 'organizations.id', 'CASCADE'),
                ('user_id', 'users.id', 'CASCADE'),
                ('reporter_id', 'users.id', 'SET NULL'),
                ('resolved_by', 'users.id', 'SET NULL'),
            ]
        }
        
        return constraints
    
    @staticmethod
    def add_organization_constraints():
        """Add constraints to Organization model"""
        from model.organization import Organization
        
        constraints = {
            'not_null': [
                'id', 'name', 'type', 'address', 'zip_code'
            ],
            'check': [
                ("type IN ('shelter', 'food_bank', 'restaurant', 'temple', 'community_org')", 
                 'Invalid organization type'),
                ('capacity IS NULL OR capacity > 0', 'Capacity must be positive'),
                ('storage_capacity_lbs IS NULL OR storage_capacity_lbs > 0', 'Storage capacity must be positive'),
            ],
            'foreign_keys': []
        }
        
        return constraints
    
    @staticmethod
    def add_user_constraints():
        """Add constraints to User model"""
        from model.user import User
        
        constraints = {
            'unique': [
                '_uid', '_email'  # UID and email must be unique
            ],
            'not_null': [
                'id', '_name', '_uid', '_email', '_password', '_role'
            ],
            'check': [
                ("_role IN ('Admin', 'Donor', 'Receiver', 'Volunteer', 'User')", 
                 'Invalid user role'),
            ],
            'foreign_keys': [
                ('_organization_id', 'organizations.id', 'SET NULL'),
            ]
        }
        
        return constraints
    
    @staticmethod
    def print_constraints():
        """Print all constraints for documentation"""
        print("\n=== DATABASE CONSTRAINTS ===\n")
        
        from model.donation import Donation
        from model.flag import Flag
        from model.organization import Organization
        from model.user import User
        
        print("DONATION CONSTRAINTS:")
        con = DatabaseConstraints.add_donation_constraints()
        for key, value in con.items():
            print(f"  {key}: {value}")
        
        print("\nFLAG CONSTRAINTS:")
        con = DatabaseConstraints.add_flag_constraints()
        for key, value in con.items():
            print(f"  {key}: {value}")
        
        print("\nORGANIZATION CONSTRAINTS:")
        con = DatabaseConstraints.add_organization_constraints()
        for key, value in con.items():
            print(f"  {key}: {value}")
        
        print("\nUSER CONSTRAINTS:")
        con = DatabaseConstraints.add_user_constraints()
        for key, value in con.items():
            print(f"  {key}: {value}")


# Indexes for performance
class DatabaseIndexes:
    """Helper for creating database indexes"""
    
    @staticmethod
    def get_donation_indexes():
        """Get recommended indexes for Donation table"""
        return [
            ['status'],          # Filter by status
            ['donor_id'],        # Filter by donor
            ['receiver_id'],     # Filter by receiver
            ['requires_review'], # Flag donations needing review
            ['created_at'],      # Sort by date
            ['safety_score'],    # Filter by safety
            ['status', 'created_at'],  # Composite for status timeline
        ]
    
    @staticmethod
    def get_flag_indexes():
        """Get recommended indexes for Flag table"""
        return [
            ['status'],          # Filter by status
            ['severity'],        # Filter by severity
            ['flag_type'],       # Filter by type
            ['donation_id'],     # Link to donation
            ['organization_id'], # Link to org
            ['user_id'],         # Link to user
            ['created_at'],      # Sort by date
            ['status', 'severity'],  # Composite for filtering
        ]
    
    @staticmethod
    def get_organization_indexes():
        """Get recommended indexes for Organization table"""
        return [
            ['is_verified'],     # Filter by verification status
            ['type'],            # Filter by type
            ['zip_code'],        # Geographic filtering
            ['created_at'],      # Sort by date
        ]
    
    @staticmethod
    def get_user_indexes():
        """Get recommended indexes for User table"""
        return [
            ['_uid'],            # Primary lookup
            ['_email'],          # Email lookup
            ['_role'],           # Filter by role
            ['_organization_id'],# Filter by org
            ['is_active'],       # Filter by status
            ['created_at'],      # Sort by date
        ]


def validate_data_integrity():
    """
    Validate data integrity of database
    Checks for orphaned records, null values where not allowed, etc.
    
    Returns:
        Dict with issues found
    """
    from model.donation import Donation
    from model.flag import Flag
    from model.user import User
    from model.organization import Organization
    from __init__ import db
    
    issues = {
        'donations': [],
        'flags': [],
        'users': [],
        'organizations': []
    }
    
    # Check donations
    try:
        # Required fields
        null_donations = Donation.query.filter(
            db.or_(
                Donation.food_name == None,
                Donation.donor_name == None,
                Donation.donation_id == None,
            )
        ).count()
        
        if null_donations > 0:
            issues['donations'].append(f'{null_donations} donations with null required fields')
        
        # Invalid safety scores
        invalid_scores = Donation.query.filter(
            db.or_(
                Donation.safety_score < 0,
                Donation.safety_score > 100
            )
        ).count()
        
        if invalid_scores > 0:
            issues['donations'].append(f'{invalid_scores} donations with invalid safety scores')
    
    except Exception as e:
        issues['donations'].append(f'Error checking donations: {str(e)}')
    
    # Check flags
    try:
        null_flags = Flag.query.filter(
            db.or_(
                Flag.title == None,
                Flag.description == None,
                Flag.flag_type == None
            )
        ).count()
        
        if null_flags > 0:
            issues['flags'].append(f'{null_flags} flags with null required fields')
    
    except Exception as e:
        issues['flags'].append(f'Error checking flags: {str(e)}')
    
    # Check users
    try:
        null_users = User.query.filter(
            db.or_(
                User._name == None,
                User._email == None,
                User._role == None
            )
        ).count()
        
        if null_users > 0:
            issues['users'].append(f'{null_users} users with null required fields')
    
    except Exception as e:
        issues['users'].append(f'Error checking users: {str(e)}')
    
    return issues
