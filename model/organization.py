# organization.py
"""
Organization Model - Food banks, shelters, restaurants, temples

Organizations receive donations from donors and distribute them to those in need.
"""

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from __init__ import app, db


class Organization(db.Model):
    """
    Organization Model
    
    Represents food distribution organizations: food banks, shelters, restaurants, temples, community centers.
    
    Attributes:
        id (Column): Integer, Primary Key
        name (Column): String(255), Organization name, NOT NULL
        type (Column): String(50), Type of organization (shelter, food_bank, restaurant, temple, community_org)
        address (Column): String(500), Full street address, NOT NULL
        zip_code (Column): String(10), ZIP code, NOT NULL
        capacity (Column): Integer, Number of people served, NULLABLE
        accepted_food_types (Column): JSON, Types of food accepted
        operating_hours (Column): JSON, Weekly operating hours
        contact_info (Column): JSON, Contact details (phone, email, manager)
        is_verified (Column): Boolean, Whether organization is verified by admin
        verification_date (Column): DateTime, When organization was verified
        verified_by (Column): String(100), Admin who verified
        phone (Column): String(20)
        email (Column): String(255)
        website (Column): String(500)
        latitude (Column): Float, For map display
        longitude (Column): Float, For map display
        storage_capacity_lbs (Column): Float, Max food storage capacity
        refrigeration_available (Column): Boolean, Has cold storage
        dietary_restrictions_servable (Column): JSON, Dietary accommodations (vegan, halal, kosher, etc.)
        is_active (Column): Boolean, Whether organization is active
        description (Column): Text, Organization description/mission
        created_at (Column): DateTime, Record creation timestamp
        updated_at (Column): DateTime, Last update timestamp
    """
    __tablename__ = 'organizations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # shelter, food_bank, restaurant, temple, community_org
    address = db.Column(db.String(500), nullable=False)
    zip_code = db.Column(db.String(10), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)  # Number of people served
    
    # Accepted foods
    accepted_food_types = db.Column(db.JSON, nullable=True)  # ['canned', 'fresh-produce', 'dairy', ...]
    
    # Operating info
    operating_hours = db.Column(db.JSON, nullable=True)  # {"monday": {"open": "09:00", "close": "17:00"}, ...}
    contact_info = db.Column(db.JSON, nullable=True)  # {"phone": "...", "email": "...", "manager": "..."}
    
    # Verification
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_date = db.Column(db.DateTime, nullable=True)
    verified_by = db.Column(db.String(100), nullable=True)  # Admin username
    
    # Contact details
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    website = db.Column(db.String(500), nullable=True)
    
    # Location
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    
    # Storage
    storage_capacity_lbs = db.Column(db.Float, nullable=True)  # Maximum storage capacity
    refrigeration_available = db.Column(db.Boolean, default=False, nullable=False)
    
    # Dietary accommodations
    dietary_restrictions_servable = db.Column(db.JSON, nullable=True)  # ['vegan', 'halal', 'kosher', ...]
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.Text, nullable=True)  # Mission statement/description
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(self, name, type, address, zip_code, phone=None, email=None, 
                 capacity=None, accepted_food_types=None, operating_hours=None,
                 contact_info=None, latitude=None, longitude=None,
                 storage_capacity_lbs=None, refrigeration_available=False,
                 dietary_restrictions_servable=None, website=None, description=None):
        """
        Constructor for Organization.
        
        Args:
            name (str): Organization name
            type (str): Type - 'shelter', 'food_bank', 'restaurant', 'temple', 'community_org'
            address (str): Street address
            zip_code (str): ZIP code
            phone (str): Phone number
            email (str): Email address
            capacity (int): Number of people served
            accepted_food_types (list): Types of food accepted
            operating_hours (dict): Weekly hours
            contact_info (dict): Contact information
            latitude (float): Map coordinate
            longitude (float): Map coordinate
            storage_capacity_lbs (float): Max storage
            refrigeration_available (bool): Has cold storage
            dietary_restrictions_servable (list): Dietary accommodations
            website (str): Organization website
            description (str): Org description/mission
        """
        self.name = name
        self.type = type
        self.address = address
        self.zip_code = zip_code
        self.phone = phone
        self.email = email
        self.capacity = capacity
        self.accepted_food_types = accepted_food_types or []
        self.operating_hours = operating_hours or {}
        self.contact_info = contact_info or {'phone': phone, 'email': email}
        self.latitude = latitude
        self.longitude = longitude
        self.storage_capacity_lbs = storage_capacity_lbs
        self.refrigeration_available = refrigeration_available
        self.dietary_restrictions_servable = dietary_restrictions_servable or []
        self.website = website
        self.description = description

    def create(self):
        """
        Add organization to database.
        
        Returns:
            Organization: Created organization or None on error
        """
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def read(self):
        """
        Convert organization to dictionary.
        
        Returns:
            dict: Organization data
        """
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'address': self.address,
            'zip_code': self.zip_code,
            'capacity': self.capacity,
            'accepted_food_types': self.accepted_food_types,
            'operating_hours': self.operating_hours,
            'contact_info': self.contact_info,
            'is_verified': self.is_verified,
            'verification_date': self.verification_date.isoformat() if self.verification_date else None,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'storage_capacity_lbs': self.storage_capacity_lbs,
            'refrigeration_available': self.refrigeration_available,
            'dietary_restrictions_servable': self.dietary_restrictions_servable,
            'is_active': self.is_active,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def update(self, data):
        """
        Update organization with new data.
        
        Args:
            data (dict): Fields to update
        
        Returns:
            Organization: Updated organization or None on error
        """
        try:
            for key, value in data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def delete(self):
        """
        Delete organization from database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            db.session.delete(self)
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False

    def verify(self, verified_by):
        """
        Mark organization as verified by admin.
        
        Args:
            verified_by (str): Admin username
        
        Returns:
            Organization: Updated organization
        """
        self.is_verified = True
        self.verification_date = datetime.utcnow()
        self.verified_by = verified_by
        db.session.commit()
        return self

    def __repr__(self):
        return f"Organization(id={self.id}, name={self.name}, type={self.type}, zip_code={self.zip_code})"


def initOrganizations():
    """
    Initialize organizations table with sample data.
    """
    with app.app_context():
        db.create_all()
        
        # Check if already initialized
        if Organization.query.first():
            return
        
        orgs = [
            Organization(
                name='San Diego Food Bank',
                type='food_bank',
                address='9850 Distribution Ave, San Diego, CA 92121',
                zip_code='92121',
                phone='(619) 527-1419',
                email='info@sdfb.org',
                capacity=5000,
                accepted_food_types=['canned', 'fresh-produce', 'dairy', 'bakery', 'frozen'],
                refrigeration_available=True,
                storage_capacity_lbs=50000,
                latitude=32.8754,
                longitude=-117.2474
            ),
            Organization(
                name='San Diego Rescue Mission',
                type='shelter',
                address='1955 Fifth Ave, San Diego, CA 92101',
                zip_code='92101',
                phone='(619) 235-6000',
                email='info@sdrescue.org',
                capacity=300,
                accepted_food_types=['prepared-meals', 'canned', 'frozen'],
                refrigeration_available=True,
                storage_capacity_lbs=5000,
                latitude=32.7157,
                longitude=-117.1611
            ),
        ]
        
        for org in orgs:
            try:
                org.create()
            except IntegrityError:
                db.session.rollback()
