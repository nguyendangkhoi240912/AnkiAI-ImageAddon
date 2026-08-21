"""
LocalSVGProvider — GĐ3, G3.3                               [MS §6, §17.1]
=========================================================================
Cầu nối giữa taxonomy classifier và svg_engine.
Khi verdict.visual_type == "local_svg", gọi svg_engine.render() và đóng gói
kết quả thành một Candidate với data-URI URL.

Contract: giống BaseProvider nhưng không kế thừa để tránh phụ thuộc requests.

Không import Qt/Anki — module này phải chạy/test được độc lập.
0 request mạng.
"""
from __future__ import annotations

import base64
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

try:
    from .svg_engine import render as _svg_render, supported as _svg_supported
    from .base_provider import Candidate
except ImportError:
    from AnkiAI_ImageAddon.image_providers.svg_engine import (
        render as _svg_render,
        supported as _svg_supported,
    )
    from AnkiAI_ImageAddon.image_providers.base_provider import Candidate


def get_local_svg(word: str, group: str) -> Optional[Candidate]:
    """Return a Candidate with an inline SVG data-URI, or None if unsupported.

    Args:
        word:  Vocabulary word (e.g. "above", "H₂O").
        group: Taxonomy group ("K" or "N").

    Returns:
        Candidate whose url is a data:image/svg+xml;base64,... URI, or None.
    """
    if not _svg_supported(word, group):
        return None

    svg_str = _svg_render(word, group)
    if not svg_str:
        return None

    # Encode as data URI so it can be embedded directly in an <img src="..."> tag
    b64 = base64.b64encode(svg_str.encode("utf-8")).decode("ascii")
    data_uri = f"data:image/svg+xml;base64,{b64}"

    return Candidate(
        url=data_uri,
        provider="local_svg",
        visual_type="local_svg",
        width=400,
        height=300,
        license="public-domain",
        attribution="",
        title=f"{word} ({group})",
        score=1.0,   # local svg is always "best" — no network needed
    )


def search(query: str, visual_type: str, **kwargs) -> List[Candidate]:
    """Minimal BaseProvider-compatible interface.

    Args:
        query:       The word/formula to render.
        visual_type: Expected to be "local_svg"; returns [] otherwise.

    Returns:
        List with one Candidate, or empty list.
    """
    if visual_type != "local_svg":
        return []

    # Determine group from caller context if provided, else infer
    group = kwargs.get("group", "K")
    result = get_local_svg(query, group)
    return [result] if result is not None else []
