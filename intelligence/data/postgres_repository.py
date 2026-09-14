"""
Corrected version: uses our actual `reports` table's `fingerprint` JSON
column, via the shared app.services.intelligence_data module, instead of
a hardcoded, mismatched database connection.
"""

from app.services.intelligence_data import load_historical_reports_from_db


def load_historical_reports(db=None):
    if db is None:
        raise ValueError("A database session must be provided")
    return load_historical_reports_from_db(db)