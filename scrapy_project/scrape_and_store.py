"""
Run spiders and store new items into a local SQLite DB.

Modes:
- full: crawl all reachable pages
- incremental: crawl newest N pages only (daily scheduler mode)

Reliability features:
- optional Scrapy JOBDIR for resume support
- optional chunked full crawl (recommended for long pazar3 backfills)
"""
import argparse
import json
import logging
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

HERE = Path(__file__).resolve().parent
JLS = {
    'pazar3': HERE / 'pazar3_items.jl',
    'reklama5': HERE / 'reklama5_items.jl',
}
DB_PATH = HERE / 'scraped_ads.db'
DEFAULT_PAZAR3_URL = 'https://www.pazar3.mk/oglasi/elektronika/prodazba-kupuvanje-zamena'
DEFAULT_REKLAMA5_URLS = [
    'https://reklama5.mk/Search?city=&cat=580&q=&sell=0&sell=1&buy=0&buy=1&trade=0&trade=1&includeOld=0&includeOld=1&includeNew=0&includeNew=1&cargoReady=0&DDVIncluded=0&private=0&company=0&page=1&SortByPrice=0&zz=1&pageView=',
    'https://reklama5.mk/Search?city=&cat=558&q=&sell=0&sell=1&buy=0&buy=1&trade=0&trade=1&includeOld=0&includeOld=1&includeNew=0&includeNew=1&cargoReady=0&DDVIncluded=0&private=0&company=0&page=1&SortByPrice=0&zz=1&pageView=',
]
JOBDIR_ROOT = HERE / '.scrapy-jobdirs'

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS ads (
    ad_url TEXT PRIMARY KEY,
    title TEXT,
    price TEXT,
    currency TEXT,
    price_amount TEXT,
    price_eur REAL,
    price_mkd REAL,
    price_note TEXT,
    location TEXT,
    description TEXT,
    seller_name TEXT,
    phone TEXT,
    images TEXT,
    posted_date TEXT,
    category TEXT,
    condition TEXT,
    specs TEXT,
    source TEXT,
    scraped_at TEXT
);
'''


def set_query_page(url, param_name, page_number):
    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query[param_name] = [str(page_number)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def run_spider(spider, start_url=None, page_limit=None, jobdir=None):
    cmd = ['scrapy', 'crawl', spider]
    if start_url:
        cmd += ['-a', f'start_url={start_url}']
    if page_limit is not None and page_limit > 0:
        cmd += ['-s', f'CLOSESPIDER_PAGECOUNT={page_limit}']
    if jobdir:
        cmd += ['-s', f'JOBDIR={jobdir}']
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
        try:
            cur.execute(
                '''INSERT OR IGNORE INTO ads
                   (ad_url,title,price,currency,price_amount,price_eur,price_mkd,price_note,
                    location,description,seller_name,phone,images,posted_date,
                    category,condition,specs,source,scraped_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (
                    ad_url,
                    it.get('title'),
                    it.get('price'),
                    it.get('currency'),
                    it.get('price_amount'),
                    it.get('price_eur'),
                    it.get('price_mkd'),
                    it.get('price_note'),
                    it.get('location'),
                    it.get('description'),
                    it.get('seller_name'),
                    it.get('phone'),
                    json.dumps(it.get('images') or []),
                    it.get('posted_date'),
                    it.get('category'),
                    it.get('condition'),
                    json.dumps(it.get('specs') or {}),
                    source,
                    it.get('scraped_at') or datetime.now(timezone.utc).isoformat(),
                ),
            )
            if cur.rowcount == 1:
                inserted += 1
        except Exception as e:
            logging.warning('DB insert failed for %s: %s', ad_url, e)
    conn.commit()
    return inserted


def ingest_source(conn, source_name):
    path = JLS[source_name]
    items = load_jl(path)
    if not items:
        logging.info('No items found in %s', path)
        return 0
    new_count = upsert_items(conn, items, source_name)
    logging.info('Inserted %d new items from %s', new_count, source_name)
    return new_count


def run_full_in_chunks(conn, spider, source_name, base_url, page_param, start_page, end_page, chunk_size, use_jobdir):
    total_new = 0
    page = start_page
    while end_page is None or page <= end_page:
        chunk_url = set_query_page(base_url, page_param, page)
        chunk_label = f'{spider}_p{page}_n{chunk_size}'
        jobdir = None
        if use_jobdir:
            JOBDIR_ROOT.mkdir(parents=True, exist_ok=True)
            jobdir = JOBDIR_ROOT / chunk_label
        rc = run_spider(spider, start_url=chunk_url, page_limit=chunk_size, jobdir=jobdir)
        if rc != 0:
            logging.error('Stopping due to spider failure in chunk %s', chunk_label)
            break
        total_new += ingest_source(conn, source_name)
        page += chunk_size
    return total_new


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pazar3', action='store_true')
    parser.add_argument('--reklama5', action='store_true')
    parser.add_argument('--mode', choices=['full', 'incremental'], default='full',
                        help='full=all pages, incremental=only first N pages (newest-first crawl)')
    parser.add_argument('--pazar3-pages', type=int, default=3,
                        help='Pages to crawl for pazar3 in incremental mode')
    parser.add_argument('--reklama5-pages', type=int, default=3,
                        help='Pages to crawl for reklama5 in incremental mode')
    parser.add_argument('--pazar3-url', default=DEFAULT_PAZAR3_URL, help='Pazar3 start URL')

    parser.add_argument('--chunked-full', action='store_true',
                        help='Run full mode in chunks for better reliability')
    parser.add_argument('--chunk-size', type=int, default=100,
                        help='Pages per chunk in chunked full mode')
    parser.add_argument('--start-page', type=int, default=1,
                        help='Start page for chunked full mode')
    parser.add_argument('--end-page', type=int, default=0,
                        help='Optional end page for chunked full mode (0 means no explicit limit)')
    parser.add_argument('--jobdir', action='store_true',
                        help='Enable Scrapy JOBDIR resume support')
    args = parser.parse_args()

    run_pazar = args.pazar3 or not (args.pazar3 or args.reklama5)
    run_reklama = args.reklama5 or not (args.pazar3 or args.reklama5)
    end_page = args.end_page if args.end_page > 0 else None

    conn = sqlite3.connect(str(DB_PATH))
    ensure_db(conn)
    total_new = 0

    if run_pazar:
        if args.mode == 'incremental':
            run_spider('pazar3', start_url=args.pazar3_url, page_limit=args.pazar3_pages, jobdir=(JOBDIR_ROOT / 'pazar3_incremental' if args.jobdir else None))
            total_new += ingest_source(conn, 'pazar3')
        elif args.chunked_full:
            total_new += run_full_in_chunks(
                conn=conn,
                spider='pazar3',
                source_name='pazar3',
                base_url=args.pazar3_url,
                page_param='Page',
                start_page=args.start_page,
                end_page=end_page,
                chunk_size=args.chunk_size,
                use_jobdir=args.jobdir,
            )
        else:
            run_spider('pazar3', start_url=args.pazar3_url, jobdir=(JOBDIR_ROOT / 'pazar3_full' if args.jobdir else None))
            total_new += ingest_source(conn, 'pazar3')

    if run_reklama:
        if args.mode == 'incremental':
            run_spider('reklama5', page_limit=args.reklama5_pages, jobdir=(JOBDIR_ROOT / 'reklama5_incremental' if args.jobdir else None))
            total_new += ingest_source(conn, 'reklama5')
        elif args.chunked_full:
            run_spider('reklama5', jobdir=(JOBDIR_ROOT / 'reklama5_full' if args.jobdir else None))
            total_new += ingest_source(conn, 'reklama5')
        else:
            run_spider('reklama5', jobdir=(JOBDIR_ROOT / 'reklama5_full' if args.jobdir else None))
            total_new += ingest_source(conn, 'reklama5')

    conn.close()
    logging.info('Done. Total new items: %d. DB at %s', total_new, DB_PATH)


if __name__ == '__main__':
    main()
