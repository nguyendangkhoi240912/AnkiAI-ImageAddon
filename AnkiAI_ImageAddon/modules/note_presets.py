"""Per note-type field and mode presets."""

from typing import Any, Dict, Optional

PRESET_KEYS = (
    "vocabulary_field",
    "definition_field",
    "examples_field",
    "image_field",
    "image_generation_mode",
)


def get_preset(config: Dict[str, Any], model_name: str) -> Optional[Dict[str, str]]:
    presets = config.get("note_type_presets") or {}
    raw = presets.get(model_name)
    if not isinstance(raw, dict):
        return None
    return {k: raw.get(k, "") for k in PRESET_KEYS if k in raw or raw.get(k)}


def build_preset(
    vocab: str,
    definition: str,
    examples: str,
    image: str,
    mode: str,
) -> Dict[str, str]:
    return {
        "vocabulary_field": vocab,
        "definition_field": definition,
        "examples_field": examples or "",
        "image_field": image,
        "image_generation_mode": mode or "search",
    }
