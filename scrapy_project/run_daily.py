"""
Daily incremental scrape + dedup pipeline.

Runs both spiders in incremental mode (stops when it hits already-known ads),
then re-runs the dedup agent on the full dataset.

Schedule via Windows Task Scheduler to run once a day.
"""
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BASE = Path(__file__).parent
PYTHON = sys.executable


def run(cmd: list, label: str):
    log.info("=== START: %s ===", label)
    result = subprocess.run(cmd, cwd=BASE)
    if result.returncode != 0:
        log.error("%s finished with errors (exit code %d)", label, result.returncode)
    else:
        log.info("=== DONE: %s ===", label)


def main():
    log.info("Daily pipeline started at %s", datetime.now().strftime("%Y-%m-%d %H:%M"))

    # Incremental crawl — stops after 10 consecutive known ads
    run([
        "scrapy", "crawl", "pazar3",
        "-s", "INCREMENTAL=1",
        "-s", "DOWNLOAD_DELAY=2",
        "-s", "CONCURRENT_REQUESTS=2",
        "-s", "LOG_LEVEL=WARNING",
    ], "pazar3 incremental crawl")

    run([
        "scrapy", "crawl", "reklama5",
        "-s", "INCREMENTAL=1",
        "-s", "DOWNLOAD_DELAY=2",
        "-s", "CONCURRENT_REQUESTS=2",
        "-s", "LOG_LEVEL=WARNING",
    ], "reklama5 incremental crawl")

    # Re-run dedup on the full dataset
    run([PYTHON, "run_dedup_agent.py", "--clear"], "dedup agent (cross-site)")
    run([PYTHON, "run_dedup_agent.py", "--same-site"], "dedup agent (same-site)")

    log.info("Daily pipeline finished at %s", datetime.now().strftime("%Y-%m-%d %H:%M"))


if __name__ == "__main__":
    main()
