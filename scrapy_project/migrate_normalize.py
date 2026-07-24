"""
One-time migration: normalise all existing rows in scraped_ads.db.

Changes applied:
- Adds columns: price_amount, price_eur, price_mkd, price_note  (if missing)
- Splits raw price string into amount + currency + EUR/MKD equivalents
- Resolves relative posted_date strings ("Денес", "Вчера") to ISO dates (YYYY-MM-DD)
- Parses absolute Macedonian date strings ("01 авг. 10:30") to ISO dates
- Strips emojis from title and description
- Fixes scraped_at to include UTC timezone marker (+00:00)

Run once: python migrate_normalize.py
"""
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ads_scraper.normalize import clean_text, parse_price, resolve_posted_date, strip_emoji

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
DB_PATH = Path(__file__).resolve().parent / 'scraped_ads.db'

NEW_COLUMNS = [
    ('price_amount', 'TEXT'),
    ('price_eur',    'REAL'),
    ('price_mkd',    'REAL'),
    ('price_note',   'TEXT'),
]


def add_missing_columns(cur):
    existing = {r[1] for r in cur.execute('PRAGMA table_info(ads)')}
    for col, col_type in NEW_COLUMNS:
        if col not in existing:
            cur.execute(f'ALTER TABLE ads ADD COLUMN {col} {col_type}')
            logging.info('Added column %s %s', col, col_type)


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    add_missing_columns(cur)
    conn.commit()

    rows = cur.execute(
        'SELECT ad_url, title, description, price, posted_date, scraped_at FROM ads'
    ).fetchall()
    logging.info('Processing %d rows...', len(rows))

    batch = []
    for ad_url, title, description, price, posted_date, scraped_at in rows:
        # Fix scraped_at timezone marker
        new_scraped_at = scraped_at
        if scraped_at and '+' not in scraped_at and not scraped_at.endswith('Z'):
            new_scraped_at = scraped_at + '+00:00'

        new_title = strip_emoji(clean_text(title))
        new_desc = strip_emoji(clean_text(description))

        p = parse_price(price)
        new_posted = resolve_posted_date(posted_date, new_scraped_at) or posted_date

        batch.append((
            new_title, new_desc,
            p['price_amount'], p['currency'], p['price_eur'], p['price_mkd'], p['price_note'],
            new_posted, new_scraped_at,
            ad_url,
        ))

    cur.executemany(
        '''UPDATE ads SET
               title=?, description=?,
               price_amount=?, currency=?, price_eur=?, price_mkd=?, price_note=?,
               posted_date=?, scraped_at=?
           WHERE ad_url=?''',
        batch,
    )
    conn.commit()
    conn.close()
    logging.info('Done — updated %d rows.', len(batch))


if __name__ == '__main__':
    migrate()
