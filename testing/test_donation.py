"""
Unit tests for the Donation model — creation, update, and deletion.

Run from project root:
    python -m pytest testing/test_donation.py -v
"""

import sys
import os
import pytest
from datetime import date, datetime, timedelta

# Ensure project root is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from __init__ import app, db  # noqa: E402
from model.donation import Donation, generate_donation_id  # noqa: E402
# Import all models so that db.create_all() can resolve every relationship/FK
from model.user import User  # noqa: E402,F401
from model.post import Post  # noqa: E402,F401


@pytest.fixture(autouse=True)
def setup_db():
    """Create a fresh in-memory database for each test."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield
        db.session.rollback()
        db.drop_all()


# ──────────────────────────────────────────────────
# 1. Test: Model creation with all new fields
# ──────────────────────────────────────────────────
def test_donation_creation_full_fields():
    """Verify that a Donation can be created with all original + new fields."""
    with app.app_context():
        d = Donation(
            id=generate_donation_id(),
            food_name='Veggie Tray',
            category='fresh-produce',
            food_type='raw',
            quantity=10,
            unit='trays',
            serving_count=50,
            weight_lbs=15.5,
            description='Assorted raw veggies with hummus',
            expiry_date=date.today() + timedelta(days=2),
            storage='refrigerated',
            allergens=['nuts'],
            allergen_info='Contains tree nuts in hummus.',
            dietary_tags=['vegan', 'gluten-free'],
            temperature_at_pickup=38.0,
            storage_method='cooler-with-ice',
            donor_name='Green Garden',
            donor_email='info@greengarden.com',
            donor_phone='555-0100',
            donor_zip='92101',
            pickup_location='100 Veggie St, San Diego, CA',
            zip_code='92101',
            pickup_window_start=datetime(2026, 3, 5, 9, 0),
            pickup_window_end=datetime(2026, 3, 5, 17, 0),
            special_instructions='Keep cold',
        )
        db.session.add(d)
        db.session.commit()

        fetched = Donation.query.get(d.id)
        assert fetched is not None
        assert fetched.food_name == 'Veggie Tray'
        assert fetched.food_type == 'raw'
        assert fetched.serving_count == 50
        assert fetched.weight_lbs == 15.5
        assert fetched.allergen_info == 'Contains tree nuts in hummus.'
        assert fetched.temperature_at_pickup == 38.0
        assert fetched.storage_method == 'cooler-with-ice'
        assert fetched.pickup_location == '100 Veggie St, San Diego, CA'
        assert fetched.zip_code == '92101'
        assert fetched.pickup_window_start == datetime(2026, 3, 5, 9, 0)
        assert fetched.pickup_window_end == datetime(2026, 3, 5, 17, 0)
        assert fetched.status == 'active'
        assert fetched.is_archived is False

        # Verify to_dict includes new keys
        data = fetched.to_dict()
        assert 'food_type' in data
        assert 'serving_count' in data
        assert 'weight_lbs' in data
        assert 'allergen_info' in data
        assert 'temperature_at_pickup' in data
        assert 'storage_method' in data
        assert 'pickup_location' in data
        assert 'zip_code' in data
        assert 'pickup_window_start' in data
        assert 'pickup_window_end' in data
        assert 'donor_id' in data
        assert 'receiver_id' in data
        assert 'volunteer_id' in data
        assert 'is_archived' in data


# ──────────────────────────────────────────────────
# 2. Test: Model update (modify fields + archive)
# ──────────────────────────────────────────────────
def test_donation_update():
    """Verify that a Donation's fields can be updated and persisted."""
    with app.app_context():
        d = Donation(
            id=generate_donation_id(),
            food_name='Bread Rolls',
            category='bakery',
            quantity=20,
            unit='items',
            expiry_date=date.today() + timedelta(days=5),
            storage='room-temp',
            donor_name='Corner Bakery',
            donor_email='cb@example.com',
            donor_zip='92102',
        )
        db.session.add(d)
        db.session.commit()

        # Update several fields including new ones
        d.food_type = 'baked'
        d.serving_count = 40
        d.weight_lbs = 10.0
        d.allergen_info = 'Contains wheat gluten'
        d.temperature_at_pickup = 70.0
        d.storage_method = 'insulated-bag'
        d.pickup_location = '55 Bakery Rd'
        d.zip_code = '92102'
        d.pickup_window_start = datetime(2026, 3, 6, 8, 0)
        d.pickup_window_end = datetime(2026, 3, 6, 12, 0)
        d.status = 'accepted'
        d.accepted_by = 'Food Bank #3'
        d.accepted_at = datetime.utcnow()
        db.session.commit()

        fetched = Donation.query.get(d.id)
        assert fetched.food_type == 'baked'
        assert fetched.serving_count == 40
        assert fetched.weight_lbs == 10.0
        assert fetched.allergen_info == 'Contains wheat gluten'
        assert fetched.temperature_at_pickup == 70.0
        assert fetched.storage_method == 'insulated-bag'
        assert fetched.status == 'accepted'
        assert fetched.accepted_by == 'Food Bank #3'

        # Test soft-delete (archive)
        fetched.is_archived = True
        fetched.status = 'archived'
        db.session.commit()

        archived = Donation.query.get(d.id)
        assert archived.is_archived is True
        assert archived.status == 'archived'


# ──────────────────────────────────────────────────
# 3. Test: Model deletion (hard delete)
# ──────────────────────────────────────────────────
def test_donation_deletion():
    """Verify that a Donation can be permanently deleted from the database."""
    with app.app_context():
        d = Donation(
            id=generate_donation_id(),
            food_name='Canned Beans',
            category='canned',
            quantity=50,
            unit='cans',
            expiry_date=date.today() + timedelta(days=365),
            storage='room-temp',
            donor_name='Bean Co.',
            donor_email='beans@example.com',
            donor_zip='92103',
        )
        db.session.add(d)
        db.session.commit()
        donation_id = d.id

        assert Donation.query.get(donation_id) is not None

        db.session.delete(d)
        db.session.commit()

        assert Donation.query.get(donation_id) is None


# ──────────────────────────────────────────────────
# 4. Test: to_dict_short includes new fields
# ──────────────────────────────────────────────────
def test_to_dict_short_includes_new_fields():
    """Verify to_dict_short returns the expanded compact schema."""
    with app.app_context():
        d = Donation(
            id=generate_donation_id(),
            food_name='Pasta Box',
            category='grains',
            food_type='non-perishable',
            quantity=12,
            unit='boxes',
            serving_count=48,
            weight_lbs=8.0,
            expiry_date=date.today() + timedelta(days=200),
            storage='cool-dry',
            donor_name='Pantry Helper',
            donor_email='ph@example.com',
            donor_zip='92104',
            pickup_location='321 Pasta Pl',
            zip_code='92104',
        )
        db.session.add(d)
        db.session.commit()

        short = d.to_dict_short()
        assert short['food_type'] == 'non-perishable'
        assert short['serving_count'] == 48
        assert short['weight_lbs'] == 8.0
        assert short['pickup_location'] == '321 Pasta Pl'
        assert short['zip_code'] == '92104'
        assert short['is_archived'] is False


# ──────────────────────────────────────────────────
# 5. Test: Backward compatibility — minimal creation
# ──────────────────────────────────────────────────
def test_donation_creation_minimal_backward_compatible():
    """Verify old-style creation (without new fields) still works."""
    with app.app_context():
        d = Donation(
            id=generate_donation_id(),
            food_name='Mystery Food',
            category='other',
            quantity=1,
            unit='items',
            expiry_date=date.today() + timedelta(days=30),
            storage='room-temp',
            donor_name='Anon',
            donor_email='anon@example.com',
            donor_zip='00000',
        )
        db.session.add(d)
        db.session.commit()

        fetched = Donation.query.get(d.id)
        assert fetched is not None
        # All new nullable fields should be None / default
        assert fetched.food_type is None
        assert fetched.serving_count is None
        assert fetched.weight_lbs is None
        assert fetched.allergen_info is None
        assert fetched.temperature_at_pickup is None
        assert fetched.storage_method is None
        assert fetched.pickup_location is None
        assert fetched.zip_code is None
        assert fetched.pickup_window_start is None
        assert fetched.pickup_window_end is None
        assert fetched.donor_id is None
        assert fetched.receiver_id is None
        assert fetched.volunteer_id is None
        assert fetched.is_archived is False
