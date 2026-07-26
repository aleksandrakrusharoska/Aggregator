"""
LLM-based parser for unstructured electronics ad descriptions.
Rotates between Groq (llama-3.1-8b-instant) and Gemini (gemini-2.0-flash)
on each request to share the load across both free-tier daily token limits.
"""
import json
import logging
import os
import re
from itertools import cycle
from typing import Dict, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_SYSTEM = """You extract structured information from second-hand electronics ads.
Ads may be written in Macedonian, Albanian, Serbian, or English.
Return ONLY a valid JSON object — no markdown, no code blocks, no explanation.

CRITICAL RULES:
- ONLY extract information EXPLICITLY written in the description. Do NOT invent or guess.
- specs: key-value pairs of technical specs (RAM, storage, display, battery, processor, etc.) found in the text. Empty object if none mentioned.
- condition: ONLY if explicitly mentioned. One of: "New", "Used - Like New", "Used", "For parts". Never put condition inside specs.
- seller_notes: seller personal comments (warranty, reason for selling, meeting place). null if none.
- phone: first phone number found (Macedonian numbers start with 07, 02, 03). null if none.
- delivery_available: true only if seller explicitly mentions delivery/shipping, otherwise false.
- seller_type: "private" or "business". null if unclear.
- If description is not about an electronics product, return all fields empty.

Return exactly this structure:
{"specs": {}, "condition": null, "seller_notes": null, "phone": null, "delivery_available": false, "seller_type": null}"""


class ParsedAdContent(BaseModel):
    specs: Dict[str, str] = Field(default_factory=dict)
    condition: Optional[str] = None
    seller_notes: Optional[str] = None
    phone: Optional[str] = None
    delivery_available: bool = False
    seller_type: Optional[str] = None


def _build_clients():
    """Build all available LLM clients. Returns a list of (name, client) tuples."""
    clients = []

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        from langchain_groq import ChatGroq
        clients.append(("groq", ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            api_key=groq_key,
            temperature=0,
        )))

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        from langchain_google_genai import ChatGoogleGenerativeAI
        clients.append(("gemini", ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            google_api_key=gemini_key,
            temperature=0,
        )))

    if not clients:
        raise RuntimeError("No LLM API keys found. Set GROQ_API_KEY and/or GEMINI_API_KEY.")

    logger.info("Parser using %d provider(s): %s", len(clients), [n for n, _ in clients])
    return clients


class RotatingParser:
    """Alternates requests between all available LLM providers."""

    def __init__(self):
        self._clients = _build_clients()
        self._cycle = cycle(self._clients)
        self._exhausted: set = set()

    def next(self):
        for _ in range(len(self._clients)):
            name, client = next(self._cycle)
            if name not in self._exhausted:
                return name, client
        raise RuntimeError("All LLM providers exhausted for this run.")

    def mark_exhausted(self, name: str):
        self._exhausted.add(name)
        remaining = [n for n, _ in self._clients if n not in self._exhausted]
        logger.warning("Provider '%s' hit daily limit — removed from rotation. Remaining: %s", name, remaining)


def build_parser() -> RotatingParser:
    return RotatingParser()


def parse_ad(title: str, description: str, parser: RotatingParser = None) -> ParsedAdContent:
    if parser is None:
        parser = build_parser()

    prompt = f"Title: {(title or '').strip()}\n\nDescription:\n{(description or '').strip()}"
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": prompt},
    ]

    for _ in range(len(parser._clients)):
        name, client = parser.next()
        try:
            response = client.invoke(messages)
            raw = response.content.strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            data = json.loads(raw)
            logger.debug("Parsed via %s: %s", name, title[:50])
            return ParsedAdContent(
                specs={k: str(v) for k, v in (data.get("specs") or {}).items() if v and str(v).strip()},
                condition=data.get("condition") or None,
                seller_notes=data.get("seller_notes") or None,
                phone=data.get("phone") or None,
                delivery_available=bool(data.get("delivery_available", False)),
                seller_type=data.get("seller_type") or None,
            )
        except Exception as exc:
            exc_str = str(exc)
            if 'RESOURCE_EXHAUSTED' in exc_str and ('PerDay' in exc_str or 'per_day' in exc_str or 'limit: 0' in exc_str):
                parser.mark_exhausted(name)
            else:
                logger.warning("LLM parse failed (%s) for title=%r: %s — trying next provider", name, title, exc)

    logger.error("All providers exhausted or failed for title=%r", title)
    return ParsedAdContent()
