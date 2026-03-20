# api/analytics.py — Analytics & Impact Metrics Endpoints
"""
Analytics API - Platform-wide metrics and impact tracking

Endpoints:
- GET /api/analytics/overview — Platform overview statistics
- GET /api/analytics/weekly — Week-over-week trends
- GET /api/analytics/by-organization/<id> — Organization statistics
- GET /api/analytics/by-donor/<id> — Donor impact history
- GET /api/analytics/food-types — Food type breakdown
- GET /api/analytics/safety-compliance — Safety compliance metrics
- GET /api/analytics/export — CSV export of analytics
"""

from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource
from datetime import datetime
import csv
from io import StringIO, BytesIO

from __init__ import app, db
from api.jwt_authorize import token_required
from services.analytics_calculator import AnalyticsCalculator
from model.user import User
from model.donation import Donation
from model.organization import Organization


# Blueprint setup
analytics_api = Blueprint('analytics_api', __name__, url_prefix='/api')
api = Api(analytics_api, errors={})


def _try_get_current_user():
    """Attempt to authenticate user from JWT cookie without requiring it."""
    token = request.cookies.get(current_app.config.get("JWT_TOKEN_NAME", "jwt_python_flask"))
    if not token:
        return None
    try:
        import jwt
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        user = User.query.filter_by(_uid=data["_uid"]).first()
        return user
    except Exception:
        return None


class AnalyticsOverviewAPI(Resource):
    """GET /api/analytics/overview — Platform-wide overview statistics."""
    
    def get(self):
        """
        Retrieve platform overview with all key metrics.
        
        Returns:
            {
                'timestamp': ISO timestamp,
                'data': {
                    'total_donations': int,
                    'total_servings': int,
                    'total_pounds': float,
                    'active_donors': int,
                    'active_receivers': int,
                    'active_volunteers': int,
                    'avg_response_time_minutes': float,
                    'completion_rate': float,
                    'food_waste_diverted_lbs': float,
                    'co2_prevented_lbs': float,
                }
            }
        """
        try:
            stats = AnalyticsCalculator.get_overview_stats()
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'data': stats,
            }, 200
        except Exception as e:
            return {'error': f'Failed to retrieve overview: {str(e)}'}, 500


class AnalyticsWeeklyAPI(Resource):
    """GET /api/analytics/weekly — Week-over-week trend analysis."""
    
    def get(self):
        """
        Retrieve week-over-week trends.
        
        Query params:
            weeks (int, optional): Number of weeks to retrieve (default: 4, max: 52)
        
        Returns:
            {
                'timestamp': ISO timestamp,
                'trend': 'up'|'down'|'stable',
                'period_days': int,
                'weeks': [
                    {
                        'week_start': ISO datetime,
                        'week_end': ISO datetime,
                        'donations_posted': int,
                        'donations_completed': int,
                        'pounds_redistributed': float,
                        'servings_redistributed': int,
                        'new_donors': int,
                        'volunteers_active': int,
                    }
                ]
            }
        """
        try:
            weeks = request.args.get('weeks', 4, type=int)
            # Limit max weeks to prevent abuse
            weeks = min(weeks, 52)
            weeks = max(weeks, 1)
            
            result = AnalyticsCalculator.get_weekly_trends(weeks_back=weeks)
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'trend': result['trend'],
                'period_days': result['period_days'],
                'weeks': result['weeks'],
            }, 200
        except Exception as e:
            return {'error': f'Failed to retrieve weekly trends: {str(e)}'}, 500


class AnalyticsOrganizationAPI(Resource):
    """GET /api/analytics/by-organization/<id> — Organization-specific statistics."""
    
    def get(self, organization_id):
        """
        Retrieve impact metrics for a specific organization.
        
        Args:
            organization_id (int): Organization ID
        
        Returns:
            {
                'timestamp': ISO timestamp,
                'data': {
                    'organization_id': int,
                    'organization_name': str,
                    'organization_type': str,
                    'address': str,
                    'donations_received': int,
                    'servings_received': int,
                    'pounds_received': float,
                    'food_type_breakdown': {
                        'food_type': {'count': int, 'pounds': float}
                    },
                    'avg_safety_score': float,
                    'volunteers_helped': int,
                }
            }
        """
        try:
            result = AnalyticsCalculator.get_organization_stats(organization_id)
            if isinstance(result, tuple):
                return result
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'data': result,
            }, 200
        except Exception as e:
            return {'error': f'Failed to retrieve organization stats: {str(e)}'}, 500


class AnalyticsDonorAPI(Resource):
    """GET /api/analytics/by-donor/<id> — Donor impact history and statistics."""
    
    def get(self, donor_id):
        """
        Retrieve donor impact history and personal statistics.
        
        Args:
            donor_id (int): Donor (User) ID
        
        Returns:
            {
                'timestamp': ISO timestamp,
                'data': {
                    'donor_id': int,
                    'donor_name': str,
                    'donor_email': str,
                    'total_donations': int,
                    'total_servings': int,
                    'total_pounds': float,
                    'food_types_donated': {food_type: count},
                    'avg_response_time_minutes': float,
                    'completion_rate': float,
                    'impact_co2_prevented': float,
                    'recent_donations': [
                        {
                            'id': str,
                            'food_name': str,
                            'quantity': int,
                            'unit': str,
                            'status': str,
                            'created_at': ISO datetime,
                        }
                    ]
                }
            }
        """
        try:
            result = AnalyticsCalculator.get_donor_stats(donor_id)
            if isinstance(result, tuple):
                return result
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'data': result,
            }, 200
        except Exception as e:
            return {'error': f'Failed to retrieve donor stats: {str(e)}'}, 500


class AnalyticsFoodTypesAPI(Resource):
    """GET /api/analytics/food-types — Food type breakdown and metrics."""
    
    def get(self):
        """
        Retrieve donation statistics broken down by food type.
        
        Returns:
            {
                'timestamp': ISO timestamp,
                'food_types': {
                    'food_type': {
                        'count': int,
                        'pounds': float,
                        'servings': int,
                        'avg_response_time_minutes': float,
                        'completion_rate': float,
                    }
                }
            }
        """
        try:
            breakdown = AnalyticsCalculator.get_food_type_breakdown()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'food_types': breakdown,
                'total_types': len(breakdown),
            }, 200
        except Exception as e:
            return {'error': f'Failed to retrieve food type breakdown: {str(e)}'}, 500


class AnalyticsSafetyComplianceAPI(Resource):
    """GET /api/analytics/safety-compliance — Food safety compliance metrics."""
    
    def get(self):
        """
        Retrieve platform-wide food safety compliance statistics.
        
        Returns:
            {
                'timestamp': ISO timestamp,
                'data': {
                    'total_donations': int,
                    'donations_with_safety_logs': int,
                    'passed_inspections': int,
                    'failed_inspections': int,
                    'compliance_rate': float,
                    'avg_safety_score': float,
                    'score_distribution': {
                        'excellent_90_100': int,
                        'good_70_89': int,
                        'fair_50_69': int,
                        'poor_below_50': int,
                    },
                    'requiring_review': int,
                    'high_risk_count': int,
                }
            }
        """
        try:
            compliance = AnalyticsCalculator.get_safety_compliance()
            
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'data': compliance,
            }, 200
        except Exception as e:
            return {'error': f'Failed to retrieve safety compliance: {str(e)}'}, 500


class AnalyticsExportAPI(Resource):
    """GET /api/analytics/export — Export analytics data."""
    
    def get(self):
        """
        Export analytics data in CSV format.
        
        Query params:
            format (str, optional): Export format, currently supports 'csv' (default)
            scope (str, optional): Export scope - 'overview', 'weekly', 'all' (default: 'all')
        
        Returns:
            CSV file with analytics data
        """
        try:
            export_format = request.args.get('format', 'csv').lower()
            scope = request.args.get('scope', 'all').lower()
            
            if export_format not in ['csv']:
                return {'error': 'Unsupported format. Currently supports: csv'}, 400
            
            # Generate CSV based on scope
            if scope == 'overview':
                csv_data = _generate_overview_csv()
            elif scope == 'weekly':
                csv_data = _generate_weekly_csv()
            elif scope == 'all':
                csv_data = _generate_all_csv()
            else:
                return {'error': 'Invalid scope. Options: overview, weekly, all'}, 400
            
            # Return as CSV file download
            from flask import make_response
            response = make_response(csv_data)
            response.headers['Content-Disposition'] = f'attachment; filename=hunger_heroes_analytics_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
            response.headers['Content-Type'] = 'text/csv'
            return response, 200
            
        except Exception as e:
            return {'error': f'Failed to export analytics: {str(e)}'}, 500


def _generate_overview_csv():
    """Generate overview statistics CSV."""
    stats = AnalyticsCalculator.get_overview_stats()
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Hunger Heroes Analytics - Overview Report'])
    writer.writerow(['Generated', datetime.utcnow().isoformat()])
    writer.writerow([])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Total Donations', stats['total_donations']])
    writer.writerow(['Total Servings', stats['total_servings']])
    writer.writerow(['Total Pounds Redistributed', stats['total_pounds']])
    writer.writerow(['Active Donors', stats['active_donors']])
    writer.writerow(['Active Receivers', stats['active_receivers']])
    writer.writerow(['Active Volunteers', stats['active_volunteers']])
    writer.writerow(['Average Response Time (minutes)', stats['avg_response_time_minutes']])
    writer.writerow(['Completion Rate (%)', stats['completion_rate']])
    writer.writerow(['Food Waste Diverted (lbs)', stats['food_waste_diverted_lbs']])
    writer.writerow(['CO2 Emissions Prevented (lbs)', stats['co2_prevented_lbs']])
    
    return output.getvalue()


def _generate_weekly_csv():
    """Generate weekly trends CSV."""
    trends = AnalyticsCalculator.get_weekly_trends(weeks_back=12)
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Hunger Heroes Analytics - Weekly Trends (12 weeks)'])
    writer.writerow(['Generated', datetime.utcnow().isoformat()])
    writer.writerow(['Overall Trend', trends['trend']])
    writer.writerow([])
    
    writer.writerow([
        'Week Start',
        'Week End',
        'Donations Posted',
        'Donations Completed',
        'Pounds Redistributed',
        'Servings Redistributed',
        'New Donors',
        'Volunteers Active'
    ])
    
    for week in trends['weeks']:
        writer.writerow([
            week['week_start'],
            week['week_end'],
            week['donations_posted'],
            week['donations_completed'],
            week['pounds_redistributed'],
            week['servings_redistributed'],
            week['new_donors'],
            week['volunteers_active'],
        ])
    
    return output.getvalue()


def _generate_all_csv():
    """Generate comprehensive analytics CSV."""
    # Overview
    overview = AnalyticsCalculator.get_overview_stats()
    
    # Food types
    food_types = AnalyticsCalculator.get_food_type_breakdown()
    
    # Safety compliance
    compliance = AnalyticsCalculator.get_safety_compliance()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Hunger Heroes Analytics - Comprehensive Report'])
    writer.writerow(['Generated', datetime.utcnow().isoformat()])
    writer.writerow([])
    
    # Overview Section
    writer.writerow(['OVERVIEW STATISTICS'])
    writer.writerow(['Metric', 'Value'])
    for key, value in overview.items():
        writer.writerow([key.replace('_', ' ').title(), value])
    
    writer.writerow([])
    writer.writerow(['FOOD TYPE BREAKDOWN'])
    writer.writerow(['Food Type', 'Count', 'Pounds', 'Servings', 'Avg Response Time (min)', 'Completion Rate (%)'])
    for food_type, stats in food_types.items():
        writer.writerow([
            food_type,
            stats['count'],
            stats['pounds'],
            stats['servings'],
            stats['avg_response_time_minutes'],
            stats['completion_rate'],
        ])
    
    writer.writerow([])
    writer.writerow(['SAFETY COMPLIANCE'])
    writer.writerow(['Metric', 'Value'])
    for key, value in compliance.items():
        if key == 'score_distribution':
            writer.writerow(['Score Distribution', ''])
            for dist_key, dist_val in value.items():
                writer.writerow([f'  {dist_key}', dist_val])
        else:
            writer.writerow([key.replace('_', ' ').title(), value])
    
    return output.getvalue()


# Register routes
api.add_resource(AnalyticsOverviewAPI, '/analytics/overview')
api.add_resource(AnalyticsWeeklyAPI, '/analytics/weekly')
api.add_resource(AnalyticsOrganizationAPI, '/analytics/by-organization/<int:organization_id>')
api.add_resource(AnalyticsDonorAPI, '/analytics/by-donor/<int:donor_id>')
api.add_resource(AnalyticsFoodTypesAPI, '/analytics/food-types')
api.add_resource(AnalyticsSafetyComplianceAPI, '/analytics/safety-compliance')
api.add_resource(AnalyticsExportAPI, '/analytics/export')
