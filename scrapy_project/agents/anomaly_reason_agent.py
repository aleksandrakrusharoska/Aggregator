"""
Anomaly reason agent — uses LLM to explain why a flagged ad has an unusual price.

For each anomaly, sends title + description to the LLM and asks it to explain
why the price might be unusually low or high. Result is stored in anomaly_reason.
Rotates between Groq and Gemini providers; skips exhausted providers automatically.
"""
import logging
import time

from agents.parser_agent import build_parser

logger = logging.getLogger(__name__)

_PROMPT = """An electronics ad on a Macedonian marketplace has been flagged as having an unusually {direction} price.

Title: {title}
Listed price: €{price:.2f}
Description: {description}

In 1-2 sentences, explain why this price might be {direction}. Consider: broken or damaged item, missing accessories, for parts only, starting auction price, bulk listing, data entry error (e.g. missing a zero), or a genuine deal. Be specific to the description above."""


def explain_anomalies(ads: list[dict]) -> list[dict]:
    """
    Call LLM once per ad to generate a brief explanation of the unusual price.
    Expects each ad to have: ad_url, title, price_eur, price_zscore, description.
    Returns list of {ad_url, anomaly_reason}.
    """
    parser = build_parser()
    results = []

    for i, ad in enumerate(ads):
        title = ad.get("title") or ""
        price = float(ad.get("price_eur") or 0)
        zscore = float(ad.get("price_zscore") or 0)
        description = (ad.get("description") or "No description provided.")[:400]
        direction = "low" if zscore <= 0 else "high"

        logger.info("[%d/%d] %s — €%.2f (z=%.2f)", i + 1, len(ads), title[:50], price, zscore)

        prompt = _PROMPT.format(direction=direction, title=title, price=price, description=description)
        reason = None

        for _ in range(len(parser._clients)):
            name, client = parser.next()
            try:
                from langchain_core.messages import HumanMessage
                response = client.invoke([HumanMessage(content=prompt)])
                reason = response.content.strip()
                break
            except Exception as exc:
                exc_str = str(exc)
                if 'RESOURCE_EXHAUSTED' in exc_str and ('PerDay' in exc_str or 'per_day' in exc_str or 'limit: 0' in exc_str):
                    parser.mark_exhausted(name)
                else:
                    logger.error("LLM error (%s) for %s: %s — trying next provider", name, ad["ad_url"], exc)

        if reason is None:
            logger.error("All providers failed for %s", ad["ad_url"])

        results.append({"ad_url": ad["ad_url"], "anomaly_reason": reason})
        time.sleep(4)

    return results
