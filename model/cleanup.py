# cleanup.py — Week 2: auto_maintenance scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from __init__ import app, db
from model.donation import Donation, log_status_change


def auto_maintenance():
    """
    Three-part automatic maintenance:
    1. Auto-expire: posted donations past their expiry_date → 'expired'
    2. Auto-archive confirmed: confirmed donations older than 24 hours → is_archived = True
    3. Auto-archive delivered: delivered donations older than 48 hours → is_archived = True
    """
    with app.app_context():
        now = datetime.utcnow()
        today_date = now.date()
        archived_count = 0
        expired_count = 0

        # 1. Auto-expire posted donations past expiry
        posted_past = Donation.query.filter(
            Donation.status == 'posted',
            Donation.is_archived == False,
            Donation.expiry_date < today_date
        ).all()
        for d in posted_past:
            log_status_change(d.id, 'posted', 'expired', 'system',
                              'Auto-expired by scheduler')
            d.status = 'expired'
            expired_count += 1

        # 2. Archive confirmed donations after 24 hours
        confirmed_cutoff = now - timedelta(hours=24)
        confirmed_old = Donation.query.filter(
            Donation.status == 'confirmed',
            Donation.is_archived == False,
            Donation.confirmed_at <= confirmed_cutoff
        ).all()
        for d in confirmed_old:
            d.is_archived = True
            archived_count += 1

        # 3. Archive delivered donations after 48 hours
        delivered_cutoff = now - timedelta(hours=48)
        delivered_old = Donation.query.filter(
            Donation.status == 'delivered',
            Donation.is_archived == False,
            Donation.delivered_at <= delivered_cutoff
        ).all()
        for d in delivered_old:
            d.is_archived = True
            archived_count += 1

        if expired_count or archived_count:
            db.session.commit()
            print(f"� Auto-maintenance: expired={expired_count}, archived={archived_count}")


def start_cleanup_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=auto_maintenance,
        trigger='interval',
        minutes=30,
        id='donation_auto_maintenance',
        name='Auto-maintenance: expire, archive confirmed/delivered',
        replace_existing=True
    )
    scheduler.start()
    print("✅ APScheduler started for donation auto-maintenance.")
