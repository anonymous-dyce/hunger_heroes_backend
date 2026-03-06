# food_safety_log.py
"""
Food Safety Log Model - Temperature, storage method, and inspection records
"""

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from __init__ import app, db


class FoodSafetyLog(db.Model):
    """
    Food Safety Log Model
    
    Records food safety inspections, temperature readings, and compliance data.
    Multiple logs can exist for a single donation.
    
    Attributes:
        id (Column): Integer, Primary Key
        donation_id (Column): String(50), Foreign Key to donations.id
        temperature_reading (Column): Float, Temperature in Celsius/Fahrenheit
        storage_method (Column): String(50), How food was stored
        handling_notes (Column): Text, Notes about how food was handled
        inspector_id (Column): Integer, FK to users.id - Inspector/volunteer
        logged_at (Column): DateTime, When inspection occurred
        passed_inspection (Column): Boolean, Pass or fail
        inspection_date (Column): DateTime
        notes (Column): Text, Additional notes
        created_at (Column): DateTime
    """
    __tablename__ = 'food_safety_logs'

    id = db.Column(db.Integer, primary_key=True)
    donation_id = db.Column(db.String(50), db.ForeignKey('donations.id'), nullable=False, index=True)
    
    # Temperature and storage
    temperature_reading = db.Column(db.Float, nullable=True)  # Celsius or Fahrenheit
    storage_method = db.Column(db.String(50), nullable=True)  # cooler-with-ice, refrigerator, freezer, etc.
    handling_notes = db.Column(db.Text, nullable=True)  # How food was handled, packaged, etc.
    
    # Inspector info
    inspector_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    
    # Status and dates
    logged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # When inspection happened
    passed_inspection = db.Column(db.Boolean, default=True, nullable=False)  # Pass/fail
    inspection_date = db.Column(db.DateTime, nullable=True)  # Date of inspection
    notes = db.Column(db.Text, nullable=True)  # Additional inspection notes
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    donation = db.relationship('Donation', backref='safety_logs', lazy=True)
    inspector = db.relationship('User', backref='inspections', lazy=True)

    def __init__(self, donation_id, temperature_reading=None, storage_method=None,
                 handling_notes=None, inspector_id=None, passed_inspection=True,
                 inspection_date=None, notes=None):
        """
        Constructor for FoodSafetyLog.
        
        Args:
            donation_id (str): ID of donation being logged
            temperature_reading (float): Temperature reading
            storage_method (str): How food was stored
            handling_notes (str): Handling details
            inspector_id (int): User ID of inspector
            passed_inspection (bool): Pass/fail status
            inspection_date (datetime): When inspection occurred
            notes (str): Additional notes
        """
        self.donation_id = donation_id
        self.temperature_reading = temperature_reading
        self.storage_method = storage_method
        self.handling_notes = handling_notes
        self.inspector_id = inspector_id
        self.passed_inspection = passed_inspection
        self.inspection_date = inspection_date
        self.notes = notes

    def create(self):
        """
        Add safety log to database.
        
        Returns:
            FoodSafetyLog: Created log or None on error
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
        Convert safety log to dictionary.
        
        Returns:
            dict: Log data
        """
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'temperature_reading': self.temperature_reading,
            'storage_method': self.storage_method,
            'handling_notes': self.handling_notes,
            'inspector_id': self.inspector_id,
            'inspector_name': self.inspector.name if self.inspector else None,
            'logged_at': self.logged_at.isoformat(),
            'passed_inspection': self.passed_inspection,
            'inspection_date': self.inspection_date.isoformat() if self.inspection_date else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat()
        }

    def update(self, data):
        """
        Update safety log with new data.
        
        Args:
            data (dict): Fields to update
        
        Returns:
            FoodSafetyLog: Updated log or None on error
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
        Delete safety log from database.
        
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

    def is_temperature_safe(self, food_type=None):
        """
        Check if temperature reading is within safe range.
        
        Args:
            food_type (str): Type of food for context
        
        Returns:
            bool: True if temperature is safe
        """
        if self.temperature_reading is None:
            return False
        
        # Assuming reading is in Fahrenheit
        # Perishable foods should be 40°F or below
        # Frozen should be 0°F or below
        if 'frozen' in (self.storage_method or '').lower():
            return self.temperature_reading <= 0
        else:
            return self.temperature_reading <= 40

    def __repr__(self):
        return f"FoodSafetyLog(donation_id={self.donation_id}, passed={self.passed_inspection}, temp={self.temperature_reading})"


def initFoodSafetyLogs():
    """
    Initialize food safety logs table.
    """
    with app.app_context():
        db.create_all()
