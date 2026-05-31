"""Tests for note-type presets."""

from AnkiAI_ImageAddon.modules.note_presets import build_preset, get_preset


def test_build_and_get_preset():
    cfg = {
        "note_type_presets": {
            "Basic": build_preset("Front", "Back", "", "Image", "search"),
        }
    }
    p = get_preset(cfg, "Basic")
    assert p["vocabulary_field"] == "Front"
    assert p["image_generation_mode"] == "search"
    assert get_preset(cfg, "Missing") is None
