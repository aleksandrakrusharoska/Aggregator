"""
Batch-processes ads in Supabase with the LLM parser agent.

Reads ads where:
  - description is not null/empty
  - llm_parsed_at is null (not yet processed)

Writes back: specs, condition, seller_notes, phone,
             delivery_available, seller_type, llm_parsed_at

Usage:
    python run_parser_agent.py              # process all pending
    python run_parser_agent.py --limit 20  # test run with 20 ads
    python run_parser_agent.py --source pazar3  # only one source
    python run_parser_agent.py --reparse   # reparse already-processed ads
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client

from agents.parser_agent import ParsedAdContent, build_parser, parse_ad

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FETCH_BATCH = 50  # rows per Supabase page


def fetch_pending(sb, source=None, reparse=False, limit=None):
    """Yield rows that need LLM parsing, including existing condition/seller_type to avoid overwriting."""
    offset = 0
    fetched = 0
    while True:
        q = (
            sb.table("ads")
            .select("ad_url, title, description, condition, seller_type")
            .not_.is_("description", "null")
            .neq("description", "")
        )
        if not reparse:
            q = q.is_("llm_parsed_at", "null")
        if source:
            q = q.eq("source", source)
        page_limit = FETCH_BATCH
        if limit is not None:
            page_limit = min(FETCH_BATCH, limit - fetched)
        result = q.range(offset, offset + page_limit - 1).execute()
        rows = result.data
        if not rows:
            break
        for row in rows:
            yield row
            fetched += 1
            if limit is not None and fetched >= limit:
                return
        if len(rows) < page_limit:
            break
        offset += page_limit


def update_batch(sb, updates: list[dict]):
    try:
        sb.table("ads").upsert(updates, on_conflict="ad_url").execute()
    except Exception as exc:
        log.error("Supabase upsert failed: %s", exc)


def main():
    parser = argparse.ArgumentParser(description="Run LLM parser agent on Supabase ads")
    parser.add_argument("--limit", type=int, default=None, help="Max ads to process")
    parser.add_argument("--source", default=None, choices=["reklama5", "pazar3"], help="Filter by source")
    parser.add_argument("--reparse", action="store_true", help="Re-run even on already-parsed ads")
    args = parser.parse_args()

    if not SUPABASE_URL or not SUPABASE_KEY:
        sys.exit("Missing SUPABASE_URL or SUPABASE_KEY in environment / .env")

    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    llm_parser = build_parser()
    log.info("Connected to Supabase. LLM parser ready (%s).", os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))

    processed = 0
    flush_every = 10
    pending_updates: list[dict] = []

    for row in fetch_pending(sb, source=args.source, reparse=args.reparse, limit=args.limit):
        ad_url = row["ad_url"]
        title = row.get("title") or ""
        description = row.get("description") or ""

        log.info("[%d] Parsing: %s", processed + 1, title[:60])
        parsed: ParsedAdContent = parse_ad(title, description, llm_parser)
        time.sleep(4)  # stay under Groq free tier 30 req/min limit

        # Filter empty-string values from specs
        clean_specs = {k: v for k, v in (parsed.specs or {}).items() if v and v.strip()}

        update: dict = {
            "ad_url": ad_url,
            "specs": clean_specs,
            "seller_notes": parsed.seller_notes,
            "phone": parsed.phone,
            "delivery_available": bool(parsed.delivery_available),
            "llm_parsed_at": datetime.now(timezone.utc).isoformat(),
        }
        # Only fill condition/seller_type if the spider didn't already capture them
        if not row.get("condition") and parsed.condition:
            update["condition"] = parsed.condition
        if not row.get("seller_type") and parsed.seller_type:
            update["seller_type"] = parsed.seller_type

        pending_updates.append(update)
        processed += 1

        if len(pending_updates) >= flush_every:
            update_batch(sb, pending_updates)
            log.info("  -> flushed %d updates to Supabase", len(pending_updates))
            pending_updates.clear()

    if pending_updates:
        update_batch(sb, pending_updates)
        log.info("  -> flushed final %d updates to Supabase", len(pending_updates))

    log.info("Done. Processed %d ads.", processed)


if __name__ == "__main__":
    main()
