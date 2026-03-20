# services/analytics_calculator.py — Analytics & Impact Metrics Calculator
"""
Analytics Calculator Service

Provides comprehensive analytics calculations for:
- Platform-wide statistics
- Weekly trends
- Organization-specific metrics
- Donor impact tracking
- Food type breakdowns
- Safety compliance metrics
"""

from datetime import datetime, timedelta, date
from sqlalchemy import func, and_, or_
from sqlalchemy.sql import text

from __init__ import db
from model.donation import Donation, DonationStatusLog, VolunteerAssignment
from model.user import User
from model.organization import Organization
from model.food_safety_log import FoodSafetyLog
from model.allergen_profile import AllergenProfile


class AnalyticsCalculator:
    """
    Analytics service for calculating platform-wide and segment-specific metrics.
    
    Key metrics:
    - Total donations, servings, pounds redistributed
    - Active participants (donors, receivers, volunteers)
    - Response times and completion rates
    - Food waste diverted and CO2 prevented (environmental impact)
    - Safety compliance tracking
    - Donor/organization impact history
    """
    
    # CO2 emissions prevention factor (lbs of food waste → lbs of CO2 prevented)
    # Based on EPA data: ~7.19 lbs CO2 equivalent per pound of food waste diverted
    CO2_PREVENTION_FACTOR = 7.19
    
    # Average food weight per serving (lbs) - used when serving_count available
    LBS_PER_SERVING = 0.5
    
    @staticmethod
    def get_overview_stats():
        """
        Calculate platform-wide overview statistics.
        
        Returns:
            dict: Overview stats including:
                - total_donations: Total donations posted
                - total_servings: Total servings redistributed
                - total_pounds: Total food weight redistributed (lbs)
                - active_donors: Unique donor count
                - active_receivers: Unique receiver count
                - active_volunteers: Total volunteer assignments
                - avg_response_time_minutes: Avg time from posted to claimed
                - completion_rate: % of donations completed/confirmed
                - food_waste_diverted_lbs: Estimated food waste prevented
                - co2_prevented_lbs: Estimated CO2 emissions prevented
        """
        # Total donations
        total_donations = Donation.query.filter_by(is_archived=False).count()
        
        # Count by status to understand overall platform health
        completed_donations = Donation.query.filter(
            Donation.status.in_(['confirmed', 'delivered']),
            Donation.is_archived == False
        ).count()
        
        # Servings and pounds
        total_servings = db.session.query(
            func.coalesce(func.sum(Donation.serving_count), 0)
        ).filter(
            Donation.status.in_(['confirmed', 'delivered']),
            Donation.is_archived == False
        ).scalar() or 0
        
        # Calculate pounds: use weight_lbs if available, else estimate from servings
        total_pounds_query = db.session.query(
            func.coalesce(func.sum(Donation.weight_lbs), 0)
        ).filter(
            Donation.status.in_(['confirmed', 'delivered']),
            Donation.is_archived == False
        ).scalar() or 0
        
        estimated_pounds_from_servings = (total_servings * AnalyticsCalculator.LBS_PER_SERVING)
        total_pounds = max(total_pounds_query, estimated_pounds_from_servings)
        
        # Active participants
        active_donors = db.session.query(func.count(func.distinct(Donation.donor_id))).filter(
            Donation.donor_id.isnot(None),
            Donation.is_archived == False
        ).scalar() or 0
        
        active_receivers = db.session.query(func.count(func.distinct(Donation.receiver_id))).filter(
            Donation.receiver_id.isnot(None),
            Donation.is_archived == False
        ).scalar() or 0
        
        active_volunteers = VolunteerAssignment.query.count()
        
        # Average response time (posted → claimed in minutes)
        avg_response_minutes = 0
        claimed_donations = Donation.query.filter(
            Donation.claimed_at.isnot(None),
            Donation.created_at.isnot(None),
            Donation.is_archived == False
        ).all()
        
        if claimed_donations:
            response_times = []
            for d in claimed_donations:
                response = (d.claimed_at - d.created_at).total_seconds() / 60
                response_times.append(response)
            avg_response_minutes = sum(response_times) / len(response_times)
        
        # Completion rate
        completion_rate = 0
        if total_donations > 0:
            completion_rate = (completed_donations / total_donations) * 100
        
        # Environmental impact
        food_waste_diverted_lbs = total_pounds
        co2_prevented_lbs = food_waste_diverted_lbs * AnalyticsCalculator.CO2_PREVENTION_FACTOR
        
        return {
            'total_donations': total_donations,
            'total_servings': int(total_servings),
            'total_pounds': round(total_pounds, 2),
            'active_donors': int(active_donors),
            'active_receivers': int(active_receivers),
            'active_volunteers': int(active_volunteers),
            'avg_response_time_minutes': round(avg_response_minutes, 2),
            'completion_rate': round(completion_rate, 2),
            'food_waste_diverted_lbs': round(food_waste_diverted_lbs, 2),
            'co2_prevented_lbs': round(co2_prevented_lbs, 2),
        }
    
    @staticmethod
    def get_weekly_trends(weeks_back=4):
        """
        Calculate week-over-week trends.
        
        Args:
            weeks_back (int): Number of weeks to retrieve (default: 4)
        
        Returns:
            dict: Weekly data with keys:
                - weeks: Array of weekly statistics
                - trend: Overall trend direction (up, down, stable)
        """
        trends = []
        
        for i in range(weeks_back, 0, -1):
            week_start = datetime.utcnow() - timedelta(days=7*i)
            week_end = datetime.utcnow() - timedelta(days=7*(i-1))
            
            # Donations posted in week
            posted = Donation.query.filter(
                Donation.created_at >= week_start,
                Donation.created_at < week_end,
                Donation.is_archived == False
            ).count()
            
            # Donations completed in week
            completed = Donation.query.filter(
                Donation.confirmed_at >= week_start,
                Donation.confirmed_at < week_end,
                Donation.is_archived == False
            ).count()
            
            # Pounds redistributed
            pounds = db.session.query(
                func.coalesce(func.sum(Donation.weight_lbs), 0)
            ).filter(
                Donation.confirmed_at >= week_start,
                Donation.confirmed_at < week_end,
                Donation.is_archived == False
            ).scalar() or 0
            
            # Servings
            servings = db.session.query(
                func.coalesce(func.sum(Donation.serving_count), 0)
            ).filter(
                Donation.confirmed_at >= week_start,
                Donation.confirmed_at < week_end,
                Donation.is_archived == False
            ).scalar() or 0
            
            # New donors
            new_donors = db.session.query(func.count(func.distinct(Donation.donor_id))).filter(
                Donation.created_at >= week_start,
                Donation.created_at < week_end,
                Donation.donor_id.isnot(None),
                Donation.is_archived == False
            ).scalar() or 0
            
            # Volunteers active
            volunteers = VolunteerAssignment.query.filter(
                VolunteerAssignment.assigned_at >= week_start,
                VolunteerAssignment.assigned_at < week_end
            ).count()
            
            trends.append({
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'donations_posted': int(posted),
                'donations_completed': int(completed),
                'pounds_redistributed': round(pounds, 2),
                'servings_redistributed': int(servings),
                'new_donors': int(new_donors),
                'volunteers_active': int(volunteers),
            })
        
        # Determine trend direction
        trend = 'stable'
        if len(trends) >= 2:
            latest = trends[-1]['donations_completed']
            previous = trends[-2]['donations_completed']
            if latest > previous * 1.1:
                trend = 'up'
            elif latest < previous * 0.9:
                trend = 'down'
        
        return {
            'weeks': trends,
            'trend': trend,
            'period_days': weeks_back * 7,
        }
    
    @staticmethod
    def get_organization_stats(organization_id):
        """
        Calculate statistics for a specific organization.
        
        Args:
            organization_id (int): Organization ID
        
        Returns:
            dict: Organization statistics including:
                - organization_name, type, address
                - donations_received: Total donations
                - servings_received: Total servings
                - pounds_received: Total food weight (lbs)
                - food_types: Breakdown by food type
                - avg_safety_score: Average safety score
                - volunteers_helped: Count of volunteer assignments
        """
        org = Organization.query.get(organization_id)
        if not org:
            return {'error': 'Organization not found'}, 404
        
        # Donations where receiver is from this org
        donations = Donation.query.filter(
            Donation.receiver_id.in_(
                db.session.query(User.id).filter_by(_organization_id=organization_id)
            ),
            Donation.is_archived == False
        ).all()
        
        total_donations = len(donations)
        
        # Aggregate metrics
        total_servings = sum(d.serving_count or 0 for d in donations)
        total_pounds = sum(d.weight_lbs or 0 for d in donations)
        
        # Food type breakdown
        food_type_breakdown = {}
        for d in donations:
            ft = d.food_type or d.category or 'unknown'
            if ft not in food_type_breakdown:
                food_type_breakdown[ft] = {'count': 0, 'pounds': 0}
            food_type_breakdown[ft]['count'] += 1
            food_type_breakdown[ft]['pounds'] += d.weight_lbs or 0
        
        # Average safety score
        avg_safety = 100
        if donations:
            avg_safety = sum(d.safety_score or 100 for d in donations) / len(donations)
        
        # Volunteers helped
        volunteers_assigned = VolunteerAssignment.query.filter(
            VolunteerAssignment.donation_id.in_([d.id for d in donations])
        ).count()
        
        return {
            'organization_id': organization_id,
            'organization_name': org.name,
            'organization_type': org.type,
            'address': org.address,
            'donations_received': total_donations,
            'servings_received': total_servings,
            'pounds_received': round(total_pounds, 2),
            'food_type_breakdown': {
                k: {'count': v['count'], 'pounds': round(v['pounds'], 2)}
                for k, v in food_type_breakdown.items()
            },
            'avg_safety_score': round(avg_safety, 2),
            'volunteers_helped': int(volunteers_assigned),
        }
    
    @staticmethod
    def get_donor_stats(donor_id):
        """
        Calculate donor impact history and statistics.
        
        Args:
            donor_id (int): Donor (User) ID
        
        Returns:
            dict: Donor statistics including:
                - donor_name, email
                - total_donations: Total donations made
                - total_servings: Total servings provided
                - total_pounds: Total pounds provided
                - food_types_donated: Breakdown by type
                - avg_response_time: Avg time to claim
                - completion_rate: % completed successfully
                - impact_co2_prevented: CO2 emissions prevented
                - donation_history: Recent donations
        """
        donor = User.query.get(donor_id)
        if not donor:
            return {'error': 'Donor not found'}, 404
        
        donations = Donation.query.filter_by(
            donor_id=donor_id,
            is_archived=False
        ).all()
        
        total_donations = len(donations)
        
        # Servings and pounds
        total_servings = sum(d.serving_count or 0 for d in donations)
        total_pounds = sum(d.weight_lbs or 0 for d in donations)
        
        # Food types breakdown
        food_types = {}
        for d in donations:
            ft = d.food_type or d.category or 'unknown'
            food_types[ft] = food_types.get(ft, 0) + 1
        
        # Response time
        response_times = []
        for d in donations:
            if d.claimed_at and d.created_at:
                response = (d.claimed_at - d.created_at).total_seconds() / 60
                response_times.append(response)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Completion rate
        completed = sum(1 for d in donations if d.status in ['confirmed', 'delivered'])
        completion_rate = (completed / total_donations * 100) if total_donations > 0 else 0
        
        # CO2 prevented
        co2_prevented = total_pounds * AnalyticsCalculator.CO2_PREVENTION_FACTOR
        
        # Recent donations (last 5)
        recent = sorted(donations, key=lambda d: d.created_at, reverse=True)[:5]
        
        return {
            'donor_id': donor_id,
            'donor_name': getattr(donor, '_name', 'Unknown'),
            'donor_email': getattr(donor, '_email', ''),
            'total_donations': total_donations,
            'total_servings': total_servings,
            'total_pounds': round(total_pounds, 2),
            'food_types_donated': food_types,
            'avg_response_time_minutes': round(avg_response_time, 2),
            'completion_rate': round(completion_rate, 2),
            'impact_co2_prevented': round(co2_prevented, 2),
            'recent_donations': [
                {
                    'id': d.id,
                    'food_name': d.food_name,
                    'quantity': d.quantity,
                    'unit': d.unit,
                    'status': d.status,
                    'created_at': d.created_at.isoformat() if d.created_at else None,
                }
                for d in recent
            ],
        }
    
    @staticmethod
    def get_food_type_breakdown():
        """
        Calculate donation breakdown by food type.
        
        Returns:
            dict: Food type metrics including:
                - food_type: Food type name
                - count: Number of donations
                - pounds: Total pounds
                - servings: Total servings
                - avg_response_time: Average time to claim
                - completion_rate: Completion percentage
        """
        donations = Donation.query.filter_by(is_archived=False).all()
        
        breakdown = {}
        for d in donations:
            ft = d.food_type or d.category or 'unknown'
            if ft not in breakdown:
                breakdown[ft] = {
                    'count': 0,
                    'pounds': 0,
                    'servings': 0,
                    'response_times': [],
                    'completed': 0,
                }
            
            breakdown[ft]['count'] += 1
            breakdown[ft]['pounds'] += d.weight_lbs or 0
            breakdown[ft]['servings'] += d.serving_count or 0
            
            if d.claimed_at and d.created_at:
                response = (d.claimed_at - d.created_at).total_seconds() / 60
                breakdown[ft]['response_times'].append(response)
            
            if d.status in ['confirmed', 'delivered']:
                breakdown[ft]['completed'] += 1
        
        # Format results
        results = {}
        for ft, stats in breakdown.items():
            avg_response = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
            completion_rate = (stats['completed'] / stats['count'] * 100) if stats['count'] > 0 else 0
            
            results[ft] = {
                'count': stats['count'],
                'pounds': round(stats['pounds'], 2),
                'servings': stats['servings'],
                'avg_response_time_minutes': round(avg_response, 2),
                'completion_rate': round(completion_rate, 2),
            }
        
        return results
    
    @staticmethod
    def get_safety_compliance():
        """
        Calculate platform-wide food safety compliance metrics.
        
        Returns:
            dict: Safety metrics including:
                - total_with_logs: Donations with safety logs
                - passed_inspections: Count/percentage passed
                - failed_inspections: Count/percentage failed
                - avg_safety_score: Average safety score
                - score_distribution: Distribution by score ranges
                - requiring_review: Donations flagged for review
                - high_risk_count: Donations with score < 50
        """
        all_donations = Donation.query.filter_by(is_archived=False).all()
        total = len(all_donations)
        
        # Count donations with safety logs
        with_logs = db.session.query(func.count(func.distinct(FoodSafetyLog.donation_id))).scalar() or 0
        
        # Count passed/failed inspections
        passed = db.session.query(func.count()).filter(
            FoodSafetyLog.passed_inspection == True
        ).scalar() or 0
        
        failed = db.session.query(func.count()).filter(
            FoodSafetyLog.passed_inspection == False
        ).scalar() or 0
        
        # Average safety score
        avg_score = db.session.query(
            func.coalesce(func.avg(Donation.safety_score), 100)
        ).filter(
            Donation.is_archived == False
        ).scalar() or 100
        
        # Score distribution
        excellent = len([d for d in all_donations if d.safety_score >= 90])
        good = len([d for d in all_donations if 70 <= d.safety_score < 90])
        fair = len([d for d in all_donations if 50 <= d.safety_score < 70])
        poor = len([d for d in all_donations if d.safety_score < 50])
        
        # Requiring review
        requiring_review = len([d for d in all_donations if d.requires_review])
        
        # Compliance percentage (passed inspections / total with logs)
        compliance_rate = 0
        if with_logs > 0:
            compliance_rate = (passed / (passed + failed) * 100) if (passed + failed) > 0 else 0
        
        return {
            'total_donations': total,
            'donations_with_safety_logs': int(with_logs),
            'passed_inspections': int(passed),
            'failed_inspections': int(failed),
            'compliance_rate': round(compliance_rate, 2),
            'avg_safety_score': round(avg_score, 2),
            'score_distribution': {
                'excellent_90_100': excellent,
                'good_70_89': good,
                'fair_50_69': fair,
                'poor_below_50': poor,
            },
            'requiring_review': int(requiring_review),
            'high_risk_count': poor,
        }
