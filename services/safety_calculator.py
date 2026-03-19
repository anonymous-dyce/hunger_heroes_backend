# safety_calculator.py
"""
SafetyScoreCalculator - Computes food safety scores based on multiple factors.

Score Calculation Logic:
- Base score: 100 points
- Temperature compliance: ±0.5 pts per degree deviation from safe range
- Storage method compliance: 0-20 point deduction based on method
- Time since preparation: Progressive deduction based on hours elapsed
- Food type: Risk multiplier for food types
- Allergen warnings: Minor deduction if allergens present

Safe temperature ranges per food type:
- Cooked: 140-165°F (60-74°C)
- Raw vegetables: 50-60°F (10-15°C)
- Dairy: 32-40°F (0-4°C)
- Meat: 32-40°F (0-4°C) before cooking, 165°F+ (74°C+) after cooking
"""

from datetime import datetime, timedelta
from __init__ import app, db


class SafetyScoreCalculator:
    """
    Calculates a 0-100 safety score for food donations based on multiple factors.
    """

    # Safe temperature ranges in Celsius (can accept Fahrenheit and convert)
    TEMP_RANGES = {
        'cooked': (15, 74),  # Room temp to 74°C (165°F)
        'raw': (5, 15),      # 5-15°C (40-60°F)
        'dairy': (0, 4),     # Refrigerated
        'meat-protein': (0, 4),  # Refrigerated before cooking
        'frozen': (-25, -18), # Freezer temp
        'packaged': (5, 25), # Shelf stable to room temp
        'perishable': (0, 15),   # Refrigerated
        'non-perishable': (10, 25),  # Room temperature
        'baked': (15, 25),   # Room temperature
        'frozen-prepared': (-25, -18),  # Freezer temp
        'canned-goods': (10, 25),  # Room temperature
        'beverage': (0, 10), # Refrigerated or room temp
        'other': (5, 20),    # Conservative range
    }

    # Storage method safety ratings
    STORAGE_METHOD_POINTS = {
        'cooler-with-ice': 0,      # Best - no deduction
        'insulated-bag': 0,         # Good - no deduction
        'refrigerator': 0,          # Excellent - no deduction
        'freezer': 0,               # Excellent - no deduction
        'room-temperature-shelf': 10,  # Risky for perishables - 10 pt deduction
        'heated-container': 5,      # Acceptable for hot foods - 5 pt deduction
        'other': 15,                # Unknown - 15 pt deduction
    }

    # Storage type safety ratings (from donation.storage field)
    STORAGE_TYPE_POINTS = {
        'room-temp': 15,        # Risky - 15 pt deduction
        'refrigerated': 0,      # Safe - no deduction
        'frozen': 0,            # Safe - no deduction
        'cool-dry': 5,          # Good - 5 pt deduction
    }

    # Time-based safety deductions (hours since preparation)
    TIME_DEDUCTION_SCHEDULES = {
        'cooked': [           # Hot/cooked foods spoil faster
            (2, 0),           # 0-2 hours: 0 deduction
            (4, 5),           # 2-4 hours: 5 points
            (8, 15),          # 4-8 hours: 15 points
            (24, 30),         # 8-24 hours: 30 points
            (float('inf'), 50),  # 24+ hours: 50 points (near failure)
        ],
        'raw': [              # Raw vegetables last longer
            (6, 0),           # 0-6 hours: 0 deduction
            (12, 5),          # 6-12 hours: 5 points
            (24, 10),         # 12-24 hours: 10 points
            (72, 20),         # 24-72 hours: 20 points
            (float('inf'), 40),  # 72+ hours: 40 points
        ],
        'frozen-prepared': [  # Frozen items last much longer
            (24, 0),          # 0-24 hours: 0 deduction
            (72, 0),          # 24-72 hours: 0 deduction
            (168, 5),         # 3-7 days: 5 points
            (float('inf'), 15),  # 7+ days: 15 points
        ],
        'canned-goods': [     # Canned goods very stable
            (365, 0),         # 0-1 year: 0 deduction
            (730, 10),        # 1-2 years: 10 points
            (float('inf'), 30),  # 2+ years: 30 points
        ],
        'packaged': [         # Packaged goods moderately stable
            (30, 0),          # 0-30 days: 0 deduction
            (90, 5),          # 30-90 days: 5 points
            (180, 15),        # 90-180 days: 15 points
            (float('inf'), 30),  # 180+ days: 30 points
        ],
    }

    @classmethod
    def calculate_safety_score(cls, donation, safety_logs=None):
        """
        Calculate a 0-100 safety score for a donation.

        Args:
            donation: Donation model instance
            safety_logs: List of FoodSafetyLog instances (optional, will query if not provided)

        Returns:
            dict: {
                'score': int (0-100),
                'factors': {
                    'temperature': float,
                    'storage': float,
                    'time': float,
                    'allergens': float,
                },
                'warnings': [str],
                'requires_review': bool,
            }
        """
        score = 100.0
        factors = {
            'temperature': 0,
            'storage': 0,
            'time': 0,
            'allergens': 0,
        }
        warnings = []

        # ─────────────────────────────────────────────────────────────
        # 1. Temperature Compliance (if temperature_at_pickup exists)
        # ─────────────────────────────────────────────────────────────
        if donation.temperature_at_pickup is not None:
            temp_deduction = cls._calculate_temperature_deduction(
                donation.temperature_at_pickup,
                donation.food_type or 'other'
            )
            factors['temperature'] = temp_deduction
            score -= temp_deduction

            if temp_deduction > 15:
                warnings.append(f'Temperature reading ({donation.temperature_at_pickup}°) deviates significantly from safe range')
            if temp_deduction > 0:
                warnings.append(f'Temperature is {temp_deduction:.1f} points below safe')

        # ─────────────────────────────────────────────────────────────
        # 2. Storage Method Compliance
        # ─────────────────────────────────────────────────────────────
        storage_deduction = 0
        if donation.storage_method:
            storage_deduction += cls.STORAGE_METHOD_POINTS.get(donation.storage_method, 15)
        if donation.storage:
            storage_deduction += cls.STORAGE_TYPE_POINTS.get(donation.storage, 10)

        factors['storage'] = storage_deduction
        score -= storage_deduction

        if storage_deduction > 15:
            warnings.append('Storage method or type not optimal for food safety')

        # ─────────────────────────────────────────────────────────────
        # 3. Time Since Preparation
        # ─────────────────────────────────────────────────────────────
        if donation.prepared_at:
            time_deduction = cls._calculate_time_deduction(
                donation.prepared_at,
                donation.food_type or 'packaged',
                donation.expiry_date
            )
            factors['time'] = time_deduction
            score -= time_deduction

            hours_elapsed = (datetime.utcnow() - donation.prepared_at.replace(tzinfo=None)).total_seconds() / 3600
            if time_deduction > 10:
                warnings.append(f'Food prepared {hours_elapsed:.1f} hours ago - freshness declining')

        # ─────────────────────────────────────────────────────────────
        # 4. Allergen Warnings (minor deduction)
        # ─────────────────────────────────────────────────────────────
        allergen_deduction = 0
        if donation.allergens and len(donation.allergens) > 0:
            allergen_deduction = min(5, len(donation.allergens) * 1)  # Max 5 pts
            warnings.append(f'Allergens present: {", ".join(donation.allergens)}')

        factors['allergens'] = allergen_deduction
        score -= allergen_deduction

        # ─────────────────────────────────────────────────────────────
        # 5. Additional Safety Logs Review
        # ─────────────────────────────────────────────────────────────
        if safety_logs is None and hasattr(donation, 'safety_logs'):
            safety_logs = donation.safety_logs

        if safety_logs:
            failed_logs = [log for log in safety_logs if not log.passed_inspection]
            if failed_logs:
                score -= 20  # Significant deduction for failed inspections
                warnings.append(f'{len(failed_logs)} safety inspection(s) failed')

        # ─────────────────────────────────────────────────────────────
        # 6. Normalize score to 0-100 range
        # ─────────────────────────────────────────────────────────────
        score = max(0, min(100, score))  # Clamp to 0-100

        # ─────────────────────────────────────────────────────────────
        # 7. Determine if requires_review
        # ─────────────────────────────────────────────────────────────
        requires_review = score < 50

        return {
            'score': int(score),
            'factors': factors,
            'warnings': warnings,
            'requires_review': requires_review,
        }

    @classmethod
    def _calculate_temperature_deduction(cls, temp_reading, food_type):
        """
        Calculate deduction points based on temperature deviation from safe range.

        Args:
            temp_reading (float): Temperature reading (assuming Celsius)
            food_type (str): Type of food

        Returns:
            float: Deduction points (0-25)
        """
        min_temp, max_temp = cls.TEMP_RANGES.get(food_type, (5, 20))

        if temp_reading < min_temp:
            # Too cold - deduct 0.5 pts per degree below minimum
            deviation = min_temp - temp_reading
        elif temp_reading > max_temp:
            # Too hot (or too cold if max is higher) - deduct 0.5 pts per degree above maximum
            deviation = temp_reading - max_temp
        else:
            # Within safe range
            return 0

        deduction = min(25, deviation * 0.5)  # Cap at 25 points
        return deduction

    @classmethod
    def _calculate_time_deduction(cls, prepared_at, food_type, expiry_date=None):
        """
        Calculate deduction points based on time since preparation.

        Args:
            prepared_at (datetime): When food was prepared
            food_type (str): Type of food
            expiry_date (date): Expiration date (optional)

        Returns:
            float: Deduction points (0-50)
        """
        now = datetime.utcnow()
        prepared_dt = prepared_at.replace(tzinfo=None) if prepared_at else now

        hours_elapsed = (now - prepared_dt).total_seconds() / 3600

        # Check if past expiry
        if expiry_date and datetime.utcnow().date() > expiry_date:
            return 50  # Maximum deduction for expired food

        # Get schedule for food type
        schedule = cls.TIME_DEDUCTION_SCHEDULES.get(
            food_type,
            cls.TIME_DEDUCTION_SCHEDULES['packaged']  # Default to packaged
        )

        # Find appropriate deduction
        for hours_threshold, deduction in schedule:
            if hours_elapsed <= hours_threshold:
                return deduction

        return 50  # Maximum deduction if past all thresholds

    @classmethod
    def update_donation_safety_score(cls, donation, safety_logs=None):
        """
        Calculate safety score and update donation record.

        Args:
            donation: Donation model instance
            safety_logs: List of FoodSafetyLog instances (optional)

        Returns:
            dict: Result with updated score and flags
        """
        result = cls.calculate_safety_score(donation, safety_logs)

        # Update donation fields
        donation.safety_score = result['score']
        donation.requires_review = result['requires_review']

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {
                'error': str(e),
                'score': result['score'],
                'requires_review': result['requires_review'],
            }

        return {
            'donation_id': donation.id,
            'score': result['score'],
            'requires_review': result['requires_review'],
            'factors': result['factors'],
            'warnings': result['warnings'],
        }
