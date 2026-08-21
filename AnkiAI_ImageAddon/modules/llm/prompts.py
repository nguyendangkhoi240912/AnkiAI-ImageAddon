"""
Prompt Templates — GĐ4, G4.3                               [MS §23]
=========================================================================
P1 — Workhorse batch (nhóm B/D/H, kèm dịch nội bộ sang EN)
P2 — Hard model lô nhỏ (nhóm E/F/J/L, bảng proxy + few-shot)
P3 — Vision QC đồng bộ (chạy theo lô ảnh trong Browser mode)

Không import Qt/Anki. Không gọi network từ module này.
"""
from __future__ import annotations

from typing import List

# ---------------------------------------------------------------------------
# P1 — Workhorse: batch classify + generate search query
# ---------------------------------------------------------------------------

P1_SYSTEM = (
    "You are a vocabulary image search expert. "
    "Respond with a JSON array ONLY — no explanation, no markdown."
)

P1_USER_TEMPLATE = """\
For EACH item in the list below, do ALL of:
1. If lang≠en, translate the word internally and store as en_query.
2. Pick the sense that matches the sentence context.
3. Output a SHORT concrete English search query (noun phrase, no definitions) as q.
4. Output one alternative query as alt.
5. Output confidence 0.0–1.0 as c.

Return JSON array ONLY:
[{{"w":<word>,"en_query":<en_query>,"q":<query>,"alt":<alt>,"c":<confidence>}}]

Items:
{items_json}
"""

def build_p1_user(items: List[dict]) -> str:
    """Build P1 user message from a list of {word, sentence, pos, lang} dicts."""
    import json
    return P1_USER_TEMPLATE.format(items_json=json.dumps(items, ensure_ascii=False))


# ---------------------------------------------------------------------------
# P2 — Hard model: abstract / idiomatic words
# ---------------------------------------------------------------------------

P2_SYSTEM = (
    "You create VISUAL PROXIES for abstract/idiomatic words "
    "for language-learning flashcards. "
    "Respond with a JSON array ONLY — no explanation, no markdown."
)

# Proxy family reference injected into the prompt (from §8)
_PROXY_FAMILY_HINT = (
    "PROXY FAMILY reference: "
    "STRATEGY→military map with attack arrows/chess board; "
    "WORKFLOW→flowchart; "
    "NEGOTIATION→negotiation table top-down view; "
    "TIME→hourglass; "
    "CHANGE→caterpillar-to-butterfly; "
    "CAUSE→dominoes; "
    "RISK→dice/tightrope; "
    "LAW→scales; "
    "FREEDOM→broken chains; "
    "KNOWLEDGE→lightbulb; "
    "MONEY→coin stack/chart; "
    "TEAMWORK→joined hands; "
    "DANGER→warning triangle; "
    "BALANCE→seesaw."
)

P2_USER_TEMPLATE = """\
{proxy_hint}

RULE: for STRATEGY-family words, NEVER output a generic person photo.
FEW-SHOT: "tactics" → NOT "coach shouting at players" → YES "military map with attack arrows".
For idioms: default to figurative meaning; use literal ONLY if literal_ok=true
(memorable AND not misleading — e.g. "break the ice": literal ice breaking still conveys the idiom well).

For EACH item, output visual proxy:
Return JSON array ONLY:
[{{"w":<word>,"type":"diagram_or_map"|"metaphor_photo"|"icon"|"gif","q":<query>,"alt":<alt>,"literal_ok":<bool>,"c":<confidence>}}]

Items:
{items_json}
"""

def build_p2_user(items: List[dict]) -> str:
    """Build P2 user message from a list of {word, sentence, group} dicts."""
    import json
    return P2_USER_TEMPLATE.format(
        proxy_hint=_PROXY_FAMILY_HINT,
        items_json=json.dumps(items, ensure_ascii=False),
    )


# ---------------------------------------------------------------------------
# P3 — Vision QC: synchronous image verification
# ---------------------------------------------------------------------------

P3_SYSTEM = (
    "You are an image quality reviewer for vocabulary flashcards. "
    "Respond with a JSON array ONLY — no explanation, no markdown."
)

P3_USER_TEMPLATE = """\
Review each image for vocabulary flashcard suitability.

Rules:
- For group F (diagram_or_map): ok=false if the image only shows a generic related
  activity (e.g. a coach talking) WITHOUT showing the actual structure/system/
  relationship the word describes.
- For all other groups: ok=true ONLY if a learner seeing this image would recall
  the CORRECT sense of the word (not just a loosely related scene).

Each pair: {{"i":<index>, "word":<word>, "sense":<sense_id_or_meaning>, "group":<group>, "image_url":<url>}}

Return JSON array ONLY:
[{{"i":<index>,"ok":<bool>,"r":<short_reason_under_10_words>}}]

Pairs:
{pairs_json}
"""

def build_p3_user(pairs: List[dict]) -> str:
    """Build P3 user message from a list of {i, word, sense, group, image_url} dicts."""
    import json
    return P3_USER_TEMPLATE.format(pairs_json=json.dumps(pairs, ensure_ascii=False))


# ---------------------------------------------------------------------------
# Response parsing helpers
# ---------------------------------------------------------------------------

import json as _json
import re as _re


def _extract_json_array(text: str) -> list:
    """Extract first JSON array from model response (handles markdown fences)."""
    # Strip markdown code fences
    text = _re.sub(r"```(?:json)?\s*", "", text).strip()
    # Find first '[' to last ']'
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array found in response: {text[:200]!r}")
    return _json.loads(text[start : end + 1])


def parse_p1_response(text: str) -> list:
    """Parse P1 model response into list of verdict dicts.
    Returns [] on parse failure (caller should retry or fallback).
    """
    try:
        items = _extract_json_array(text)
        required = {"w", "en_query", "q", "alt", "c"}
        return [it for it in items if required.issubset(it.keys())]
    except Exception:
        return []


def parse_p2_response(text: str) -> list:
    """Parse P2 model response."""
    try:
        items = _extract_json_array(text)
        required = {"w", "type", "q", "alt", "c"}
        return [it for it in items if required.issubset(it.keys())]
    except Exception:
        return []


def parse_p3_response(text: str) -> list:
    """Parse P3 vision QC response."""
    try:
        items = _extract_json_array(text)
        return [it for it in items if {"i", "ok", "r"}.issubset(it.keys())]
    except Exception:
        return []
