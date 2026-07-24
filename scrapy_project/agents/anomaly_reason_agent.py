"""
Anomaly reason agent — uses Groq LLM to explain why a flagged ad has an unusual price.

For each anomaly, sends title + description to the LLM and asks it to explain
why the price might be unusually low or high. Result is stored in anomaly_reason.
"""
import logging
import os
import time

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)

_PROMPT = """An electronics ad on a Macedonian marketplace has been flagged as having an unusually {direction} price.

Title: {title}
Listed price: €{price:.2f}
Description: {description}

In 1-2 sentences, explain why this price might be {direction}. Consider: broken or damaged item, missing accessories, for parts only, starting auction price, bulk listing, data entry error (e.g. missing a zero), or a genuine deal. Be specific to the description above."""


def explain_anomalies(ads: list[dict]) -> list[dict]:
    """
    Call Groq once per ad to generate a brief explanation of the unusual price.
    Expects each ad to have: ad_url, title, price_eur, price_zscore, description.
    Returns list of {ad_url, anomaly_reason}.
    """
    llm = ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_tokens=120,
    )

    results = []
    for i, ad in enumerate(ads):
        title = ad.get("title") or ""
        price = float(ad.get("price_eur") or 0)
        zscore = float(ad.get("price_zscore") or 0)
        description = (ad.get("description") or "No description provided.")[:400]
        direction = "low" if zscore <= 0 else "high"

        logger.info("[%d/%d] %s — €%.2f (z=%.2f)", i + 1, len(ads), title[:50], price, zscore)

        try:
            response = llm.invoke([HumanMessage(content=_PROMPT.format(
                direction=direction,
                title=title,
                price=price,
                description=description,
            ))])
            reason = response.content.strip()
        except Exception as exc:
            logger.error("Groq error for %s: %s", ad["ad_url"], exc)
            reason = None

        results.append({"ad_url": ad["ad_url"], "anomaly_reason": reason})
        time.sleep(4)

    return results
