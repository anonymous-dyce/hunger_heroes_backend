# flag.py
"""
Flag/Issue Model - For admin review of flagged donations and reported issues
"""

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from __init__ import app, db


class Flag(db.Model):
    """
    Flag/Issue Model
    
    Tracks flagged donations and reported issues that require admin review.
    
    Attributes:
        id (Column): Integer, Primary Key
        donation_id (Column): String(50), Foreign Key to donations.id (can be null for general issues)
        organization_id (Column): Integer, Foreign Key to organizations.id (can be null)
        user_id (Column): Integer, Foreign Key to users.id (reporter/flagged user, can be null)
        flag_type (Column): String - Type of flag: 'safety_concern', 'donation_issue', 'organization_issue', 'user_violation'
        severity (Column): String - 'low', 'medium', 'high', 'critical'
        status (Column): String - 'open', 'in_review', 'resolved', 'dismissed'
        title (Column): String - Main issue title
        description (Column): Text - Detailed description
        reporter_id (Column): Integer - Admin or user who reported/flagged the issue
        resolution_notes (Column): Text - Admin notes on resolution
        resolved_by (Column): Integer - Admin who resolved the issue
        resolved_at (Column): DateTime - When issue was resolved
        created_at (Column): DateTime
        updated_at (Column): DateTime
    """
    __tablename__ = 'flags'

    id = db.Column(db.Integer, primary_key=True)
    
    # Reference to flagged resource
    donation_id = db.Column(db.String(50), db.ForeignKey('donations.id'), nullable=True, index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey('organizations.id'), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Issue tracking
    flag_type = db.Column(db.String(50), nullable=False, index=True)  # safety_concern, donation_issue, organization_issue, user_violation
    severity = db.Column(db.String(20), default='medium', nullable=False)  # low, medium, high, critical
    status = db.Column(db.String(20), default='open', nullable=False, index=True)  # open, in_review, resolved, dismissed
    
    # Details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    # Reporter info
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Resolution
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    donation = db.relationship('Donation', backref='flags', lazy=True)
    organization = db.relationship('Organization', backref='flags', lazy=True)
    flagged_user = db.relationship('User', foreign_keys=[user_id], backref='flags_on_user', lazy=True)
    reporter = db.relationship('User', foreign_keys=[reporter_id], backref='flags_reported', lazy=True)
    resolver = db.relationship('User', foreign_keys=[resolved_by], backref='flags_resolved', lazy=True)

    def __init__(self, flag_type, severity, title, description, 
                 donation_id=None, organization_id=None, user_id=None, reporter_id=None):
        """
        Constructor for Flag.
        
        Args:
            flag_type (str): Type of flag
            severity (str): Severity level
            title (str): Issue title
            description (str): Issue description
            donation_id (str): Donation ID (optional)
            organization_id (int): Organization ID (optional)
            user_id (int): User ID (optional)
            reporter_id (int): Reporter user ID (optional)
        """
        self.flag_type = flag_type
        self.severity = severity
        self.title = title
        self.description = description
        self.donation_id = donation_id
        self.organization_id = organization_id
        self.user_id = user_id
        self.reporter_id = reporter_id

    def create(self):
        """Add flag to database."""
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error creating flag: {e}")
            return None

    def read(self):
        """Convert flag to dictionary."""
        return {
            'id': self.id,
            'flag_type': self.flag_type,
            'severity': self.severity,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'donation_id': self.donation_id,
            'donation_food_name': self.donation.food_name if self.donation else None,
            'organization_id': self.organization_id,
            'organization_name': self.organization.name if self.organization else None,
            'user_id': self.user_id,
            'flagged_user_name': self.flagged_user.name if self.flagged_user else None,
            'reporter_id': self.reporter_id,
            'reporter_name': self.reporter.name if self.reporter else None,
            'resolution_notes': self.resolution_notes,
            'resolved_by': self.resolved_by,
            'resolver_name': self.resolver.name if self.resolver else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def update(self, data):
        """Update flag with new data."""
        try:
            for key, value in data.items():
                if hasattr(self, key) and key not in ['id', 'created_at']:
                    setattr(self, key, value)
            self.updated_at = datetime.utcnow()
            db.session.commit()
            return self
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error updating flag: {e}")
            return None

    def delete(self):
        """Delete flag from database."""
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except IntegrityError as e:
            db.session.rollback()
            print(f"Error deleting flag: {e}")
            return False

    def resolve(self, resolver_id, resolution_notes):
        """Resolve a flag."""
        self.status = 'resolved'
        self.resolved_by = resolver_id
        self.resolution_notes = resolution_notes
        self.resolved_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return self

    def __repr__(self):
        return f"<Flag {self.id} – {self.flag_type} ({self.status})>"
