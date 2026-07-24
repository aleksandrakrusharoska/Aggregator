"""
LLM-based parser for unstructured electronics ad descriptions.
Uses Groq (llama-3.1-8b-instant) via LangChain to extract structured data.
"""
import json
import logging
import os
import re
from typing import Dict, Optional

from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

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


def build_parser():
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0,
    )


def parse_ad(title: str, description: str, parser=None) -> ParsedAdContent:
    if parser is None:
        parser = build_parser()
    try:
        prompt = f"Title: {(title or '').strip()}\n\nDescription:\n{(description or '').strip()}"
        response = parser.invoke([
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": prompt},
        ])
        raw = response.content.strip()
        # Strip markdown code blocks if model wraps output
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        data = json.loads(raw)
        return ParsedAdContent(
            specs={k: str(v) for k, v in (data.get("specs") or {}).items() if v and str(v).strip()},
            condition=data.get("condition") or None,
            seller_notes=data.get("seller_notes") or None,
            phone=data.get("phone") or None,
            delivery_available=bool(data.get("delivery_available", False)),
            seller_type=data.get("seller_type") or None,
        )
    except Exception as exc:
        logger.warning("LLM parse failed for title=%r: %s", title, exc)
        return ParsedAdContent()
