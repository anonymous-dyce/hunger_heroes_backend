import jwt
from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource
from datetime import datetime, date, timedelta

from __init__ import app, db
from api.jwt_authorize import token_required
from model.donation import (
    Donation, generate_donation_id,
    ALLOWED_CATEGORIES, ALLOWED_UNITS, ALLOWED_STORAGE,
    ALLOWED_ALLERGENS, ALLOWED_DIETARY, ALLOWED_STATUSES,
    ALLOWED_FOOD_TYPES, ALLOWED_STORAGE_METHODS
)
from model.user import User

# Blueprint setup
donation_api = Blueprint('donation_api', __name__, url_prefix='/api')
api = Api(donation_api, errors={})  # disable default Flask-RESTful error handling for clean JSON responses


def _try_get_current_user():
    """
    Attempt to authenticate the user from the JWT cookie without requiring it.
    Returns the User object if authenticated, or None otherwise.
    """
    token = request.cookies.get(current_app.config.get("JWT_TOKEN_NAME", "jwt_python_flask"))
    if not token:
        return None
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user = User.query.filter_by(_uid=data["_uid"]).first()
        return user
    except Exception:
        return None


class DonationListAPI(Resource):
    """
    POST /api/donation   → Create a new donation
    GET  /api/donation   → List current user's donations (auth required)
    """

    def post(self):
        """Create a new donation."""
        data = request.get_json()
        if not data:
            return {'message': 'Request body is required'}, 400

        # --- Validate required fields ---
        required = [
            'food_name', 'category', 'quantity', 'unit',
            'expiry_date', 'storage', 'donor_name', 'donor_email', 'donor_zip'
        ]
        for field in required:
            if not data.get(field):
                return {'message': f'Missing required field: {field}'}, 400

        # --- Validate enums ---
        if data['category'] not in ALLOWED_CATEGORIES:
            return {'message': f'Invalid category: {data["category"]}. Allowed: {ALLOWED_CATEGORIES}'}, 400
        if data['unit'] not in ALLOWED_UNITS:
            return {'message': f'Invalid unit: {data["unit"]}. Allowed: {ALLOWED_UNITS}'}, 400
        if data['storage'] not in ALLOWED_STORAGE:
            return {'message': f'Invalid storage type: {data["storage"]}. Allowed: {ALLOWED_STORAGE}'}, 400

        # Validate food_type if provided
        food_type = data.get('food_type')
        if food_type and food_type not in ALLOWED_FOOD_TYPES:
            return {'message': f'Invalid food_type: {food_type}. Allowed: {ALLOWED_FOOD_TYPES}'}, 400

        # Validate storage_method if provided
        storage_method = data.get('storage_method')
        if storage_method and storage_method not in ALLOWED_STORAGE_METHODS:
            return {'message': f'Invalid storage_method: {storage_method}. Allowed: {ALLOWED_STORAGE_METHODS}'}, 400

        # Validate allergens if provided
        allergens = data.get('allergens', [])
        if allergens:
            for a in allergens:
                if a not in ALLOWED_ALLERGENS:
                    return {'message': f'Invalid allergen: {a}. Allowed: {ALLOWED_ALLERGENS}'}, 400

        # Validate dietary tags if provided
        dietary_tags = data.get('dietary_tags', [])
        if dietary_tags:
            for t in dietary_tags:
                if t not in ALLOWED_DIETARY:
                    return {'message': f'Invalid dietary tag: {t}. Allowed: {ALLOWED_DIETARY}'}, 400

        # --- Validate expiry date ---
        try:
            expiry = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            if expiry < date.today():
                return {'message': 'Expiry date cannot be in the past'}, 400
        except ValueError:
            return {'message': 'Invalid date format. Use YYYY-MM-DD'}, 400

        # --- Validate quantity ---
        try:
            quantity = int(data['quantity'])
            if quantity < 1:
                return {'message': 'Quantity must be at least 1'}, 400
        except (ValueError, TypeError):
            return {'message': 'Quantity must be a positive integer'}, 400

        # --- Validate optional numeric fields ---
        serving_count = data.get('serving_count')
        if serving_count is not None:
            try:
                serving_count = int(serving_count)
                if serving_count < 1:
                    return {'message': 'serving_count must be at least 1'}, 400
            except (ValueError, TypeError):
                return {'message': 'serving_count must be a positive integer'}, 400

        weight_lbs = data.get('weight_lbs')
        if weight_lbs is not None:
            try:
                weight_lbs = float(weight_lbs)
                if weight_lbs <= 0:
                    return {'message': 'weight_lbs must be positive'}, 400
            except (ValueError, TypeError):
                return {'message': 'weight_lbs must be a positive number'}, 400

        temperature_at_pickup = data.get('temperature_at_pickup')
        if temperature_at_pickup is not None:
            try:
                temperature_at_pickup = float(temperature_at_pickup)
            except (ValueError, TypeError):
                return {'message': 'temperature_at_pickup must be a number (°F)'}, 400

        # --- Parse pickup window datetimes ---
        pickup_window_start = None
        pickup_window_end = None
        if data.get('pickup_window_start'):
            try:
                pickup_window_start = datetime.fromisoformat(data['pickup_window_start'])
            except ValueError:
                return {'message': 'Invalid pickup_window_start format. Use ISO 8601 (e.g. 2025-06-01T09:00:00)'}, 400
        if data.get('pickup_window_end'):
            try:
                pickup_window_end = datetime.fromisoformat(data['pickup_window_end'])
            except ValueError:
                return {'message': 'Invalid pickup_window_end format. Use ISO 8601 (e.g. 2025-06-01T17:00:00)'}, 400
        if pickup_window_start and pickup_window_end and pickup_window_end <= pickup_window_start:
            return {'message': 'pickup_window_end must be after pickup_window_start'}, 400

        # --- Resolve optional foreign keys ---
        donor_id = data.get('donor_id')
        receiver_id = data.get('receiver_id')
        volunteer_id = data.get('volunteer_id')
        for fk_name, fk_val in [('donor_id', donor_id), ('receiver_id', receiver_id), ('volunteer_id', volunteer_id)]:
            if fk_val is not None:
                if not User.query.get(int(fk_val)):
                    return {'message': f'{fk_name} refers to a non-existent user'}, 400

        # --- Attempt optional auth ---
        current_user = _try_get_current_user()

        # --- Create donation ---
        donation_id = generate_donation_id()
        donation = Donation(
            id=donation_id,
            food_name=data['food_name'],
            category=data['category'],
            food_type=food_type,
            quantity=quantity,
            unit=data['unit'],
            serving_count=serving_count,
            weight_lbs=weight_lbs,
            description=data.get('description', ''),
            expiry_date=expiry,
            storage=data['storage'],
            allergens=allergens,
            allergen_info=data.get('allergen_info'),
            dietary_tags=dietary_tags,
            temperature_at_pickup=temperature_at_pickup,
            storage_method=storage_method,
            donor_name=data['donor_name'],
            donor_email=data['donor_email'],
            donor_phone=data.get('donor_phone', ''),
            donor_zip=data['donor_zip'],
            special_instructions=data.get('special_instructions', ''),
            pickup_location=data.get('pickup_location'),
            zip_code=data.get('zip_code'),
            pickup_window_start=pickup_window_start,
            pickup_window_end=pickup_window_end,
            user_id=current_user.id if current_user else None,
            donor_id=int(donor_id) if donor_id else None,
            receiver_id=int(receiver_id) if receiver_id else None,
            volunteer_id=int(volunteer_id) if volunteer_id else None,
            status='active'
        )

        try:
            db.session.add(donation)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'message': f'Failed to create donation: {str(e)}'}, 500

        return {
            'id': donation_id,
            'message': 'Donation created successfully',
            'donation': donation.to_dict()
        }, 201

    @token_required()
    def get(self):
        """List donations for the current authenticated user."""
        current_user = g.current_user

        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        # Validate status filter
        if status_filter != 'all' and status_filter not in ALLOWED_STATUSES:
            return {'message': f'Invalid status filter: {status_filter}'}, 400

        # Auto-expire old donations
        today = date.today()
        expired_donations = Donation.query.filter(
            Donation.user_id == current_user.id,
            Donation.expiry_date < today,
            Donation.status == 'active'
        ).all()
        for d in expired_donations:
            d.status = 'expired'
        if expired_donations:
            db.session.commit()

        # Build query
        query = Donation.query.filter_by(user_id=current_user.id)
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)

        # Paginate
        query = query.order_by(Donation.created_at.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)

        return {
            'donations': [d.to_dict_short() for d in paginated.items],
            'total': paginated.total,
            'page': paginated.page,
            'per_page': paginated.per_page,
            'pages': paginated.pages,
        }, 200


class DonationDetailAPI(Resource):
    """
    GET /api/donation/<id>   → Get a single donation by ID (public)
    """

    def get(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        # Auto-expire if past expiry date
        if donation.status == 'active' and donation.expiry_date < date.today():
            donation.status = 'expired'

        # Increment scan count
        donation.scan_count = (donation.scan_count or 0) + 1
        db.session.commit()

        return donation.to_dict(), 200


class DonationAcceptAPI(Resource):
    """
    POST /api/donation/<id>/accept   → Accept a donation
    """

    def post(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        # Auto-expire check
        if donation.status == 'active' and donation.expiry_date < date.today():
            donation.status = 'expired'
            db.session.commit()

        if donation.status == 'accepted':
            return {'message': 'Donation already accepted'}, 409
        if donation.status == 'delivered':
            return {'message': 'Donation already delivered'}, 409
        if donation.status == 'expired':
            return {'message': 'Cannot accept an expired donation'}, 400
        if donation.status == 'cancelled':
            return {'message': 'Cannot accept a cancelled donation'}, 400

        data = request.get_json(silent=True) or {}
        accepted_by = data.get('accepted_by', '')

        # Try to auto-fill from auth
        current_user = _try_get_current_user()
        if current_user and not accepted_by:
            accepted_by = current_user._name

        donation.status = 'accepted'
        donation.accepted_by = accepted_by
        donation.accepted_at = datetime.utcnow()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'message': f'Failed to accept donation: {str(e)}'}, 500

        return {
            'message': 'Donation accepted',
            'donation_id': donation_id,
            'status': 'accepted',
            'accepted_by': accepted_by,
        }, 200


class DonationDeliverAPI(Resource):
    """
    POST /api/donation/<id>/deliver   → Mark donation as delivered
    Once delivered, the background scheduler will auto-delete after 24 hours.
    """

    def post(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        # Auto-expire check
        if donation.status == 'active' and donation.expiry_date < date.today():
            donation.status = 'expired'
            db.session.commit()

        if donation.status == 'delivered':
            return {'message': 'Donation already delivered'}, 409
        if donation.status == 'expired':
            return {'message': 'Cannot deliver an expired donation'}, 400
        if donation.status == 'cancelled':
            return {'message': 'Cannot deliver a cancelled donation'}, 400

        data = request.get_json(silent=True) or {}
        delivered_by = data.get('delivered_by', '')

        # Try to auto-fill from auth
        current_user = _try_get_current_user()
        if current_user and not delivered_by:
            delivered_by = current_user._name

        donation.status = 'delivered'
        donation.delivered_by = delivered_by
        donation.delivered_at = datetime.utcnow()

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'message': f'Failed to mark as delivered: {str(e)}'}, 500

        auto_remove_at = (donation.delivered_at + timedelta(hours=24)).isoformat() if donation.delivered_at else None
        return {
            'message': 'Donation marked as delivered — will be auto-removed in 24 hours',
            'donation_id': donation_id,
            'status': 'delivered',
            'delivered_at': donation.delivered_at.isoformat() if donation.delivered_at else None,
            'auto_remove_at': auto_remove_at
        }, 200


class DonationStatsAPI(Resource):
    """
    GET /api/donation/stats   → Get aggregate donation stats
    """

    def get(self):
        current_user = _try_get_current_user()

        # If authenticated, return personal stats; otherwise global
        if current_user:
            base = Donation.query.filter_by(user_id=current_user.id)
        else:
            base = Donation.query

        # Exclude archived from stats by default
        base = base.filter(Donation.is_archived == False)

        total = base.count()
        active = base.filter_by(status='active').count()
        accepted = base.filter_by(status='accepted').count()
        delivered = base.filter_by(status='delivered').count()
        expired = base.filter_by(status='expired').count()
        cancelled = base.filter_by(status='cancelled').count()

        # Total scans (global regardless of user)
        scanned = db.session.query(db.func.sum(Donation.scan_count)).filter(
            Donation.is_archived == False
        ).scalar() or 0

        return {
            'total': total,
            'active': active,
            'accepted': accepted,
            'delivered': delivered,
            'expired': expired,
            'cancelled': cancelled,
            'scanned': int(scanned),
        }, 200


class DonationCleanupAPI(Resource):
    """
    POST /api/donations/cleanup   → Soft-delete (archive) donations older than 7 days.
    Optionally accepts { "days": N } to override the 7-day threshold.
    Requires admin auth.
    """

    @token_required()
    def post(self):
        current_user = g.current_user
        if current_user._role != 'Admin':
            return {'message': 'Admin access required'}, 403

        data = request.get_json(silent=True) or {}
        days = data.get('days', 7)
        try:
            days = int(days)
            if days < 1:
                return {'message': 'days must be at least 1'}, 400
        except (ValueError, TypeError):
            return {'message': 'days must be a positive integer'}, 400

        cutoff = datetime.utcnow() - timedelta(days=days)

        stale = Donation.query.filter(
            Donation.created_at <= cutoff,
            Donation.is_archived == False,
            Donation.status.in_(['active', 'expired', 'cancelled'])
        ).all()

        count = len(stale)
        for d in stale:
            d.is_archived = True
            d.status = 'archived'
        if count:
            db.session.commit()

        return {
            'message': f'Archived {count} donation(s) older than {days} day(s)',
            'archived_count': count,
            'cutoff': cutoff.isoformat(),
        }, 200


# --- Register routes ---
# IMPORTANT: stats must be registered BEFORE the <string:donation_id> route
# to avoid Flask treating "stats" as a donation_id
api.add_resource(DonationListAPI, '/donation')
api.add_resource(DonationStatsAPI, '/donation/stats')
api.add_resource(DonationCleanupAPI, '/donations/cleanup')
api.add_resource(DonationDetailAPI, '/donation/<string:donation_id>')
api.add_resource(DonationAcceptAPI, '/donation/<string:donation_id>/accept')
api.add_resource(DonationDeliverAPI, '/donation/<string:donation_id>/deliver')
