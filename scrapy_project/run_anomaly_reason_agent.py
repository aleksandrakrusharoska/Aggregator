"""
Run the anomaly reason agent.

Fetches all anomaly ads that don't yet have an explanation,
calls Groq to explain each unusual price, and writes the result
back to the anomaly_reason column in Supabase.

Usage:
    python run_anomaly_reason_agent.py              # explain all unexplained anomalies
    python run_anomaly_reason_agent.py --limit 50   # explain first 50
    python run_anomaly_reason_agent.py --rerun      # re-explain already explained ones
"""
import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Explain anomaly prices with LLM")
    parser.add_argument("--limit", type=int, default=None, help="Max anomalies to explain")
    parser.add_argument("--rerun", action="store_true", help="Re-explain already explained anomalies")
    args = parser.parse_args()

    for var in ("SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY"):
        if not os.getenv(var):
            sys.exit(f"Missing {var} in .env")

    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    q = (
        sb.table("ads")
        .select("ad_url, title, price_eur, price_zscore, description")
        .eq("is_anomaly", True)
        .not_.is_("description", "null")
        .neq("description", "")
    )
    if not args.rerun:
        q = q.is_("anomaly_reason", "null")
    if args.limit:
        q = q.limit(args.limit)

    rows = q.execute().data
    if not rows:
        log.info("No anomalies need explaining.")
        return

    log.info("Found %d anomalies to explain...", len(rows))

    from agents.anomaly_reason_agent import explain_anomalies
    results = explain_anomalies(rows)

    for i in range(0, len(results), 50):
        sb.table("ads").upsert(results[i:i + 50], on_conflict="ad_url").execute()

    explained = sum(1 for r in results if r.get("anomaly_reason"))
    log.info("Done. Explained %d / %d anomalies.", explained, len(results))


if __name__ == "__main__":
    main()
