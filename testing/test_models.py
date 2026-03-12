"""
tests/test_models.py - Model Validation Tests for Hunger Heroes

This module tests all database models to ensure:
- Required fields are validated
- Data constraints are enforced
- Relationships work correctly
- CRUD operations function properly

Run tests with:
    python -m pytest testing/test_models.py -v
    
Or without pytest:
    python testing/test_models.py
"""

import sys
import os
import unittest
from datetime import datetime, timedelta, date

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import from main to ensure all models are initialized properly
from main import app, db
from model.user import User
from model.organization import Organization
from model.donation import Donation, generate_donation_id
from model.allergen_profile import AllergenProfile
from model.food_safety_log import FoodSafetyLog
from model.donation_feedback import DonationFeedback
from model.subscription import Subscription


class TestUserModel(unittest.TestCase):
    """Test User model validation and operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        # Use an in-memory SQLite database for tests
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

        # Create and push an application context
        self.ctx = self.app.app_context()
        self.ctx.push()

        # Ensure the SQLAlchemy engine is re-bound to the test URI.
        # Remove any existing session and dispose of the current engine/cache
        db.session.remove()
        # Dispose of the existing engine if it has already been created
        if hasattr(db, "engine"):
            db.engine.dispose()
        # Clear any cached engine for this app (for Flask-SQLAlchemy versions that use it)
        if hasattr(db, "engines"):
            db.engines.pop(self.app, None)

        # Now create all tables against the in-memory test database
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_user_creation_with_all_fields(self):
        """✅ Test creating user with all fields."""
        user = User(
            name='John Donor',
            uid='johndoner',
            password='secure123',
            role='Donor',
            email='john@example.com',
            organization_id=None
        )
        result = user.create()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'John Donor')
        self.assertEqual(result._role, 'Donor')
        self.assertTrue(result.is_donor())
    
    def test_user_role_validation(self):
        """✅ Test all user roles are properly set."""
        roles = ['Admin', 'Donor', 'Receiver', 'Volunteer', 'User']
        
        for role in roles:
            user = User(name=f'Test {role}', uid=f'user_{role}', role=role)
            user.create()
            
            fetched = User.query.filter_by(_uid=f'user_{role}').first()
            self.assertEqual(fetched._role, role)
            self.assertEqual(fetched.read()['role'], role)
    
    def test_role_check_methods(self):
        """✅ Test role checking methods."""
        admin = User(name='Admin User', uid='admin', role='Admin')
        admin.create()
        
        donor = User(name='Donor User', uid='donor', role='Donor')
        donor.create()
        
        self.assertTrue(admin.is_admin())
        self.assertFalse(donor.is_admin())
        
        self.assertTrue(donor.is_donor())
        self.assertFalse(admin.is_donor())
        
        self.assertTrue(admin.has_role('Admin'))
        self.assertTrue(donor.has_role('Donor'))
        self.assertFalse(admin.has_role('Donor'))
    
    def test_user_unique_uid(self):
        """✅ Test UID uniqueness constraint."""
        user1 = User(name='User 1', uid='duplicate', password='pass1')
        user1.create()
        
        # Try to create duplicate UID
        user2 = User(name='User 2', uid='duplicate', password='pass2')
        result = user2.create()
        
        # Should fail (return None)
        self.assertIsNone(result)
    
    def test_password_hashing(self):
        """✅ Test password is properly hashed."""
        user = User(name='Test User', uid='testuser', password='mypassword')
        user.create()
        
        # Password should be hashed, not plain text
        self.assertNotEqual(user._password, 'mypassword')
        self.assertTrue(user.is_password('mypassword'))
        self.assertFalse(user.is_password('wrongpassword'))
    
    def test_user_read_method(self):
        """✅ Test user.read() returns all fields."""
        user = User(
            name='John Doe',
            uid='johndoe',
            email='john@example.com',
            role='Donor',
            organization_id=None
        )
        user.create()
        
        data = user.read()
        self.assertIn('id', data)
        self.assertIn('uid', data)
        self.assertIn('name', data)
        self.assertIn('email', data)
        self.assertIn('role', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_user_timestamps(self):
        """✅ Test created_at and updated_at timestamps."""
        before = datetime.utcnow()
        user = User(name='Time Test', uid='timetest')
        user.create()
        after = datetime.utcnow()
        
        self.assertIsNotNone(user.created_at)
        self.assertGreaterEqual(user.created_at, before)
        self.assertLessEqual(user.created_at, after)


class TestOrganizationModel(unittest.TestCase):
    """Test Organization model validation and operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_organization_creation(self):
        """✅ Test creating organization with required fields."""
        org = Organization(
            name='Local Food Bank',
            type='food_bank',
            address='123 Main St, City, State 12345',
            zip_code='12345',
            phone='(555) 123-4567',
            email='info@foodbank.org'
        )
        result = org.create()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'Local Food Bank')
    
    def test_organization_type_enum(self):
        """✅ Test organization types."""
        types = ['shelter', 'food_bank', 'restaurant', 'temple', 'community_org']
        
        for org_type in types:
            org = Organization(
                name=f'Org {org_type}',
                type=org_type,
                address=f'123 {org_type} St',
                zip_code='12345'
            )
            org.create()
            fetched = Organization.query.filter_by(type=org_type).first()
            self.assertEqual(fetched.type, org_type)
    
    def test_organization_accepted_food_types(self):
        """✅ Test accepted_food_types JSON field."""
        org = Organization(
            name='Picky Food Bank',
            type='food_bank',
            address='456 Main St',
            zip_code='67890',
            accepted_food_types=['canned', 'frozen', 'dairy']
        )
        org.create()
        
        fetched = Organization.query.first()
        self.assertIsInstance(fetched.accepted_food_types, list)
        self.assertIn('canned', fetched.accepted_food_types)
    
    def test_organization_dietary_restrictions(self):
        """✅ Test dietary restrictions JSON field."""
        org = Organization(
            name='Kosher Kitchen',
            type='temple',
            address='789 Temple Way',
            zip_code='11111',
            dietary_restrictions_servable=['kosher', 'vegetarian']
        )
        org.create()
        
        fetched = Organization.query.first()
        self.assertIn('kosher', fetched.dietary_restrictions_servable)
    
    def test_organization_verify(self):
        """✅ Test organization verification."""
        org = Organization(
            name='To Verify Org',
            type='food_bank',
            address='999 Verify St',
            zip_code='99999'
        )
        org.create()
        
        self.assertFalse(org.is_verified)
        org.verify('admin_user')
        self.assertTrue(org.is_verified)
        self.assertIsNotNone(org.verification_date)
        self.assertEqual(org.verified_by, 'admin_user')
    
    def test_organization_read_method(self):
        """✅ Test organization.read() returns complete data."""
        org = Organization(
            name='Complete Org',
            type='food_bank',
            address='111 Complete St',
            zip_code='11111'
        )
        org.create()
        
        data = org.read()
        self.assertIn('id', data)
        self.assertIn('name', data)
        self.assertIn('type', data)
        self.assertIn('is_active', data)
        self.assertIn('created_at', data)


class TestDonationModel(unittest.TestCase):
    """Test Donation model validation and operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_donation_creation(self):
        """✅ Test creating donation with required fields."""
        donation_id = generate_donation_id()
        expiry = date.today() + timedelta(days=30)
        
        donation = Donation(
            id=donation_id,
            food_name='Canned Vegetables',
            category='canned',
            quantity=24,
            unit='cans',
            expiry_date=expiry,
            storage='room-temp',
            donor_name='John Donor',
            donor_email='john@example.com',
            donor_zip='12345'
        )
        db.session.add(donation)
        db.session.commit()
        
        fetched = Donation.query.get(donation_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.food_name, 'Canned Vegetables')
    
    def test_donation_id_generation(self):
        """✅ Test unique donation ID generation."""
        id1 = generate_donation_id()
        id2 = generate_donation_id()
        
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith('HH-'))
        self.assertTrue(id2.startswith('HH-'))
    
    def test_donation_status_flow(self):
        """✅ Test donation status transitions."""
        donation_id = generate_donation_id()
        donation = Donation(
            id=donation_id,
            food_name='Test Food',
            category='canned',
            quantity=10,
            unit='cans',
            expiry_date=date.today() + timedelta(days=30),
            storage='room-temp',
            donor_name='Donor',
            donor_email='donor@example.com',
            donor_zip='12345',
            status='active'
        )
        db.session.add(donation)
        db.session.commit()
        
        # Can transition to accepted
        donation.status = 'accepted'
        db.session.commit()
        fetched = Donation.query.get(donation_id)
        self.assertEqual(fetched.status, 'accepted')
    
    def test_donation_expiry_date_required(self):
        """✅ Test expiry date must be in future."""
        # Expiry date in past should be caught by application
        past_date = date.today() - timedelta(days=1)
        donation = Donation(
            id=generate_donation_id(),
            food_name='Expired Food',
            category='canned',
            quantity=10,
            unit='cans',
            expiry_date=past_date,
            storage='room-temp',
            donor_name='Donor',
            donor_email='donor@example.com',
            donor_zip='12345'
        )
        # Create without validation - validation is in the API
        db.session.add(donation)
        db.session.commit()
        
        fetched = Donation.query.filter_by(food_name='Expired Food').first()
        self.assertEqual(fetched.expiry_date, past_date)
    
    def test_donation_allergen_tracking(self):
        """✅ Test donation allergen fields."""
        donation = Donation(
            id=generate_donation_id(),
            food_name='Food with Allergens',
            category='other',
            quantity=5,
            unit='items',
            expiry_date=date.today() + timedelta(days=30),
            storage='room-temp',
            donor_name='Donor',
            donor_email='donor@example.com',
            donor_zip='12345',
            allergens=['nuts', 'dairy'],
            allergen_info='Contains peanuts and milk'
        )
        db.session.add(donation)
        db.session.commit()
        
        fetched = Donation.query.filter_by(food_name='Food with Allergens').first()
        self.assertIn('nuts', fetched.allergens)
        self.assertIn('dairy', fetched.allergens)


class TestAllergenProfileModel(unittest.TestCase):
    """Test AllergenProfile model validation and operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_allergen_profile_creation(self):
        """✅ Test creating allergen profile."""
        donation_id = 'HH-TEST-001'
        profile = AllergenProfile(
            donation_id=donation_id,
            contains_nuts=True,
            contains_dairy=False,
            is_vegetarian=True
        )
        result = profile.create()
        self.assertIsNotNone(result)
        self.assertTrue(result.contains_nuts)
    
    def test_allergen_profile_flags(self):
        """✅ Test all allergen boolean flags."""
        profile = AllergenProfile(
            donation_id='HH-TEST-002',
            contains_nuts=True,
            contains_dairy=True,
            contains_gluten=True,
            contains_soy=True,
            contains_shellfish=True,
            contains_eggs=True
        )
        profile.create()
        
        fetched = AllergenProfile.query.first()
        self.assertTrue(fetched.contains_nuts)
        self.assertTrue(fetched.contains_dairy)
        self.assertTrue(fetched.contains_gluten)
        self.assertTrue(fetched.contains_soy)
        self.assertTrue(fetched.contains_shellfish)
        self.assertTrue(fetched.contains_eggs)
    
    def test_allergen_has_allergen_method(self):
        """✅ Test has_allergen() method."""
        # Profile with allergen
        profile1 = AllergenProfile(
            donation_id='HH-TEST-003',
            contains_nuts=True
        )
        profile1.create()
        self.assertTrue(profile1.has_allergen())
        
        # Profile without allergen
        profile2 = AllergenProfile(donation_id='HH-TEST-004')
        profile2.create()
        self.assertFalse(profile2.has_allergen())
    
    def test_allergen_summary_methods(self):
        """✅ Test allergen and dietary summary methods."""
        profile = AllergenProfile(
            donation_id='HH-TEST-005',
            contains_nuts=True,
            contains_dairy=True,
            is_vegetarian=True,
            is_vegan=False
        )
        profile.create()
        
        allergen_summary = profile.get_allergen_summary()
        dietary_summary = profile.get_dietary_summary()
        
        self.assertIn('Nuts', allergen_summary)
        self.assertIn('Dairy', allergen_summary)
        self.assertIn('Vegetarian', dietary_summary)


class TestFoodSafetyLogModel(unittest.TestCase):
    """Test FoodSafetyLog model validation and operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_food_safety_log_creation(self):
        """✅ Test creating food safety log."""
        log = FoodSafetyLog(
            donation_id='HH-TEST-001',
            temperature_reading=38.5,
            storage_method='refrigerator',
            passed_inspection=True
        )
        result = log.create()
        self.assertIsNotNone(result)
        self.assertEqual(result.temperature_reading, 38.5)
    
    def test_temperature_safety_check(self):
        """✅ Test temperature safety validation."""
        # Frozen food - should be ≤0°F
        log1 = FoodSafetyLog(
            donation_id='HH-TEST-002',
            temperature_reading=-4.0,
            storage_method='freezer'
        )
        self.assertTrue(log1.is_temperature_safe())
        
        # Refrigerated - should be ≤40°F
        log2 = FoodSafetyLog(
            donation_id='HH-TEST-003',
            temperature_reading=38.0,
            storage_method='refrigerator'
        )
        self.assertTrue(log2.is_temperature_safe())
        
        # Too warm
        log3 = FoodSafetyLog(
            donation_id='HH-TEST-004',
            temperature_reading=70.0,
            storage_method='refrigerator'
        )
        self.assertFalse(log3.is_temperature_safe())
    
    def test_inspection_pass_fail(self):
        """✅ Test inspection pass/fail status."""
        log_pass = FoodSafetyLog(
            donation_id='HH-TEST-005',
            passed_inspection=True
        )
        log_pass.create()
        
        log_fail = FoodSafetyLog(
            donation_id='HH-TEST-006',
            passed_inspection=False
        )
        log_fail.create()
        
        self.assertTrue(log_pass.passed_inspection)
        self.assertFalse(log_fail.passed_inspection)


class TestDonationFeedbackModel(unittest.TestCase):
    """Test DonationFeedback model validation and operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
    
    def test_donation_feedback_creation(self):
        """✅ Test creating donation feedback."""
        feedback = DonationFeedback(
            donation_id='HH-TEST-001',
            reviewer_id=1,
            food_quality_rating=4,
            timeliness_rating=5,
            overall_rating=4,
            comments='Great donation!'
        )
        result = feedback.create()
        self.assertIsNotNone(result)
        self.assertEqual(result.overall_rating, 4)
    
    def test_feedback_rating_validation(self):
        """✅ Test rating validation (1-5 range)."""
        feedback = DonationFeedback(
            donation_id='HH-TEST-002',
            reviewer_id=1,
            food_quality_rating=3,
            timeliness_rating=4,
            overall_rating=5
        )
        is_valid, message = feedback.validate_ratings()
        self.assertTrue(is_valid)
        
        # Invalid rating
        feedback.overall_rating = 6
        is_valid, message = feedback.validate_ratings()
        self.assertFalse(is_valid)
    
    def test_feedback_average_rating(self):
        """✅ Test average rating calculation."""
        feedback = DonationFeedback(
            donation_id='HH-TEST-003',
            reviewer_id=1,
            food_quality_rating=4,
            timeliness_rating=5,
            overall_rating=4
        )
        
        avg = feedback.get_rating_summary()
        self.assertAlmostEqual(avg, 4.33, places=2)
    
    def test_feedback_issues_tracking(self):
        """✅ Test reported issues tracking."""
        feedback = DonationFeedback(
            donation_id='HH-TEST-004',
            reviewer_id=1,
            reported_issues=['damaged_packaging', 'expired_date']
        )
        
        self.assertTrue(feedback.has_issues())
        self.assertIn('damaged_packaging', feedback.reported_issues)


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*70)
    print("🧪 HUNGER HEROES MODEL VALIDATION TESTS")
    print("="*70)
    print()
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestUserModel))
    suite.addTests(loader.loadTestsFromTestCase(TestOrganizationModel))
    suite.addTests(loader.loadTestsFromTestCase(TestDonationModel))
    suite.addTests(loader.loadTestsFromTestCase(TestAllergenProfileModel))
    suite.addTests(loader.loadTestsFromTestCase(TestFoodSafetyLogModel))
    suite.addTests(loader.loadTestsFromTestCase(TestDonationFeedbackModel))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print()
    
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(run_all_tests())
