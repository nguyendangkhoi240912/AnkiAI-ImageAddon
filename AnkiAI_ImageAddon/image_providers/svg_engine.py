"""
SVG Engine — GĐ3, G3.2                                     [MS §6, §17.1]
=========================================================================
Sinh SVG minh hoạ cho nhóm K (giới từ / quan hệ không gian) và nhóm N
(số / đơn vị / công thức hoá học).

Đặc tính: 0 request mạng, 0 phụ thuộc ngoài stdlib.
Trả về chuỗi SVG hợp lệ (không embed <html>, chỉ thẻ <svg>).

API public:
    render(word: str, group: str) -> str | None
        Trả SVG string hoặc None nếu không có template phù hợp.

    supported(word: str, group: str) -> bool
        Kiểm tra nhanh xem engine có template cho word/group không.

Không import Qt/Anki — module này phải chạy/test được độc lập.
"""
from __future__ import annotations

import html
import re
from typing import Optional

# ---------------------------------------------------------------------------
# SVG viewport và style mặc định
# ---------------------------------------------------------------------------
_W = 400          # viewport width
_H = 300          # viewport height
_BG = "#f8f9fa"   # background
_FG = "#212529"   # foreground text/shape
_ACCENT = "#4361ee"  # accent blue
_ARROW = "#e63946"   # arrow / highlight red

_SVG_OPEN = (
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'viewBox="0 0 {_W} {_H}" width="{_W}" height="{_H}" '
    f'style="font-family:sans-serif;background:{_BG}">'
)
_SVG_CLOSE = "</svg>"


def _svg(inner: str) -> str:
    return _SVG_OPEN + inner + _SVG_CLOSE


# ---------------------------------------------------------------------------
# Primitive helpers
# ---------------------------------------------------------------------------

def _rect(x, y, w, h, fill=_ACCENT, rx=6, opacity=1.0) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'rx="{rx}" fill="{fill}" opacity="{opacity}"/>'
    )


def _circle(cx, cy, r, fill=_ACCENT, opacity=1.0) -> str:
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" '
        f'fill="{fill}" opacity="{opacity}"/>'
    )


def _text(x, y, content, size=16, fill=_FG, anchor="middle", weight="normal") -> str:
    safe = html.escape(str(content))
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{safe}</text>'
    )


def _line(x1, y1, x2, y2, stroke=_FG, width=2) -> str:
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="{width}"/>'
    )


def _arrow_right(x1, y1, x2, y2, color=_ARROW, width=2) -> str:
    """Horizontal/diagonal arrow with arrowhead."""
    # arrowhead points at (x2, y2)
    marker_id = f"arr{abs(hash((x1,y1,x2,y2)))%9999}"
    marker = (
        f'<defs><marker id="{marker_id}" markerWidth="8" markerHeight="6" '
        f'refX="6" refY="3" orient="auto">'
        f'<polygon points="0 0, 8 3, 0 6" fill="{color}"/></marker></defs>'
    )
    line = (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="{width}" '
        f'marker-end="url(#{marker_id})"/>'
    )
    return marker + line


def _label(word: str) -> str:
    """Bottom-centre label showing the word."""
    return _text(_W // 2, _H - 14, word, size=18, fill=_FG, weight="bold")


# ---------------------------------------------------------------------------
# Group K — Spatial preposition templates
# ---------------------------------------------------------------------------
# Each returns the inner SVG content (without <svg> wrapper).

def _k_above(word: str) -> str:
    ref = _rect(150, 160, 100, 60, fill="#adb5bd")          # reference box
    obj = _circle(200, 90, 30, fill=_ACCENT)                # object above
    lbl_ref = _text(200, 198, "reference", size=12, fill=_FG)
    lbl_obj = _text(200, 94, "object", size=12, fill="white")
    arrow = _arrow_right(200, 120, 200, 158, color=_ARROW)  # downward, object→ref gap
    word_lbl = _label(word)
    return ref + obj + lbl_ref + lbl_obj + arrow + word_lbl


def _k_below(word: str) -> str:
    ref = _rect(150, 80, 100, 60, fill="#adb5bd")
    obj = _circle(200, 220, 30, fill=_ACCENT)
    lbl_ref = _text(200, 118, "reference", size=12, fill=_FG)
    lbl_obj = _text(200, 224, "object", size=12, fill="white")
    arrow = _arrow_right(200, 190, 200, 152, color=_ARROW)
    word_lbl = _label(word)
    return ref + obj + lbl_ref + lbl_obj + arrow + word_lbl


def _k_beside(word: str) -> str:
    ref = _rect(220, 110, 100, 70, fill="#adb5bd")
    obj = _rect(80, 110, 100, 70, fill=_ACCENT)
    lbl_ref = _text(270, 148, "reference", size=12, fill=_FG)
    lbl_obj = _text(130, 148, "object", size=12, fill="white")
    word_lbl = _label(word)
    return ref + obj + lbl_ref + lbl_obj + word_lbl


def _k_between(word: str) -> str:
    box_a = _rect(30, 110, 90, 70, fill="#adb5bd")
    box_b = _rect(280, 110, 90, 70, fill="#adb5bd")
    obj = _circle(200, 145, 30, fill=_ACCENT)
    lbl_a = _text(75, 148, "A", size=14, fill=_FG)
    lbl_b = _text(325, 148, "B", size=14, fill=_FG)
    lbl_obj = _text(200, 149, "object", size=11, fill="white")
    # dashed lines from obj to each box
    dash = 'stroke-dasharray="6,4"'
    gap_l = f'<line x1="170" y1="145" x2="120" y2="145" stroke="{_ARROW}" stroke-width="2" {dash}/>'
    gap_r = f'<line x1="230" y1="145" x2="280" y2="145" stroke="{_ARROW}" stroke-width="2" {dash}/>'
    word_lbl = _label(word)
    return box_a + box_b + obj + lbl_a + lbl_b + lbl_obj + gap_l + gap_r + word_lbl


def _k_inside(word: str) -> str:
    outer = _rect(80, 80, 240, 140, fill="none", rx=10,
                  opacity=1.0)
    outer_stroke = f'<rect x="80" y="80" width="240" height="140" rx="10" fill="none" stroke="{_ACCENT}" stroke-width="3"/>'
    obj = _circle(200, 150, 28, fill=_ACCENT)
    lbl = _text(200, 154, "object", size=12, fill="white")
    word_lbl = _label(word)
    return outer_stroke + obj + lbl + word_lbl


def _k_outside(word: str) -> str:
    inner = f'<rect x="120" y="90" width="160" height="110" rx="10" fill="none" stroke="{_ACCENT}" stroke-width="3"/>'
    obj = _circle(60, 100, 28, fill=_ACCENT)
    lbl_obj = _text(60, 104, "object", size=11, fill="white")
    lbl_box = _text(200, 148, "container", size=12, fill=_FG)
    word_lbl = _label(word)
    return inner + obj + lbl_obj + lbl_box + word_lbl


def _k_in_front_of(word: str) -> str:
    # Side view: reference (building) at back, object (person) in front
    ref = _rect(130, 80, 140, 140, fill="#adb5bd", rx=4)
    lbl_ref = _text(200, 148, "reference", size=12, fill=_FG)
    obj = _circle(200, 230, 25, fill=_ACCENT)
    lbl_obj = _text(200, 233, "obj", size=11, fill="white")
    word_lbl = _label(word)
    return ref + lbl_ref + obj + lbl_obj + word_lbl


def _k_behind(word: str) -> str:
    # Object peeking behind reference
    ref = _rect(130, 90, 140, 130, fill="#adb5bd", rx=4)
    lbl_ref = _text(200, 158, "reference", size=12, fill=_FG)
    obj_partial = f'<rect x="174" y="60" width="52" height="50" rx="26" fill="{_ACCENT}"/>'
    lbl_obj = _text(200, 89, "object", size=11, fill="white")
    word_lbl = _label(word)
    return obj_partial + ref + lbl_ref + lbl_obj + word_lbl


def _k_over(word: str) -> str:
    # Arc over reference
    ref = _rect(100, 150, 200, 60, fill="#adb5bd")
    arc = f'<path d="M 80 150 Q 200 60 320 150" stroke="{_ACCENT}" stroke-width="4" fill="none"/>'
    lbl_ref = _text(200, 187, "reference", size=12, fill=_FG)
    word_lbl = _label(word)
    return ref + arc + lbl_ref + word_lbl


def _k_under(word: str) -> str:
    ref = _rect(100, 80, 200, 60, fill="#adb5bd")
    obj = _rect(150, 170, 100, 50, fill=_ACCENT, rx=4)
    lbl_ref = _text(200, 118, "reference", size=12, fill=_FG)
    lbl_obj = _text(200, 200, "object", size=12, fill="white")
    word_lbl = _label(word)
    return ref + obj + lbl_ref + lbl_obj + word_lbl


def _k_near(word: str) -> str:
    ref = _rect(210, 110, 120, 70, fill="#adb5bd")
    obj = _circle(130, 145, 30, fill=_ACCENT)
    lbl_ref = _text(270, 148, "reference", size=12, fill=_FG)
    lbl_obj = _text(130, 149, "object", size=11, fill="white")
    # distance marker
    dist = f'<line x1="162" y1="145" x2="210" y2="145" stroke="{_ARROW}" stroke-width="2" stroke-dasharray="5,4"/>'
    d_lbl = _text(186, 136, "near", size=10, fill=_ARROW)
    word_lbl = _label(word)
    return ref + obj + lbl_ref + lbl_obj + dist + d_lbl + word_lbl


def _k_across(word: str) -> str:
    # Object crossing a line/river
    river = _rect(0, 120, _W, 60, fill="#90e0ef", rx=0)
    obj = _circle(200, 150, 22, fill=_ACCENT)
    arrow_l = _arrow_right(50, 150, 170, 150, color=_ARROW)
    arrow_r = _arrow_right(230, 150, 350, 150, color=_ARROW)
    lbl = _text(200, 244, "crossing", size=12, fill=_FG)
    word_lbl = _label(word)
    return river + obj + arrow_l + arrow_r + lbl + word_lbl


def _k_through(word: str) -> str:
    # Tunnel / passage
    tunnel = _rect(80, 100, 240, 90, fill="#adb5bd", rx=8)
    obj = _circle(200, 145, 22, fill=_ACCENT)
    arrow = _arrow_right(50, 145, 350, 145, color=_ARROW, width=3)
    word_lbl = _label(word)
    return tunnel + obj + arrow + word_lbl


def _k_on_top_of(word: str) -> str:
    base = _rect(100, 160, 200, 60, fill="#adb5bd")
    obj = _rect(150, 110, 100, 50, fill=_ACCENT, rx=4)
    lbl_base = _text(200, 197, "reference", size=12, fill=_FG)
    lbl_obj = _text(200, 139, "object", size=12, fill="white")
    word_lbl = _label(word)
    return base + obj + lbl_base + lbl_obj + word_lbl


def _k_next_to(word: str) -> str:
    return _k_beside(word)   # same visual concept


def _k_among(word: str) -> str:
    # Object surrounded by several others
    dots = [
        (120, 100), (280, 100), (80, 180), (320, 180), (200, 220),
    ]
    surround = "".join(_circle(x, y, 18, fill="#adb5bd") for x, y in dots)
    obj = _circle(200, 145, 28, fill=_ACCENT)
    lbl = _text(200, 149, "object", size=11, fill="white")
    word_lbl = _label(word)
    return surround + obj + lbl + word_lbl


def _k_around(word: str) -> str:
    outer_ring = f'<circle cx="200" cy="140" r="80" fill="none" stroke="{_ACCENT}" stroke-width="3" stroke-dasharray="10,6"/>'
    obj = _circle(200, 140, 28, fill="#adb5bd")
    lbl = _text(200, 144, "reference", size=11, fill=_FG)
    arrows = "".join([
        _arrow_right(200, 60, 278, 107, color=_ARROW),
        _arrow_right(278, 173, 200, 220, color=_ARROW),
        _arrow_right(122, 173, 122, 107, color=_ARROW),
    ])
    word_lbl = _label(word)
    return obj + outer_ring + arrows + lbl + word_lbl


def _k_up(word: str) -> str:
    arrow = _arrow_right(200, 240, 200, 60, color=_ACCENT, width=4)
    obj = _circle(200, 240, 22, fill="#adb5bd")
    lbl = _text(200, 244, "start", size=11, fill=_FG)
    word_lbl = _label(word)
    return obj + arrow + lbl + word_lbl


def _k_down(word: str) -> str:
    arrow = _arrow_right(200, 60, 200, 240, color=_ACCENT, width=4)
    obj = _circle(200, 60, 22, fill="#adb5bd")
    lbl = _text(200, 64, "start", size=11, fill=_FG)
    word_lbl = _label(word)
    return obj + arrow + lbl + word_lbl


def _k_towards(word: str) -> str:
    target = _circle(320, 150, 28, fill="#adb5bd")
    obj = _circle(80, 150, 22, fill=_ACCENT)
    arrow = _arrow_right(104, 150, 290, 150, color=_ARROW, width=3)
    lbl_target = _text(320, 154, "target", size=11, fill=_FG)
    lbl_obj = _text(80, 154, "obj", size=11, fill="white")
    word_lbl = _label(word)
    return target + obj + arrow + lbl_target + lbl_obj + word_lbl


def _k_away_from(word: str) -> str:
    target = _circle(80, 150, 28, fill="#adb5bd")
    obj = _circle(310, 150, 22, fill=_ACCENT)
    arrow = _arrow_right(110, 150, 286, 150, color=_ARROW, width=3)
    lbl_target = _text(80, 154, "origin", size=11, fill=_FG)
    lbl_obj = _text(310, 154, "obj", size=11, fill="white")
    word_lbl = _label(word)
    return target + obj + arrow + lbl_target + lbl_obj + word_lbl


def _k_generic(word: str) -> str:
    """Fallback: show word with a simple position indicator."""
    ref = _rect(130, 100, 140, 90, fill="#adb5bd")
    obj = _circle(200, 75, 22, fill=_ACCENT)
    lbl_ref = _text(200, 148, "reference", size=12, fill=_FG)
    word_lbl = _label(word)
    return ref + obj + lbl_ref + word_lbl


# ---------------------------------------------------------------------------
# Group N — Formula / unit templates
# ---------------------------------------------------------------------------

def _n_chemical(formula: str) -> str:
    """Simple chemical formula display with coloured element blocks."""
    # Parse element tokens: letter(s) + optional subscript digit
    tokens = re.findall(r"([A-Z][a-z]?)([0-9₀-₉]*)", formula)
    palette = [_ACCENT, "#e63946", "#2dc653", "#ff9f1c", "#9b5de5",
               "#00bbf9", "#fee440", "#00f5d4"]
    block_w, block_h = 54, 54
    n_tokens = max(len(tokens), 1)
    total_w = n_tokens * (block_w + 10) - 10
    start_x = (_W - total_w) // 2
    inner = ""
    for i, (sym, sub) in enumerate(tokens):
        bx = start_x + i * (block_w + 10)
        by = (_H - block_h) // 2 - 20
        color = palette[i % len(palette)]
        inner += _rect(bx, by, block_w, block_h, fill=color, rx=8)
        inner += _text(bx + block_w // 2, by + 34, sym, size=22, fill="white", weight="bold")
        if sub:
            # Convert unicode subscript digits to normal
            normal_sub = sub.translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
            inner += _text(bx + block_w // 2 + 14, by + 46, normal_sub, size=13, fill="white")
    inner += _text(_W // 2, _H - 18, formula, size=16, fill=_FG, weight="bold")
    return inner


def _n_measurement(value: str) -> str:
    """Number + unit on a simple gauge/ruler visual."""
    # Split into numeric and unit parts
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(.+)$", value.strip())
    num = m.group(1) if m else value
    unit = m.group(2) if m else ""

    # Draw thermometer-style bar for temperature; ruler for others
    if "°" in unit:
        # Vertical thermometer
        bar_x, bar_top, bar_h = 190, 50, 180
        inner = f'<rect x="{bar_x}" y="{bar_top}" width="20" height="{bar_h}" rx="10" fill="#dee2e6"/>'
        fill_h = min(bar_h, int(bar_h * 0.6))
        inner += f'<rect x="{bar_x}" y="{bar_top + bar_h - fill_h}" width="20" height="{fill_h}" rx="10" fill="{_ARROW}"/>'
        inner += _circle(200, bar_top + bar_h + 12, 18, fill=_ARROW)
        inner += _text(200, bar_top + bar_h + 17, num, size=13, fill="white")
        inner += _text(240, bar_top + bar_h - fill_h + 10, unit, size=14, fill=_FG)
        inner += _text(_W // 2, _H - 18, value, size=16, fill=_FG, weight="bold")
    else:
        # Horizontal ruler
        ruler_x, ruler_y, ruler_w = 50, 130, 300
        inner = f'<rect x="{ruler_x}" y="{ruler_y}" width="{ruler_w}" height="20" rx="4" fill="#dee2e6"/>'
        fill_w = int(ruler_w * 0.65)
        inner += f'<rect x="{ruler_x}" y="{ruler_y}" width="{fill_w}" height="20" rx="4" fill="{_ACCENT}"/>'
        # Tick marks
        for tick in range(0, ruler_w + 1, ruler_w // 5):
            inner += _line(ruler_x + tick, ruler_y, ruler_x + tick, ruler_y + 20, stroke="#868e96")
        inner += _text(_W // 2, ruler_y - 14, num, size=22, fill=_FG, weight="bold")
        inner += _text(_W // 2, ruler_y + 50, unit, size=18, fill=_ACCENT, weight="bold")
        inner += _text(_W // 2, _H - 18, value, size=15, fill=_FG, weight="bold")
    return inner


def _n_math(expr: str) -> str:
    """Display a mathematical expression in a clean centred box."""
    inner = _rect(60, 90, 280, 100, fill="white", rx=12)
    inner += f'<rect x="60" y="90" width="280" height="100" rx="12" fill="none" stroke="{_ACCENT}" stroke-width="2"/>'
    inner += _text(_W // 2, 152, expr, size=28, fill=_FG, weight="bold")
    inner += _text(_W // 2, _H - 18, "expression", size=14, fill="#6c757d")
    return inner


def _n_generic(expr: str) -> str:
    inner = _rect(80, 100, 240, 90, fill="white", rx=8)
    inner += f'<rect x="80" y="100" width="240" height="90" rx="8" fill="none" stroke="{_ACCENT}" stroke-width="2"/>'
    inner += _text(_W // 2, 153, expr, size=26, fill=_FG, weight="bold")
    inner += _text(_W // 2, _H - 18, "formula / unit", size=13, fill="#6c757d")
    return inner


# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

# Map normalised word → render function for group K
_K_TEMPLATES: dict[str, object] = {
    "above": _k_above,
    "below": _k_below,
    "under": _k_under,
    "underneath": _k_under,
    "beneath": _k_under,
    "over": _k_over,
    "atop": _k_on_top_of,
    "on top of": _k_on_top_of,
    "between": _k_between,
    "in between": _k_between,
    "among": _k_among,
    "amid": _k_among,
    "amidst": _k_among,
    "behind": _k_behind,
    "inside": _k_inside,
    "within": _k_inside,
    "outside": _k_outside,
    "beside": _k_beside,
    "next to": _k_next_to,
    "alongside": _k_beside,
    "adjacent to": _k_beside,
    "near": _k_near,
    "close to": _k_near,
    "across": _k_across,
    "through": _k_through,
    "into": _k_towards,
    "onto": _k_on_top_of,
    "towards": _k_towards,
    "toward": _k_towards,
    "away from": _k_away_from,
    "up": _k_up,
    "down": _k_down,
    "around": _k_around,
    "against": _k_beside,
    "upon": _k_on_top_of,
    "in front of": _k_in_front_of,
    "ahead of": _k_in_front_of,
    "at the back of": _k_behind,
    "opposite": _k_between,
    "aboard": _k_inside,
    "out of": _k_away_from,
    "to the left of": _k_beside,
    "to the right of": _k_beside,
    "in the middle of": _k_among,
}

# Regex patterns to classify Group N sub-types
_CHEM_RE = re.compile(r"^(?:[A-Z][a-z]?[\d₀-₉]*)+(?:[+–-]\d*|\d*[+–-])?$")
_MEAS_RE = re.compile(
    r"^\d+(?:\.\d+)?\s*(?:°C|°F|K|kg|g|mg|µg|km|m|cm|mm|nm|µm|s|ms|min|h|hr|"
    r"Hz|kHz|MHz|GHz|V|kV|mV|A|mA|µA|W|kW|MW|J|kJ|cal|kcal|Pa|kPa|MPa|"
    r"atm|bar|psi|L|mL|µL|mol|mmol|rpm|dB|%|ppm|mph|km/h|m/s)$",
    re.IGNORECASE,
)
_MATH_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?|\bpi\b|\be\b|\bphi\b|[0-9]+/[0-9]+|√\d+|\d+[²³⁴⁵]|"
    r"[\d\.]+\s*[\+\-\*\/]\s*[\d\.]+)$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render(word: str, group: str) -> Optional[str]:
    """Return an SVG string for the given word and group, or None if unsupported.

    Args:
        word:  The vocabulary word (e.g. "above", "H₂O", "37°C").
        group: Taxonomy group letter ("K" or "N").

    Returns:
        SVG string (UTF-8, no XML declaration) or None.
    """
    word_clean = word.strip()
    word_lower = word_clean.lower()

    if group == "K":
        fn = _K_TEMPLATES.get(word_lower)
        if fn is None:
            # Fallback to generic spatial template rather than returning None
            fn = _k_generic
        return _svg(fn(word_clean))

    if group == "N":
        inner = _render_group_n(word_clean)
        return _svg(inner)

    return None


def supported(word: str, group: str) -> bool:
    """Return True if render() will produce a result (not None) for this word/group."""
    if group == "K":
        return True   # always has generic fallback
    if group == "N":
        return True   # always has generic fallback
    return False


def _render_group_n(expr: str) -> str:
    """Choose the best sub-template for a Group N expression."""
    if _CHEM_RE.match(expr) and any(c.isupper() for c in expr):
        return _n_chemical(expr)
    if _MEAS_RE.match(expr):
        return _n_measurement(expr)
    if _MATH_RE.match(expr):
        return _n_math(expr)
    return _n_generic(expr)
