# donation.py — Week 2: Full lifecycle + audit trail + volunteer assignments
from datetime import datetime, date
from sqlalchemy.exc import IntegrityError
import string
import time
import random

from __init__ import app, db

# ── Allowed enum values ──

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

ALLOWED_STATUSES = [
    'posted', 'claimed', 'in_transit', 'delivered', 'confirmed',
    'expired', 'cancelled'
]

ALLOWED_FOOD_TYPES = [
    'cooked', 'raw', 'packaged', 'perishable', 'non-perishable',
    'baked', 'frozen-prepared', 'canned-goods', 'beverage', 'other'
]

ALLOWED_STORAGE_METHODS = [
    'cooler-with-ice', 'insulated-bag', 'refrigerator', 'freezer',
    'room-temperature-shelf', 'heated-container', 'other'
]

# ── Status transition rules ──

VALID_TRANSITIONS = {
    'posted':     ['claimed', 'cancelled', 'expired'],
    'claimed':    ['in_transit', 'cancelled'],
    'in_transit': ['delivered', 'cancelled'],
    'delivered':  ['confirmed'],
    'confirmed':  [],   # terminal
    'expired':    [],   # terminal
    'cancelled':  [],   # terminal
}


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


# ═══════════════════════════════════════════════════════════════
# Model 1: Donation
# ═══════════════════════════════════════════════════════════════

class Donation(db.Model):
    """
    Represents a food donation with full lifecycle tracking.
    Status flow: posted → claimed → in_transit → delivered → confirmed
    """
    __tablename__ = 'donations'

    id = db.Column(db.String(50), primary_key=True)  # e.g. "HH-M3X7K9-AB2F"

    # ── Food details ──
    food_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    food_type = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit = db.Column(db.String(30), nullable=False)
    serving_count = db.Column(db.Integer, nullable=True)
    weight_lbs = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)

    # ── Safety & handling ──
    expiry_date = db.Column(db.Date, nullable=False)
    storage = db.Column(db.String(30), nullable=False)
    allergens = db.Column(db.JSON, nullable=True)
    allergen_info = db.Column(db.Text, nullable=True)
    dietary_tags = db.Column(db.JSON, nullable=True)
    temperature_at_pickup = db.Column(db.Float, nullable=True)
    storage_method = db.Column(db.String(50), nullable=True)

    # ── Donor info ──
    donor_name = db.Column(db.String(200), nullable=False)
    donor_email = db.Column(db.String(200), nullable=False)
    donor_phone = db.Column(db.String(30), nullable=True)
    donor_zip = db.Column(db.String(10), nullable=False)
    special_instructions = db.Column(db.Text, nullable=True)

    # ── Pickup details ──
    pickup_location = db.Column(db.String(500), nullable=True)
    zip_code = db.Column(db.String(10), nullable=True)
    pickup_window_start = db.Column(db.DateTime, nullable=True)
    pickup_window_end = db.Column(db.DateTime, nullable=True)

    # ── Foreign key relationships ──
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships (use foreign_keys to disambiguate multiple FKs to same table)
    donor = db.relationship('User', foreign_keys=[donor_id], backref='donated', lazy=True)
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref='received_donations', lazy=True)

    # ── Tracking ──
    status = db.Column(db.String(20), default='posted')
    scan_count = db.Column(db.Integer, default=0)

    # ── Lifecycle fields ──
    claimed_by = db.Column(db.String(200), nullable=True)
    claimed_at = db.Column(db.DateTime, nullable=True)
    in_transit_at = db.Column(db.DateTime, nullable=True)
    delivered_by = db.Column(db.String(200), nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    confirmed_by = db.Column(db.String(200), nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    # ── Soft delete ──
    is_archived = db.Column(db.Boolean, default=False)

    # ── Timestamps ──
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Relationships to new Week 2 models ──
    status_logs = db.relationship('DonationStatusLog', backref='donation', lazy=True,
                                   cascade='all, delete-orphan')
    volunteer_assignment = db.relationship('VolunteerAssignment', backref='donation',
                                           uselist=False, lazy=True)

    # Legacy compat columns (kept for migration)
    accepted_by = db.Column(db.String(200), nullable=True)
    accepted_at = db.Column(db.DateTime, nullable=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    volunteer_rel = db.relationship('User', foreign_keys=[volunteer_id],
                                    backref='volunteered_donations', lazy=True)

    def __init__(self, id, food_name, category, quantity, unit, expiry_date, storage,
                 donor_name, donor_email, donor_zip, description='', allergens=None,
                 dietary_tags=None, donor_phone='', special_instructions='',
                 user_id=None, status='posted',
                 food_type=None, allergen_info=None, serving_count=None,
                 weight_lbs=None, pickup_location=None, zip_code=None,
                 pickup_window_start=None, pickup_window_end=None,
                 donor_id=None, receiver_id=None, volunteer_id=None,
                 temperature_at_pickup=None, storage_method=None,
                 # Week 2 lifecycle kwargs
                 claimed_by=None, claimed_at=None, in_transit_at=None,
                 delivered_by=None, delivered_at=None,
                 confirmed_by=None, confirmed_at=None):
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
        # Week 2 lifecycle
        self.claimed_by = claimed_by
        self.claimed_at = claimed_at
        self.in_transit_at = in_transit_at
        self.delivered_by = delivered_by
        self.delivered_at = delivered_at
        self.confirmed_by = confirmed_by
        self.confirmed_at = confirmed_at

    def __repr__(self):
        return f"<Donation {self.id} – {self.food_name} ({self.status})>"

    def to_dict(self):
        """Full serialization including lifecycle fields."""
        return {
            'id': self.id,
            'food_name': self.food_name,
            'category': self.category,
            'food_type': self.food_type,
            'quantity': self.quantity,
            'unit': self.unit,
            'serving_count': self.serving_count,
            'weight_lbs': self.weight_lbs,
            'description': self.description,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'storage': self.storage,
            'allergens': self.allergens or [],
            'allergen_info': self.allergen_info,
            'dietary_tags': self.dietary_tags or [],
            'temperature_at_pickup': self.temperature_at_pickup,
            'storage_method': self.storage_method,
            'donor_name': self.donor_name,
            'donor_email': self.donor_email,
            'donor_phone': self.donor_phone,
            'donor_zip': self.donor_zip,
            'special_instructions': self.special_instructions,
            'pickup_location': self.pickup_location,
            'zip_code': self.zip_code,
            'pickup_window_start': self.pickup_window_start.isoformat() if self.pickup_window_start else None,
            'pickup_window_end': self.pickup_window_end.isoformat() if self.pickup_window_end else None,
            'user_id': self.user_id,
            'donor_id': self.donor_id,
            'receiver_id': self.receiver_id,
            'status': self.status,
            'is_archived': self.is_archived,
            'scan_count': self.scan_count or 0,
            'claimed_by': self.claimed_by,
            'claimed_at': self.claimed_at.isoformat() if self.claimed_at else None,
            'in_transit_at': self.in_transit_at.isoformat() if self.in_transit_at else None,
            'delivered_by': self.delivered_by,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
            'confirmed_by': self.confirmed_by,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_dict_short(self):
        """Compact version for list views."""
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
            'donor_zip': self.donor_zip,
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
                continue
            try:
                expiry = item.get('expiry_date')
                if isinstance(expiry, str):
                    expiry = datetime.strptime(expiry, '%Y-%m-%d').date()
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
                    status=item.get('status', 'posted'),
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
                    claimed_by=item.get('claimed_by'),
                    delivered_by=item.get('delivered_by'),
                    confirmed_by=item.get('confirmed_by'),
                )
                donation.scan_count = item.get('scan_count', 0)
                donation.is_archived = item.get('is_archived', False)
                if item.get('claimed_at'):
                    donation.claimed_at = datetime.fromisoformat(item['claimed_at'])
                if item.get('in_transit_at'):
                    donation.in_transit_at = datetime.fromisoformat(item['in_transit_at'])
                if item.get('delivered_at'):
                    donation.delivered_at = datetime.fromisoformat(item['delivered_at'])
                if item.get('confirmed_at'):
                    donation.confirmed_at = datetime.fromisoformat(item['confirmed_at'])
                db.session.add(donation)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
        return


# ═══════════════════════════════════════════════════════════════
# Model 2: DonationStatusLog — audit trail for every transition
# ═══════════════════════════════════════════════════════════════

class DonationStatusLog(db.Model):
    """
    Tracks every status transition for audit trail.
    """
    __tablename__ = 'donation_status_logs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    donation_id = db.Column(db.String(50), db.ForeignKey('donations.id'), nullable=False)
    old_status = db.Column(db.String(20), nullable=False)
    new_status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.String(200), nullable=True)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'old_status': self.old_status,
            'new_status': self.new_status,
            'changed_by': self.changed_by,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
            'notes': self.notes,
        }


# ═══════════════════════════════════════════════════════════════
# Model 3: VolunteerAssignment — one volunteer per donation
# ═══════════════════════════════════════════════════════════════

class VolunteerAssignment(db.Model):
    """
    Links a volunteer to a donation for pickup/delivery.
    One volunteer per donation (unique constraint prevents double-assign).
    """
    __tablename__ = 'volunteer_assignments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    donation_id = db.Column(db.String(50), db.ForeignKey('donations.id'),
                            nullable=False, unique=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    volunteer_name = db.Column(db.String(200), nullable=False)

    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    picked_up_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'donation_id': self.donation_id,
            'volunteer_id': self.volunteer_id,
            'volunteer_name': self.volunteer_name,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'picked_up_at': self.picked_up_at.isoformat() if self.picked_up_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None,
        }


# ═══════════════════════════════════════════════════════════════
# Helper: log a status change
# ═══════════════════════════════════════════════════════════════

def log_status_change(donation_id, old_status, new_status, changed_by=None, notes=None):
    """Create a DonationStatusLog entry."""
    log = DonationStatusLog(
        donation_id=donation_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by or 'system',
        notes=notes,
    )
    db.session.add(log)


# ═══════════════════════════════════════════════════════════════
# Seed data — 10 sample donations for Week 2
# ═══════════════════════════════════════════════════════════════

def initDonations():
    """Seed 10 sample donations across various statuses for Week 2."""
    from datetime import timedelta

    samples = [
        # 1. Posted — fresh, waiting for a volunteer
        {
            'food_name': 'Canned Tomato Soup',
            'category': 'canned', 'food_type': 'canned-goods',
            'quantity': 24, 'unit': 'cans',
            'serving_count': 48, 'weight_lbs': 18.0,
            'description': "Campbell's condensed, unopened",
            'expiry_date': date.today() + timedelta(days=180),
            'storage': 'room-temp', 'allergens': ['gluten'],
            'allergen_info': 'Contains wheat flour. May contain traces of soy.',
            'dietary_tags': ['vegetarian'],
            'donor_name': 'Local Grocery Co.', 'donor_email': 'donate@localgrocery.com',
            'donor_zip': '92101', 'status': 'posted',
            'pickup_location': '123 Market St, San Diego, CA', 'zip_code': '92101',
            'storage_method': 'room-temperature-shelf',
        },
        # 2. Posted — bakery, expires soon
        {
            'food_name': 'Fresh Bread Loaves',
            'category': 'bakery', 'food_type': 'baked',
            'quantity': 15, 'unit': 'items',
            'serving_count': 150, 'weight_lbs': 22.5,
            'description': 'Whole wheat, baked today',
            'expiry_date': date.today() + timedelta(days=2),
            'storage': 'room-temp', 'allergens': ['gluten'],
            'allergen_info': 'Contains wheat gluten.',
            'dietary_tags': ['vegan'],
            'donor_name': 'Sunrise Bakery', 'donor_email': 'info@sunrisebakery.com',
            'donor_zip': '92102', 'status': 'posted',
            'pickup_location': '456 Bakery Ln, San Diego, CA', 'zip_code': '92102',
            'temperature_at_pickup': 72.0, 'storage_method': 'room-temperature-shelf',
        },
        # 3. Claimed — frozen veggies, volunteer assigned
        {
            'food_name': 'Mixed Frozen Vegetables',
            'category': 'frozen', 'food_type': 'frozen-prepared',
            'quantity': 30, 'unit': 'bags',
            'serving_count': 120, 'weight_lbs': 30.0,
            'description': 'Peas, carrots, corn, green beans',
            'expiry_date': date.today() + timedelta(days=365),
            'storage': 'frozen', 'allergens': ['none'],
            'dietary_tags': ['vegan', 'gluten-free'],
            'donor_name': 'SD Community Farm', 'donor_email': 'farm@sdcommunity.org',
            'donor_zip': '92103', 'status': 'claimed',
            'claimed_by': 'Jane Smith', 'claimed_at': datetime.utcnow() - timedelta(hours=2),
            'pickup_location': '789 Farm Rd, San Diego, CA', 'zip_code': '92103',
            'temperature_at_pickup': 0.0, 'storage_method': 'freezer',
        },
        # 4. In transit — dairy
        {
            'food_name': 'Greek Yogurt Cases',
            'category': 'dairy', 'food_type': 'perishable',
            'quantity': 12, 'unit': 'boxes',
            'serving_count': 72, 'weight_lbs': 24.0,
            'description': 'Chobani vanilla, 6oz cups',
            'expiry_date': date.today() + timedelta(days=14),
            'storage': 'refrigerated', 'allergens': ['dairy'],
            'dietary_tags': ['vegetarian'],
            'donor_name': 'Healthy Foods Inc', 'donor_email': 'give@healthyfoods.com',
            'donor_zip': '92104', 'status': 'in_transit',
            'claimed_by': 'Bob Johnson', 'claimed_at': datetime.utcnow() - timedelta(hours=5),
            'in_transit_at': datetime.utcnow() - timedelta(hours=1),
            'pickup_location': '321 Dairy Dr, San Diego, CA', 'zip_code': '92104',
            'temperature_at_pickup': 38.0, 'storage_method': 'cooler-with-ice',
        },
        # 5. Delivered — meat protein
        {
            'food_name': 'Frozen Chicken Breast',
            'category': 'meat-protein', 'food_type': 'frozen-prepared',
            'quantity': 50, 'unit': 'lbs',
            'serving_count': 100, 'weight_lbs': 50.0,
            'description': 'Boneless skinless, vacuum sealed',
            'expiry_date': date.today() + timedelta(days=90),
            'storage': 'frozen', 'allergens': ['none'],
            'dietary_tags': ['halal'],
            'donor_name': 'Metro Butcher', 'donor_email': 'orders@metrobutcher.com',
            'donor_zip': '92105', 'status': 'delivered',
            'delivered_by': 'Alice Wong', 'delivered_at': datetime.utcnow() - timedelta(hours=3),
            'pickup_location': '555 Meat Ave, San Diego, CA', 'zip_code': '92105',
            'temperature_at_pickup': 0.0, 'storage_method': 'freezer',
        },
        # 6. Confirmed — baby food
        {
            'food_name': 'Organic Baby Food Pouches',
            'category': 'baby-food', 'food_type': 'packaged',
            'quantity': 48, 'unit': 'items',
            'serving_count': 48, 'weight_lbs': 12.0,
            'description': 'Assorted fruits & vegetables, stage 2',
            'expiry_date': date.today() + timedelta(days=270),
            'storage': 'room-temp', 'allergens': ['none'],
            'dietary_tags': ['organic', 'vegan'],
            'donor_name': 'Baby Nourish Co', 'donor_email': 'hello@babynourish.com',
            'donor_zip': '92106', 'status': 'confirmed',
            'confirmed_by': 'Baby Nourish Co', 'confirmed_at': datetime.utcnow() - timedelta(hours=1),
            'pickup_location': '101 Baby Blvd, San Diego, CA', 'zip_code': '92106',
            'storage_method': 'room-temperature-shelf',
        },
        # 7. Posted — beverages
        {
            'food_name': 'Bottled Water Cases',
            'category': 'beverages', 'food_type': 'beverage',
            'quantity': 20, 'unit': 'boxes',
            'serving_count': 480, 'weight_lbs': 200.0,
            'description': '24-pack spring water',
            'expiry_date': date.today() + timedelta(days=730),
            'storage': 'room-temp', 'allergens': ['none'],
            'dietary_tags': ['vegan', 'gluten-free'],
            'donor_name': 'Hydrate Foundation', 'donor_email': 'water@hydrate.org',
            'donor_zip': '92107', 'status': 'posted',
            'pickup_location': '777 Water Way, San Diego, CA', 'zip_code': '92107',
            'storage_method': 'room-temperature-shelf',
        },
        # 8. Expired — grains (past expiry)
        {
            'food_name': 'Quinoa Bulk Bags',
            'category': 'grains', 'food_type': 'non-perishable',
            'quantity': 10, 'unit': 'bags',
            'serving_count': 40, 'weight_lbs': 50.0,
            'description': 'Organic white quinoa, 5lb bags',
            'expiry_date': date.today() - timedelta(days=5),
            'storage': 'cool-dry', 'allergens': ['none'],
            'dietary_tags': ['vegan', 'gluten-free', 'organic'],
            'donor_name': 'Whole Grains Ltd', 'donor_email': 'donate@wholegrains.com',
            'donor_zip': '92108', 'status': 'expired',
            'pickup_location': '888 Grain Blvd, San Diego, CA', 'zip_code': '92108',
            'storage_method': 'room-temperature-shelf',
        },
        # 9. Claimed — prepared meals
        {
            'food_name': 'Chicken Tikka Masala Trays',
            'category': 'prepared-meals', 'food_type': 'cooked',
            'quantity': 25, 'unit': 'trays',
            'serving_count': 25, 'weight_lbs': 37.5,
            'description': 'Restaurant-quality, individually wrapped',
            'expiry_date': date.today() + timedelta(days=5),
            'storage': 'refrigerated', 'allergens': ['dairy', 'gluten'],
            'dietary_tags': ['halal'],
            'donor_name': 'Spice Kitchen', 'donor_email': 'chef@spicekitchen.com',
            'donor_zip': '92109', 'status': 'claimed',
            'claimed_by': 'Food Bank SD', 'claimed_at': datetime.utcnow() - timedelta(hours=6),
            'pickup_location': '999 Spice Ln, San Diego, CA', 'zip_code': '92109',
            'temperature_at_pickup': 40.0, 'storage_method': 'insulated-bag',
        },
        # 10. Posted — snacks
        {
            'food_name': 'Assorted Granola Bars',
            'category': 'snacks', 'food_type': 'packaged',
            'quantity': 100, 'unit': 'items',
            'serving_count': 100, 'weight_lbs': 10.0,
            'description': 'Nature Valley, variety pack',
            'expiry_date': date.today() + timedelta(days=120),
            'storage': 'room-temp', 'allergens': ['nuts', 'gluten'],
            'dietary_tags': ['vegetarian'],
            'donor_name': 'Trail Mix Co', 'donor_email': 'give@trailmix.com',
            'donor_zip': '92110', 'status': 'posted',
            'pickup_location': '202 Trail Rd, San Diego, CA', 'zip_code': '92110',
            'storage_method': 'room-temperature-shelf',
        },
    ]

    with app.app_context():
        db.create_all()
        for s in samples:
            existing = Donation.query.filter_by(
                food_name=s['food_name'], donor_email=s['donor_email']
            ).first()
            if existing:
                continue
            donation = Donation(id=generate_donation_id(), **s)
            try:
                db.session.add(donation)
                log_status_change(donation.id, 'none', s['status'],
                                  s['donor_name'], 'Seeded')
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
        print("✅ Seeded 10 sample donations for Week 2")
