"""
Push all rows from local SQLite to Supabase.
Run after migrate_normalize.py.

Usage: python push_to_supabase.py
"""
import json
import logging
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
DB_PATH = Path(__file__).resolve().parent / 'scraped_ads.db'
BATCH_SIZE = 500


import re

_ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


def parse_json_field(val, fallback):
    if val is None:
        return fallback
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return fallback


def safe_date(val):
    """Return val if it looks like YYYY-MM-DD, else None."""
    if val and _ISO_DATE_RE.match(str(val)):
        return val
    return None


def push():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    rows = conn.execute('SELECT * FROM ads').fetchall()
    total = len(rows)
    logging.info('Loaded %d rows from SQLite', total)

    batch = []
    pushed = 0

    for row in rows:
        d = dict(row)
        d['images'] = parse_json_field(d.get('images'), [])
        d['specs'] = parse_json_field(d.get('specs'), {})
        d['posted_date'] = safe_date(d.get('posted_date'))
        if not d.get('scraped_at'):
            d['scraped_at'] = None
        batch.append(d)

        if len(batch) >= BATCH_SIZE:
            sb.table('ads').upsert(batch, on_conflict='ad_url').execute()
            pushed += len(batch)
            logging.info('  %d / %d', pushed, total)
            batch = []

    if batch:
        sb.table('ads').upsert(batch, on_conflict='ad_url').execute()
        pushed += len(batch)

    conn.close()
    logging.info('Done. Pushed %d rows to Supabase.', pushed)


if __name__ == '__main__':
    push()
