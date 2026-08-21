"""Visual type mapping and rules for AnkiAI classification.

Maps groups A-N to appropriate visual_type according to Master Spec v9 §6.
"""

from typing import Dict, Optional

# Valid visual types defined in Master Spec v9 §6
VISUAL_TYPES = {
    "photo",            # Group A, B, C, I (concrete nouns, proper nouns, adjectives)
    "gif",              # Group G (observable action verbs)
    "icon",             # Group H (stative verbs when requested)
    "diagram_or_map",   # Group F, D (systems/strategies/processes, scientific)
    "metaphor_photo",   # Group E, J, L (abstract emotions/values, abstract adjectives, idioms)
    "local_svg",        # Group K, N (prepositions, simple numbers/formulas - 0 request)
    "none",             # Group M (function words - skip completely)
}

# Default visual type by Group (A-N)
GROUP_TO_VISUAL_TYPE: Dict[str, str] = {
    "A": "photo",
    "B": "photo",
    "C": "photo",
    "D": "diagram_or_map",
    "E": "metaphor_photo",
    "F": "diagram_or_map",  # §7: Forced diagram_or_map
    "G": "gif",
    "H": "icon",
    "I": "photo",
    "J": "metaphor_photo",
    "K": "local_svg",       # §6: 0 request local SVG
    "L": "metaphor_photo",
    "M": "none",            # §6: Skip completely
    "N": "local_svg",       # §6: 0 request local SVG / formula
}


def get_visual_type_for_group(group: str, default: str = "photo") -> str:
    """Return the canonical visual_type for a given taxonomy group (A-N).

    Args:
        group: Group identifier (A-N).
        default: Fallback visual type.

    Returns:
        Canonical visual_type string.
    """
    clean_group = group.strip().upper() if group else ""
    return GROUP_TO_VISUAL_TYPE.get(clean_group, default)


def is_zero_request_visual_type(visual_type: str) -> bool:
    """Check if visual_type requires 0 external provider requests (local_svg, none)."""
    return visual_type in ("local_svg", "none")
