"""
Run spiders and store new items into a local SQLite DB.
Usage:
  python scrape_and_store.py            # run spiders once and exit
  python scrape_and_store.py --pazar3   # run only pazar3 spider
  python scrape_and_store.py --reklama5 # run only reklama5 spider

To schedule daily on Windows:
- Use Task Scheduler to run run_scrape.bat daily (example provided).
"""
import subprocess
import sqlite3
import json
from pathlib import Path
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

HERE = Path(__file__).resolve().parent
JLS = {
    'pazar3': HERE / 'pazar3_items.jl',
    'reklama5': HERE / 'reklama5_items.jl',
}
DB_PATH = HERE / 'scraped_ads.db'
DEFAULT_PAZAR3_URL = 'https://www.pazar3.mk/oglasi/elektronika/prodazba-kupuvanje-zamena'
DEFAULT_REKLAMA5_URL = 'https://reklama5.mk/Search?city=&cat=580&q=&sell=0&sell=1&buy=0&buy=1&trade=0&trade=1&includeOld=0&includeOld=1&includeNew=0&includeNew=1&cargoReady=0&DDVIncluded=0&private=0&company=0&page=1&SortByPrice=0&zz=1&pageView='

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS ads (
    ad_url TEXT PRIMARY KEY,
    title TEXT,
    price TEXT,
    currency TEXT,
    location TEXT,
    description TEXT,
    seller_name TEXT,
    phone TEXT,
    images TEXT, -- JSON array
    posted_date TEXT,
    category TEXT,
    condition TEXT,
    specs TEXT, -- JSON object
    source TEXT,
    scraped_at TEXT
);
'''


def run_spider(spider, start_url=None):
    cmd = ['scrapy', 'crawl', spider]
    if start_url:
        cmd += ['-a', f'start_url={start_url}']
    logging.info('Running: %s', ' '.join(cmd))
    res = subprocess.run(cmd, cwd=str(HERE))
    if res.returncode != 0:
        logging.error('Spider %s exited with code %s', spider, res.returncode)
    return res.returncode


def load_jl(path):
    items = []
    if not path.exists():
        logging.info('No file %s', path)
        return items
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception as e:
                logging.warning('Failed to parse line: %s; %s', line[:200], e)
    return items


def ensure_db(conn):
    conn.execute(CREATE_SQL)
    conn.commit()


def upsert_items(conn, items, source):
    cur = conn.cursor()
    inserted = 0
    for it in items:
        ad_url = it.get('ad_url') or it.get('url')
        if not ad_url:
            continue
        title = it.get('title')
        price = it.get('price')
        currency = it.get('currency')
        location = it.get('location')
        description = it.get('description')
        seller_name = it.get('seller_name')
        phone = it.get('phone')
        images = json.dumps(it.get('images') or [])
        posted_date = it.get('posted_date')
        category = it.get('category')
        condition = it.get('condition')
        specs = json.dumps(it.get('specs') or {})
        scraped_at = datetime.utcnow().isoformat()
        try:
            cur.execute('INSERT OR IGNORE INTO ads (ad_url,title,price,currency,location,description,seller_name,phone,images,posted_date,category,condition,specs,source,scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (ad_url,title,price,currency,location,description,seller_name,phone,images,posted_date,category,condition,specs,source,scraped_at))
            if cur.rowcount == 1:
                inserted += 1
        except Exception as e:
            logging.warning('DB insert failed for %s: %s', ad_url, e)
    conn.commit()
    return inserted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pazar3', action='store_true')
    parser.add_argument('--reklama5', action='store_true')
    parser.add_argument('--pazar3-url', default=DEFAULT_PAZAR3_URL, help='Pazar3 start URL')
    parser.add_argument('--reklama5-url', default=DEFAULT_REKLAMA5_URL, help='Reklama5 start URL')
    args = parser.parse_args()

    run_pazar = args.pazar3 or not (args.pazar3 or args.reklama5)
    run_reklama = args.reklama5 or not (args.pazar3 or args.reklama5)

    # Run spiders
    if run_pazar:
        run_spider('pazar3', start_url=args.pazar3_url)
    if run_reklama:
        run_spider('reklama5', start_url=args.reklama5_url)

    # Load items and upsert into DB
    conn = sqlite3.connect(str(DB_PATH))
    ensure_db(conn)
    total_new = 0
    for name, path in JLS.items():
        items = load_jl(path)
        if not items:
            logging.info('No items found in %s', path)
            continue
        new = upsert_items(conn, items, name)
        logging.info('Inserted %d new items from %s', new, name)
        total_new += new

    conn.close()
    logging.info('Done. Total new items: %d. DB at %s', total_new, DB_PATH)


if __name__ == '__main__':
    main()
