# donation.py
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
import string
import time
import random

from __init__ import app, db

# Allowed enum values
ALLOWED_CATEGORIES = [
    'canned', 'fresh-produce', 'dairy', 'bakery', 'meat-protein',
    'grains', 'beverages', 'frozen', 'snacks', 'baby-food',
    'prepared-meals', 'other'
]

ALLOWED_UNITS = [
    'items', 'lbs', 'kg', 'oz', 'cans', 'boxes', 'bags', 'trays', 'servings'
]

ALLOWED_STORAGE = ['room-temp', 'refrigerated', 'frozen', 'cool-dry']

ALLOWED_ALLERGENS = [
    'gluten', 'dairy', 'nuts', 'soy', 'eggs', 'shellfish', 'fish', 'none'
]

ALLOWED_DIETARY = [
    'vegetarian', 'vegan', 'halal', 'kosher', 'gluten-free', 'organic'
]

ALLOWED_STATUSES = ['active', 'accepted', 'delivered', 'expired', 'cancelled', 'archived']

ALLOWED_FOOD_TYPES = [
    'cooked', 'raw', 'packaged', 'perishable', 'non-perishable',
    'baked', 'frozen-prepared', 'canned-goods', 'beverage', 'other'
]

ALLOWED_STORAGE_METHODS = [
    'cooler-with-ice', 'insulated-bag', 'refrigerator', 'freezer',
    'room-temperature-shelf', 'heated-container', 'other'
]


def generate_donation_id():
    """Generate a unique human-readable donation ID in the format HH-XXXXXX-XXXX."""
    timestamp = int(time.time() * 1000)
    base36 = ''
    chars = string.digits + string.ascii_uppercase
    while timestamp:
        timestamp, remainder = divmod(timestamp, 36)
        base36 = chars[remainder] + base36
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"HH-{base36[-6:]}-{suffix}"


class Donation(db.Model):
    """
    Donation Model
    
    Represents a food donation with barcode label data for the Hunger Heroes system.
    Tracks food details, donor info, safety/handling requirements, and acceptance status.
    """
    __tablename__ = 'donations'

    id = db.Column(db.String(50), primary_key=True)  # e.g. "HH-M3X7K9-AB2F"

    # Food details
    food_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    food_type = db.Column(db.String(50), nullable=True)  # cooked, raw, packaged, etc.
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    serving_count = db.Column(db.Integer, nullable=True)  # estimated number of servings
    weight_lbs = db.Column(db.Float, nullable=True)  # weight in pounds
    description = db.Column(db.Text, nullable=True)

    # Safety & handling
    expiry_date = db.Column(db.Date, nullable=False)
    storage = db.Column(db.String(30), nullable=False)
    allergens = db.Column(db.JSON, nullable=True)
    allergen_info = db.Column(db.Text, nullable=True)  # free-text allergen notes
    dietary_tags = db.Column(db.JSON, nullable=True)  # vegetarian, vegan, halal, kosher, etc.

    # Food safety compliance
    temperature_at_pickup = db.Column(db.Float, nullable=True)  # °F at time of pickup
    storage_method = db.Column(db.String(50), nullable=True)  # how food is stored during transit

    # Donor info
    donor_name = db.Column(db.String(200), nullable=False)
    donor_email = db.Column(db.String(200), nullable=False)
    donor_phone = db.Column(db.String(30), nullable=True)
    donor_zip = db.Column(db.String(10), nullable=False)
    special_instructions = db.Column(db.Text, nullable=True)

    # Pickup details
    pickup_location = db.Column(db.String(500), nullable=True)  # full address for pickup
    zip_code = db.Column(db.String(10), nullable=True)  # pickup zip code (may differ from donor_zip)
    pickup_window_start = db.Column(db.DateTime, nullable=True)  # earliest pickup time
    pickup_window_end = db.Column(db.DateTime, nullable=True)  # latest pickup time

    # Foreign key relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # legacy creator link
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # donor user account
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # receiving org/user
    volunteer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # volunteer courier

    # Relationships (use foreign_keys to disambiguate multiple FKs to same table)
    donor = db.relationship('User', foreign_keys=[donor_id], backref='donated', lazy=True)
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_donations', lazy=True)
    volunteer = db.relationship('User', foreign_keys=[volunteer_id], backref='volunteered_donations', lazy=True)

    # Tracking
    status = db.Column(db.String(20), default='active')
    is_archived = db.Column(db.Boolean, default=False)  # soft-delete flag for cleanup
    accepted_by = db.Column(db.String(200), nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    delivered_by = db.Column(db.String(200), nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    scan_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, id, food_name, category, quantity, unit, expiry_date, storage,
                 donor_name, donor_email, donor_zip, description='', allergens=None,
                 dietary_tags=None, donor_phone='', special_instructions='',
                 user_id=None, status='active',
                 # New fields
                 food_type=None, allergen_info=None, serving_count=None,
                 weight_lbs=None, pickup_location=None, zip_code=None,
                 pickup_window_start=None, pickup_window_end=None,
                 donor_id=None, receiver_id=None, volunteer_id=None,
                 temperature_at_pickup=None, storage_method=None):
        self.id = id
        self.food_name = food_name
        self.category = category
        self.food_type = food_type
        self.quantity = quantity
        self.unit = unit
        self.serving_count = serving_count
        self.weight_lbs = weight_lbs
        self.description = description
        self.expiry_date = expiry_date
        self.storage = storage
        self.allergens = allergens or []
        self.allergen_info = allergen_info
        self.dietary_tags = dietary_tags or []
        self.temperature_at_pickup = temperature_at_pickup
        self.storage_method = storage_method
        self.donor_name = donor_name
        self.donor_email = donor_email
        self.donor_phone = donor_phone
        self.donor_zip = donor_zip
        self.special_instructions = special_instructions
        self.pickup_location = pickup_location
        self.zip_code = zip_code
        self.pickup_window_start = pickup_window_start
        self.pickup_window_end = pickup_window_end
        self.user_id = user_id
        self.donor_id = donor_id
        self.receiver_id = receiver_id
        self.volunteer_id = volunteer_id
        self.status = status

    def __repr__(self):
        return f"<Donation {self.id} – {self.food_name} ({self.status})>"

    def to_dict(self):
        """Serialize the donation to a dictionary."""
        return {
            'id': self.id,
            # Food details
            'food_name': self.food_name,
            'category': self.category,
            'food_type': self.food_type,
            'quantity': self.quantity,
            'unit': self.unit,
            'serving_count': self.serving_count,
            'weight_lbs': self.weight_lbs,
            'description': self.description,
            # Safety & handling
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'storage': self.storage,
            'allergens': self.allergens or [],
            'allergen_info': self.allergen_info,
            'dietary_tags': self.dietary_tags or [],
            'temperature_at_pickup': self.temperature_at_pickup,
            'storage_method': self.storage_method,
            # Donor info
            'donor_name': self.donor_name,
            'donor_email': self.donor_email,
            'donor_phone': self.donor_phone,
            'donor_zip': self.donor_zip,
            'special_instructions': self.special_instructions,
            # Pickup details
            'pickup_location': self.pickup_location,
            'zip_code': self.zip_code,
            'pickup_window_start': self.pickup_window_start.isoformat() if self.pickup_window_start else None,
            'pickup_window_end': self.pickup_window_end.isoformat() if self.pickup_window_end else None,
            # Relationships
            'user_id': self.user_id,
            'donor_id': self.donor_id,
            'receiver_id': self.receiver_id,
            'volunteer_id': self.volunteer_id,
            # Tracking
            'status': self.status,
            'is_archived': self.is_archived,
            'scan_count': self.scan_count or 0,
            'accepted_by': self.accepted_by,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
            'delivered_by': self.delivered_by,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_short(self):
        """Serialize a compact version for list views."""
        return {
            'id': self.id,
            'food_name': self.food_name,
            'category': self.category,
            'food_type': self.food_type,
            'quantity': self.quantity,
            'unit': self.unit,
            'serving_count': self.serving_count,
            'weight_lbs': self.weight_lbs,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'status': self.status,
            'is_archived': self.is_archived,
            'pickup_location': self.pickup_location,
            'zip_code': self.zip_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def read(self):
        """Alias for to_dict for consistency with other models."""
        return self.to_dict()

    @staticmethod
    def restore(data):
        """Restore donations from a list of dictionaries."""
        for item in data:
            donation = Donation.query.get(item.get('id'))
            if donation:
                continue  # skip if already exists
            try:
                expiry = item.get('expiry_date')
                if isinstance(expiry, str):
                    expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
                # Parse pickup window datetimes if present
                pw_start = item.get('pickup_window_start')
                if isinstance(pw_start, str):
                    pw_start = datetime.fromisoformat(pw_start)
                pw_end = item.get('pickup_window_end')
                if isinstance(pw_end, str):
                    pw_end = datetime.fromisoformat(pw_end)

                donation = Donation(
                    id=item['id'],
                    food_name=item['food_name'],
                    category=item['category'],
                    quantity=item['quantity'],
                    unit=item['unit'],
                    expiry_date=expiry,
                    storage=item['storage'],
                    donor_name=item['donor_name'],
                    donor_email=item['donor_email'],
                    donor_zip=item['donor_zip'],
                    description=item.get('description', ''),
                    allergens=item.get('allergens', []),
                    dietary_tags=item.get('dietary_tags', []),
                    donor_phone=item.get('donor_phone', ''),
                    special_instructions=item.get('special_instructions', ''),
                    user_id=item.get('user_id'),
                    status=item.get('status', 'active'),
                    # New fields
                    food_type=item.get('food_type'),
                    allergen_info=item.get('allergen_info'),
                    serving_count=item.get('serving_count'),
                    weight_lbs=item.get('weight_lbs'),
                    pickup_location=item.get('pickup_location'),
                    zip_code=item.get('zip_code'),
                    pickup_window_start=pw_start,
                    pickup_window_end=pw_end,
                    donor_id=item.get('donor_id'),
                    receiver_id=item.get('receiver_id'),
                    volunteer_id=item.get('volunteer_id'),
                    temperature_at_pickup=item.get('temperature_at_pickup'),
                    storage_method=item.get('storage_method'),
                )
                donation.scan_count = item.get('scan_count', 0)
                donation.is_archived = item.get('is_archived', False)
                donation.accepted_by = item.get('accepted_by')
                if item.get('accepted_at'):
                    donation.accepted_at = datetime.fromisoformat(item['accepted_at'])
                donation.delivered_by = item.get('delivered_by')
                if item.get('delivered_at'):
                    donation.delivered_at = datetime.fromisoformat(item['delivered_at'])
                db.session.add(donation)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
        return


def initDonations():
    """Seed sample donations for development."""
    from datetime import timedelta

    samples = [
        {
            'food_name': 'Canned Tomato Soup',
            'category': 'canned',
            'food_type': 'canned-goods',
            'quantity': 24,
            'unit': 'cans',
            'serving_count': 48,
            'weight_lbs': 18.0,
            'description': "Campbell's condensed, unopened",
            'expiry_date': date.today() + timedelta(days=180),
            'storage': 'room-temp',
            'allergens': ['gluten'],
            'allergen_info': 'Contains wheat flour. May contain traces of soy.',
            'dietary_tags': ['vegetarian'],
            'donor_name': 'Local Grocery Co.',
            'donor_email': 'donate@localgrocery.com',
            'donor_zip': '92101',
            'pickup_location': '123 Market St, San Diego, CA',
            'zip_code': '92101',
            'storage_method': 'room-temperature-shelf',
        },
        {
            'food_name': 'Fresh Bread Loaves',
            'category': 'bakery',
            'food_type': 'baked',
            'quantity': 15,
            'unit': 'items',
            'serving_count': 150,
            'weight_lbs': 22.5,
            'description': 'Whole wheat, baked today',
            'expiry_date': date.today() + timedelta(days=3),
            'storage': 'room-temp',
            'allergens': ['gluten'],
            'allergen_info': 'Contains wheat gluten.',
            'dietary_tags': ['vegan'],
            'donor_name': 'Sunrise Bakery',
            'donor_email': 'info@sunrisebakery.com',
            'donor_zip': '92102',
            'pickup_location': '456 Bakery Ln, San Diego, CA',
            'zip_code': '92102',
            'temperature_at_pickup': 72.0,
            'storage_method': 'room-temperature-shelf',
        },
        {
            'food_name': 'Mixed Frozen Vegetables',
            'category': 'frozen',
            'food_type': 'frozen-prepared',
            'quantity': 30,
            'unit': 'bags',
            'serving_count': 120,
            'weight_lbs': 30.0,
            'description': 'Peas, carrots, corn, green beans',
            'expiry_date': date.today() + timedelta(days=365),
            'storage': 'frozen',
            'allergens': ['none'],
            'dietary_tags': ['vegan', 'gluten-free'],
            'donor_name': 'SD Community Farm',
            'donor_email': 'farm@sdcommunity.org',
            'donor_zip': '92103',
            'pickup_location': '789 Farm Rd, San Diego, CA',
            'zip_code': '92103',
            'temperature_at_pickup': 0.0,
            'storage_method': 'freezer',
        },
        {
            'food_name': 'Organic Baby Food Pouches',
            'category': 'baby-food',
            'food_type': 'packaged',
            'quantity': 48,
            'unit': 'items',
            'serving_count': 48,
            'weight_lbs': 12.0,
            'description': 'Assorted fruit & veggie purees',
            'expiry_date': date.today() + timedelta(days=90),
            'storage': 'room-temp',
            'allergens': ['none'],
            'dietary_tags': ['organic', 'vegan'],
            'donor_name': 'Happy Baby Foundation',
            'donor_email': 'give@happybaby.org',
            'donor_zip': '92104',
            'pickup_location': '101 Baby Blvd, San Diego, CA',
            'zip_code': '92104',
            'storage_method': 'room-temperature-shelf',
        },
        {
            'food_name': 'Rice & Pasta Variety Pack',
            'category': 'grains',
            'food_type': 'non-perishable',
            'quantity': 20,
            'unit': 'boxes',
            'serving_count': 80,
            'weight_lbs': 25.0,
            'description': 'Brown rice, penne, spaghetti',
            'expiry_date': date.today() + timedelta(days=270),
            'storage': 'cool-dry',
            'allergens': ['gluten'],
            'allergen_info': 'Contains wheat. Produced in facility that processes eggs.',
            'dietary_tags': ['vegan', 'halal', 'kosher'],
            'donor_name': 'Pantry Plus',
            'donor_email': 'donations@pantryplus.com',
            'donor_zip': '92105',
            'pickup_location': '202 Grain Ave, San Diego, CA',
            'zip_code': '92105',
            'storage_method': 'room-temperature-shelf',
        },
    ]

    with app.app_context():
        db.create_all()
        for s in samples:
            existing = Donation.query.filter_by(food_name=s['food_name'], donor_email=s['donor_email']).first()
            if existing:
                continue
            donation = Donation(
                id=generate_donation_id(),
                status='active',
                **s
            )
            try:
                db.session.add(donation)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
        print("✅ Seeded sample donations")
