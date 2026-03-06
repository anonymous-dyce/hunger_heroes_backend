"""
Migration script: Add new fields to the Donation model.

This script adds the following columns to the 'donations' table:
  - food_type, serving_count, weight_lbs          (food details)
  - allergen_info                                   (safety text)
  - temperature_at_pickup, storage_method           (food safety compliance)
  - pickup_location, zip_code                       (pickup location)
  - pickup_window_start, pickup_window_end          (pickup window)
  - donor_id, receiver_id, volunteer_id             (foreign keys)
  - is_archived                                     (soft-delete flag)

Works with both SQLite (dev) and PostgreSQL/MySQL (prod).
Run from the project root:
    python scripts/migrate_donations.py
"""

import sys
import os

# Ensure the project root is on the path so __init__ can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from __init__ import app, db  # noqa: E402
from sqlalchemy import text, inspect  # noqa: E402


# ------------------------------------------------------------------
# Column definitions:  (column_name, SQL type for SQLite, SQL type for MySQL/PG)
# ------------------------------------------------------------------
NEW_COLUMNS = [
    # Food details
    ('food_type',              'VARCHAR(50)',   'VARCHAR(50)'),
    ('serving_count',          'INTEGER',       'INTEGER'),
    ('weight_lbs',             'FLOAT',         'DOUBLE PRECISION'),
    # Safety
    ('allergen_info',          'TEXT',           'TEXT'),
    ('temperature_at_pickup',  'FLOAT',         'DOUBLE PRECISION'),
    ('storage_method',         'VARCHAR(50)',   'VARCHAR(50)'),
    # Pickup
    ('pickup_location',        'VARCHAR(500)',  'VARCHAR(500)'),
    ('zip_code',               'VARCHAR(10)',   'VARCHAR(10)'),
    ('pickup_window_start',    'DATETIME',      'TIMESTAMP'),
    ('pickup_window_end',      'DATETIME',      'TIMESTAMP'),
    # Foreign keys (added as plain INTEGER columns; FK constraints added separately)
    ('donor_id',               'INTEGER',       'INTEGER'),
    ('receiver_id',            'INTEGER',       'INTEGER'),
    ('volunteer_id',           'INTEGER',       'INTEGER'),
    # Soft-delete
    ('is_archived',            'BOOLEAN DEFAULT 0', 'BOOLEAN DEFAULT FALSE'),
]

# Foreign key constraints to add (only for non-SQLite databases)
FK_CONSTRAINTS = [
    ('donor_id',     'users', 'id', 'fk_donation_donor'),
    ('receiver_id',  'users', 'id', 'fk_donation_receiver'),
    ('volunteer_id', 'users', 'id', 'fk_donation_volunteer'),
]


def get_existing_columns(engine, table_name):
    """Return a set of column names that already exist on the table, or None if table doesn't exist."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return None
    return {col['name'] for col in inspector.get_columns(table_name)}


def is_sqlite(engine):
    return 'sqlite' in str(engine.url)


def migrate():
    with app.app_context():
        engine = db.engine
        existing = get_existing_columns(engine, 'donations')

        if existing is None:
            # Table doesn't exist yet — create all tables from models
            print("  📦  'donations' table not found — running db.create_all()")
            # Import all models so SQLAlchemy registers their tables
            from model.donation import Donation  # noqa: F401
            from model.user import User  # noqa: F401
            from model.post import Post  # noqa: F401
            db.create_all()
            print("\n✅ Migration complete — created all tables (fresh database)")
            return

        sqlite = is_sqlite(engine)
        added = []

        with engine.begin() as conn:
            for col_name, sqlite_type, pg_type in NEW_COLUMNS:
                if col_name in existing:
                    print(f"  ⏭  Column '{col_name}' already exists — skipping")
                    continue
                col_type = sqlite_type if sqlite else pg_type
                sql = f"ALTER TABLE donations ADD COLUMN {col_name} {col_type}"
                print(f"  ➕  {sql}")
                conn.execute(text(sql))
                added.append(col_name)

            # Add FK constraints for non-SQLite databases
            if not sqlite:
                for col, ref_table, ref_col, constraint_name in FK_CONSTRAINTS:
                    if col not in added and col in existing:
                        continue  # column existed before, assume FK is set
                    try:
                        sql = (
                            f"ALTER TABLE donations ADD CONSTRAINT {constraint_name} "
                            f"FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col})"
                        )
                        print(f"  🔗  {sql}")
                        conn.execute(text(sql))
                    except Exception as e:
                        print(f"  ⚠️  FK constraint '{constraint_name}' skipped: {e}")

        if added:
            print(f"\n✅ Migration complete — added {len(added)} column(s): {', '.join(added)}")
        else:
            print("\n✅ Migration complete — no new columns needed (all already present)")


if __name__ == '__main__':
    print("=== Donation Model Migration ===")
    migrate()
