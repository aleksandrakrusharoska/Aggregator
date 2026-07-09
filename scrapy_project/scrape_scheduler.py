"""
APScheduler-based scheduler to run scrape_and_store.py daily and log results.
Usage:
  python scrape_scheduler.py

Installs:
  pip install apscheduler

This runs continuously (BlockingScheduler). To run in background on Windows, use run_scrape_scheduler.bat with a loong-running runner or configure Task Scheduler to start the script at boot.
"""
import subprocess
import logging
import sys
import argparse
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
HERE = __import__('pathlib').Path(__file__).resolve().parent
PY = sys.executable or 'python'
SCRAPE_SCRIPT = HERE / 'scrape_and_store.py'

def run_job():
    logging.info('Starting scheduled scrape: %s', SCRAPE_SCRIPT)
    start = datetime.utcnow()
    try:
        res = subprocess.run([PY, str(SCRAPE_SCRIPT)], cwd=str(HERE))
        if res.returncode == 0:
            logging.info('scrape_and_store completed successfully')
        else:
            logging.error('scrape_and_store exited with code %s', res.returncode)
    except Exception as e:
        logging.exception('scrape_and_store failed: %s', e)
    finally:
        elapsed = (datetime.utcnow() - start).total_seconds()
        logging.info('Job finished in %.1f seconds', elapsed)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--hour', type=int, default=3, help='Hour in local time (0-23)')
    parser.add_argument('--minute', type=int, default=0, help='Minute in local time (0-59)')
    parser.add_argument('--run-now', action='store_true', help='Run one scrape immediately at startup')
    args = parser.parse_args()

    scheduler = BlockingScheduler()
    trigger = CronTrigger(hour=args.hour, minute=args.minute)
    scheduler.add_job(run_job, trigger, id='daily-scrape', replace_existing=True)
    next_run = scheduler.get_job('daily-scrape').next_run_time
    logging.info('Scheduler started. Next run: %s', next_run)

    if args.run_now:
        run_job()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info('Scheduler stopped')
