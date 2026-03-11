# api/donation.py — Week 2: Full lifecycle, volunteer assignment, QR/barcode labels, scan
import jwt
from flask import Blueprint, request, jsonify, current_app, g, send_file
from flask_restful import Api, Resource
from datetime import datetime, date, timedelta
from io import BytesIO
import base64

from __init__ import app, db
from api.jwt_authorize import token_required
from model.donation import (
    Donation, DonationStatusLog, VolunteerAssignment,
    generate_donation_id, log_status_change,
    ALLOWED_CATEGORIES, ALLOWED_UNITS, ALLOWED_STORAGE,
    ALLOWED_ALLERGENS, ALLOWED_DIETARY, ALLOWED_STATUSES,
    ALLOWED_FOOD_TYPES, ALLOWED_STORAGE_METHODS,
    VALID_TRANSITIONS,
)
from model.user import User

# Blueprint setup
donation_api = Blueprint('donation_api', __name__, url_prefix='/api')
api = Api(donation_api, errors={})


# Helpers

def _try_get_current_user():
    """Attempt to authenticate the user from the JWT cookie without requiring it."""
    token = request.cookies.get(current_app.config.get("JWT_TOKEN_NAME", "jwt_python_flask"))
    if not token:
        return None
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user = User.query.filter_by(_uid=data["_uid"]).first()
        return user
    except Exception:
        return None


def _get_user_name(user=None):
    """Get display name from a User object."""
    if user:
        return getattr(user, '_name', None) or getattr(user, 'name', None) or str(user.id)
    return None


def _validate_transition(current_status, new_status):
    """Validate a status transition. Returns (ok, error_message)."""
    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        return False, f"Cannot transition from '{current_status}' to '{new_status}'. Allowed: {allowed}"
    return True, None


# 1. POST /api/donations  -- Create Donation
#    GET  /api/donations  -- List Donations (with filters)

class DonationListAPI(Resource):

    def post(self):
        """Create a new donation (status = 'posted')."""
        data = request.get_json()
        if not data:
            return {'message': 'Request body is required'}, 400

        required = [
            'food_name', 'category', 'quantity', 'unit',
            'expiry_date', 'storage', 'donor_name', 'donor_email', 'donor_zip'
        ]
        for field in required:
            if not data.get(field):
                return {'message': f'Missing required field: {field}'}, 400

        if data['category'] not in ALLOWED_CATEGORIES:
            return {'message': f'Invalid category: {data["category"]}. Allowed: {ALLOWED_CATEGORIES}'}, 400
        if data['unit'] not in ALLOWED_UNITS:
            return {'message': f'Invalid unit: {data["unit"]}. Allowed: {ALLOWED_UNITS}'}, 400
        if data['storage'] not in ALLOWED_STORAGE:
            return {'message': f'Invalid storage type: {data["storage"]}. Allowed: {ALLOWED_STORAGE}'}, 400

        food_type = data.get('food_type')
        if food_type and food_type not in ALLOWED_FOOD_TYPES:
            return {'message': f'Invalid food_type: {food_type}. Allowed: {ALLOWED_FOOD_TYPES}'}, 400
        storage_method = data.get('storage_method')
        if storage_method and storage_method not in ALLOWED_STORAGE_METHODS:
            return {'message': f'Invalid storage_method: {storage_method}. Allowed: {ALLOWED_STORAGE_METHODS}'}, 400

        allergens = data.get('allergens', [])
        for a in allergens:
            if a not in ALLOWED_ALLERGENS:
                return {'message': f'Invalid allergen: {a}. Allowed: {ALLOWED_ALLERGENS}'}, 400
        dietary_tags = data.get('dietary_tags', [])
        for t in dietary_tags:
            if t not in ALLOWED_DIETARY:
                return {'message': f'Invalid dietary tag: {t}. Allowed: {ALLOWED_DIETARY}'}, 400

        try:
            expiry = datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
            if expiry < date.today():
                return {'message': 'Expiry date cannot be in the past'}, 400
        except ValueError:
            return {'message': 'Invalid date format. Use YYYY-MM-DD'}, 400

        try:
            quantity = int(data['quantity'])
            if quantity < 1:
                return {'message': 'Quantity must be at least 1'}, 400
        except (ValueError, TypeError):
            return {'message': 'Quantity must be a positive integer'}, 400

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
                return {'message': 'temperature_at_pickup must be a number'}, 400

        pickup_window_start = None
        pickup_window_end = None
        if data.get('pickup_window_start'):
            try:
                pickup_window_start = datetime.fromisoformat(data['pickup_window_start'])
            except ValueError:
                return {'message': 'Invalid pickup_window_start format. Use ISO 8601'}, 400
        if data.get('pickup_window_end'):
            try:
                pickup_window_end = datetime.fromisoformat(data['pickup_window_end'])
            except ValueError:
                return {'message': 'Invalid pickup_window_end format. Use ISO 8601'}, 400
        if pickup_window_start and pickup_window_end and pickup_window_end <= pickup_window_start:
            return {'message': 'pickup_window_end must be after pickup_window_start'}, 400

        donor_id = data.get('donor_id')
        receiver_id = data.get('receiver_id')
        for fk_name, fk_val in [('donor_id', donor_id), ('receiver_id', receiver_id)]:
            if fk_val is not None:
                if not User.query.get(int(fk_val)):
                    return {'message': f'{fk_name} refers to a non-existent user'}, 400

        current_user = _try_get_current_user()
        user_name = _get_user_name(current_user)

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
            status='posted',
        )

        try:
            db.session.add(donation)
            log_status_change(donation_id, 'none', 'posted',
                              user_name or data['donor_name'], 'Donation created')
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'message': f'Failed to create donation: {str(e)}'}, 500

        return {
            'id': donation_id,
            'message': 'Donation created successfully',
            'status': 'posted',
            'donation': donation.to_dict()
        }, 201

    def get(self):
        """List donations with optional filters. Auth required for mine=true."""
        status_filter = request.args.get('status', 'all')
        zip_code = request.args.get('zip_code')
        food_type = request.args.get('food_type')
        dietary = request.args.get('dietary_tags')
        mine_only = request.args.get('mine', 'false').lower() == 'true'
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        current_user = _try_get_current_user()

        query = Donation.query.filter_by(is_archived=False)

        if mine_only:
            if not current_user:
                return {'message': 'Authentication required for mine=true'}, 401
            query = query.filter_by(user_id=current_user.id)

        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        if zip_code:
            query = query.filter_by(donor_zip=zip_code)
        if food_type:
            query = query.filter_by(category=food_type)
        if dietary:
            tags = [t.strip() for t in dietary.split(',')]
            for tag in tags:
                query = query.filter(Donation.dietary_tags.contains([tag]))

        today = date.today()
        expired_q = Donation.query.filter(
            Donation.expiry_date < today,
            Donation.status == 'posted',
            Donation.is_archived == False
        ).all()
        for d in expired_q:
            log_status_change(d.id, d.status, 'expired', 'system',
                              'Auto-expired past expiry date')
            d.status = 'expired'
        if expired_q:
            db.session.commit()

        total = query.count()
        donations = query.order_by(Donation.created_at.desc()) \
                         .offset((page - 1) * per_page) \
                         .limit(per_page).all()

        return {
            'donations': [d.to_dict() for d in donations],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }, 200


# 2. GET /api/donations/{id}  -- Get Donation Detail

class DonationDetailAPI(Resource):

    def get(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation or donation.is_archived:
            return {'message': 'Donation not found'}, 404

        donation.scan_count = (donation.scan_count or 0) + 1
        db.session.commit()

        result = donation.to_dict()
        result['status_history'] = [
            log.to_dict() for log in
            DonationStatusLog.query.filter_by(donation_id=donation_id)
                .order_by(DonationStatusLog.changed_at.desc())
                .limit(10).all()
        ]
        if donation.volunteer_assignment:
            result['volunteer'] = donation.volunteer_assignment.to_dict()
        else:
            result['volunteer'] = None

        return result, 200

    def delete(self, donation_id):
        """Soft-delete (archive) a donation."""
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        if donation.status in ('in_transit', 'delivered'):
            return {'message': 'Cannot archive a donation that is in transit or delivered'}, 400

        current_user = _try_get_current_user()
        user_name = _get_user_name(current_user) or 'anonymous'

        donation.is_archived = True
        log_status_change(donation_id, donation.status, donation.status,
                          user_name, 'Archived by donor')
        db.session.commit()

        return {'message': 'Donation archived', 'donation_id': donation_id}, 200


# 3. PATCH /api/donations/{id}/status  -- Transition Status

class DonationStatusAPI(Resource):

    def patch(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation or donation.is_archived:
            return {'message': 'Donation not found'}, 404

        data = request.get_json(silent=True) or {}
        new_status = data.get('new_status')
        if not new_status:
            return {'message': 'Missing required field: new_status'}, 400

        valid, error = _validate_transition(donation.status, new_status)
        if not valid:
            return {'message': error}, 409

        current_user = _try_get_current_user()
        user_name = _get_user_name(current_user) or data.get('actor', 'anonymous')
        old_status = donation.status
        now = datetime.utcnow()

        if new_status == 'claimed':
            donation.claimed_by = user_name
            donation.claimed_at = now
        elif new_status == 'in_transit':
            if not donation.volunteer_assignment:
                return {'message': 'Cannot move to in_transit without a volunteer assignment'}, 400
            donation.in_transit_at = now
            donation.volunteer_assignment.picked_up_at = now
        elif new_status == 'delivered':
            donation.delivered_by = user_name
            donation.delivered_at = now
            if donation.volunteer_assignment:
                donation.volunteer_assignment.delivered_at = now
        elif new_status == 'confirmed':
            donation.confirmed_by = user_name
            donation.confirmed_at = now

        donation.status = new_status
        log_status_change(donation_id, old_status, new_status, user_name, data.get('notes'))
        db.session.commit()

        return {
            'message': f'Status updated from {old_status} to {new_status}',
            'donation_id': donation_id,
            'old_status': old_status,
            'new_status': new_status,
            'updated_at': now.isoformat()
        }, 200


# 5. POST /api/donations/{id}/assign-volunteer

class VolunteerAssignAPI(Resource):

    def post(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation or donation.is_archived:
            return {'message': 'Donation not found'}, 404

        if donation.status not in ('posted', 'claimed'):
            return {'message': f'Cannot assign volunteer when status is "{donation.status}"'}, 400

        if donation.volunteer_assignment:
            return {'message': 'A volunteer is already assigned to this donation'}, 409

        data = request.get_json(silent=True) or {}
        volunteer_name = data.get('volunteer_name', '')

        current_user = _try_get_current_user()
        if current_user:
            volunteer_id = current_user.id
            volunteer_name = volunteer_name or _get_user_name(current_user) or ''
        else:
            return {'message': 'Authentication required to volunteer'}, 401

        assignment = VolunteerAssignment(
            donation_id=donation_id,
            volunteer_id=volunteer_id,
            volunteer_name=volunteer_name,
        )
        db.session.add(assignment)

        if donation.status == 'posted':
            old = donation.status
            donation.status = 'claimed'
            donation.claimed_by = volunteer_name
            donation.claimed_at = datetime.utcnow()
            log_status_change(donation_id, old, 'claimed', volunteer_name,
                              'Auto-claimed on volunteer assignment')

        db.session.commit()

        return {
            'message': 'Volunteer assigned successfully',
            'assignment': assignment.to_dict()
        }, 201


# 6. GET /api/volunteers/{id}/assignments

class VolunteerAssignmentsAPI(Resource):

    def get(self, volunteer_id):
        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        query = VolunteerAssignment.query.filter_by(volunteer_id=volunteer_id)
        assignments = query.order_by(VolunteerAssignment.assigned_at.desc()).all()

        results = []
        for a in assignments:
            d = Donation.query.get(a.donation_id)
            if d and (status_filter == 'all' or d.status == status_filter):
                results.append({
                    **a.to_dict(),
                    'food_name': d.food_name,
                    'category': d.category,
                    'status': d.status,
                    'donor_zip': d.donor_zip,
                    'expiry_date': d.expiry_date.isoformat() if d.expiry_date else None,
                })

        start = (page - 1) * per_page
        end = start + per_page
        return {
            'assignments': results[start:end],
            'total': len(results),
            'page': page,
            'per_page': per_page,
        }, 200


# 7. POST /api/donations/scan  -- Scan QR/Barcode

class DonationScanAPI(Resource):

    def post(self):
        data = request.get_json(silent=True) or {}
        scan_data = data.get('scan_data', '').strip()
        if not scan_data:
            return {'message': 'Missing scan_data'}, 400

        donation = Donation.query.get(scan_data)
        if not donation:
            return {'message': 'Donation not found'}, 404

        donation.scan_count = (donation.scan_count or 0) + 1

        warnings = []
        today = date.today()

        if donation.expiry_date and donation.expiry_date < today:
            warnings.append({
                'type': 'expired',
                'message': f'This donation expired on {donation.expiry_date.isoformat()}'
            })
            if donation.status == 'posted':
                log_status_change(donation.id, 'posted', 'expired', 'system',
                                  'Expired on scan')
                donation.status = 'expired'
        elif donation.expiry_date and (donation.expiry_date - today).days <= 3:
            days = (donation.expiry_date - today).days
            warnings.append({
                'type': 'expiring_soon',
                'message': f'Expires in {days} day(s)'
            })

        if donation.is_archived:
            warnings.append({
                'type': 'archived',
                'message': 'This donation has been archived'
            })

        db.session.commit()

        result = donation.to_dict()
        result['warnings'] = warnings
        result['scan_count'] = donation.scan_count
        if donation.volunteer_assignment:
            result['volunteer'] = donation.volunteer_assignment.to_dict()
        else:
            result['volunteer'] = None

        return result, 200


# 8. GET /api/donations/{id}/label  -- QR + Barcode Label

class DonationLabelAPI(Resource):

    def get(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        fmt = request.args.get('format', 'json')

        if fmt == 'json':
            try:
                import qrcode as qr_lib
                import barcode as barcode_lib
                from barcode.writer import ImageWriter

                qr = qr_lib.QRCode(version=1, box_size=10, border=4)
                qr.add_data(donation_id)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                qr_buf = BytesIO()
                qr_img.save(qr_buf, format='PNG')
                qr_b64 = base64.b64encode(qr_buf.getvalue()).decode('utf-8')

                code128 = barcode_lib.get('code128', donation_id, writer=ImageWriter())
                bc_buf = BytesIO()
                code128.write(bc_buf)
                bc_b64 = base64.b64encode(bc_buf.getvalue()).decode('utf-8')

                return {
                    'donation': donation.to_dict(),
                    'qr_code_base64': f'data:image/png;base64,{qr_b64}',
                    'barcode_base64': f'data:image/png;base64,{bc_b64}',
                }, 200

            except ImportError as e:
                return {
                    'message': f'Label generation dependency missing: {str(e)}. Install with: pip install "qrcode[pil]" python-barcode Pillow',
                    'donation': donation.to_dict(),
                }, 501

        elif fmt in ('png', 'pdf'):
            return {'message': f'{fmt} format not yet implemented'}, 501

        return {'message': 'Invalid format. Use json, png, or pdf'}, 400


# 9. GET /api/donations/stats  -- Aggregate Stats

class DonationStatsAPI(Resource):

    def get(self):
        current_user = _try_get_current_user()

        if current_user:
            base = Donation.query.filter_by(user_id=current_user.id, is_archived=False)
        else:
            base = Donation.query.filter_by(is_archived=False)

        return {
            'total': base.count(),
            'posted': base.filter_by(status='posted').count(),
            'claimed': base.filter_by(status='claimed').count(),
            'in_transit': base.filter_by(status='in_transit').count(),
            'delivered': base.filter_by(status='delivered').count(),
            'confirmed': base.filter_by(status='confirmed').count(),
            'expired': base.filter_by(status='expired').count(),
            'cancelled': base.filter_by(status='cancelled').count(),
            'scanned': int(db.session.query(
                db.func.sum(Donation.scan_count)).scalar() or 0),
            'volunteers_active': VolunteerAssignment.query.count(),
        }, 200


# 10. POST /api/donations/cleanup  -- Admin manual cleanup

class DonationCleanupAPI(Resource):

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
            Donation.status.in_(['posted', 'expired', 'cancelled'])
        ).all()

        count = len(stale)
        for d in stale:
            d.is_archived = True
        if count:
            db.session.commit()

        return {
            'message': f'Archived {count} donation(s) older than {days} day(s)',
            'archived_count': count,
            'cutoff': cutoff.isoformat(),
        }, 200


# Legacy Week 1 compat endpoints (singular /donation)

class DonationAcceptAPI(Resource):
    """POST /api/donation/<id>/accept -- Legacy Week 1 accept (maps to claimed)."""

    def post(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        if donation.is_archived:
            return {'message': 'Donation has been archived'}, 404

        if donation.status == 'posted' and donation.expiry_date < date.today():
            donation.status = 'expired'
            log_status_change(donation_id, 'posted', 'expired', 'system', 'Auto-expired')
            db.session.commit()

        if donation.status in ('claimed', 'in_transit', 'delivered', 'confirmed'):
            return {'message': f'Donation already {donation.status}'}, 409
        if donation.status == 'expired':
            return {'message': 'Cannot accept an expired donation'}, 400
        if donation.status == 'cancelled':
            return {'message': 'Cannot accept a cancelled donation'}, 400

        data = request.get_json(silent=True) or {}
        accepted_by = data.get('accepted_by', '')

        current_user = _try_get_current_user()
        if current_user and not accepted_by:
            accepted_by = _get_user_name(current_user) or ''

        old_status = donation.status
        donation.status = 'claimed'
        donation.claimed_by = accepted_by
        donation.claimed_at = datetime.utcnow()
        donation.accepted_by = accepted_by
        donation.accepted_at = donation.claimed_at

        log_status_change(donation_id, old_status, 'claimed', accepted_by,
                          'Accepted via legacy endpoint')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'message': f'Failed to accept donation: {str(e)}'}, 500

        return {
            'message': 'Donation accepted',
            'donation_id': donation_id,
            'status': 'claimed',
            'accepted_by': accepted_by,
        }, 200


class DonationDeliverAPI(Resource):
    """POST /api/donation/<id>/deliver -- Legacy Week 1 deliver."""

    def post(self, donation_id):
        donation = Donation.query.get(donation_id)
        if not donation:
            return {'message': 'Donation not found'}, 404

        if donation.is_archived:
            return {'message': 'Donation has been archived'}, 404

        if donation.status == 'posted' and donation.expiry_date < date.today():
            donation.status = 'expired'
            log_status_change(donation_id, 'posted', 'expired', 'system', 'Auto-expired')
            db.session.commit()

        if donation.status == 'delivered':
            return {'message': 'Donation already delivered'}, 409
        if donation.status in ('confirmed',):
            return {'message': 'Donation already confirmed'}, 409
        if donation.status == 'expired':
            return {'message': 'Cannot deliver an expired donation'}, 400
        if donation.status == 'cancelled':
            return {'message': 'Cannot deliver a cancelled donation'}, 400

        data = request.get_json(silent=True) or {}
        delivered_by = data.get('delivered_by', '')

        current_user = _try_get_current_user()
        if current_user and not delivered_by:
            delivered_by = _get_user_name(current_user) or ''

        old_status = donation.status
        donation.status = 'delivered'
        donation.delivered_by = delivered_by
        donation.delivered_at = datetime.utcnow()

        log_status_change(donation_id, old_status, 'delivered', delivered_by,
                          'Delivered via legacy endpoint')

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {'message': f'Failed to mark as delivered: {str(e)}'}, 500

        auto_remove_at = (donation.delivered_at + timedelta(hours=24)).isoformat() \
            if donation.delivered_at else None
        return {
            'message': 'Donation marked as delivered',
            'donation_id': donation_id,
            'status': 'delivered',
            'delivered_at': donation.delivered_at.isoformat() if donation.delivered_at else None,
            'auto_remove_at': auto_remove_at,
        }, 200


# Register routes
# IMPORTANT: static paths (stats, scan, cleanup) BEFORE parameterized routes

# Week 2 endpoints (plural /donations)
api.add_resource(DonationListAPI, '/donations')
api.add_resource(DonationStatsAPI, '/donations/stats')
api.add_resource(DonationScanAPI, '/donations/scan')
api.add_resource(DonationCleanupAPI, '/donations/cleanup')
api.add_resource(DonationDetailAPI, '/donations/<string:donation_id>')
api.add_resource(DonationStatusAPI, '/donations/<string:donation_id>/status')
api.add_resource(DonationLabelAPI, '/donations/<string:donation_id>/label')
api.add_resource(VolunteerAssignAPI, '/donations/<string:donation_id>/assign-volunteer')
api.add_resource(VolunteerAssignmentsAPI, '/volunteers/<int:volunteer_id>/assignments')

# Legacy Week 1 endpoints (singular /donation) -- backward compat
api.add_resource(DonationAcceptAPI, '/donation/<string:donation_id>/accept')
api.add_resource(DonationDeliverAPI, '/donation/<string:donation_id>/deliver')
