"""
Tests for image_providers/svg_engine.py và local_svg_provider.py — GĐ3, G3.2 G3.3
Gate: K/N trả ảnh 0 request (local_svg, provider="local_svg")
Chạy độc lập, không cần Anki/Qt.
"""
import sys
import os
import re
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AnkiAI_ImageAddon.image_providers.svg_engine import render, supported, _render_group_n
from AnkiAI_ImageAddon.image_providers.local_svg_provider import get_local_svg, search


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_valid_svg(svg_str: str) -> bool:
    """Parse SVG as XML; return True if well-formed."""
    try:
        ET.fromstring(svg_str)
        return True
    except ET.ParseError:
        return False


# ---------------------------------------------------------------------------
# svg_engine.render — Group K (spatial prepositions)
# ---------------------------------------------------------------------------

class TestGroupKPrepositions:
    """Render 3 prepositions with explicit templates + generic fallback."""

    @pytest.mark.parametrize("word", ["above", "below", "beside"])
    def test_explicit_template_produces_valid_svg(self, word):
        svg = render(word, "K")
        assert svg is not None
        assert is_valid_svg(svg), f"SVG for '{word}' is not valid XML:\n{svg[:200]}"

    def test_between_valid_svg(self):
        svg = render("between", "K")
        assert svg is not None
        assert is_valid_svg(svg)

    def test_inside_valid_svg(self):
        svg = render("inside", "K")
        assert is_valid_svg(render("inside", "K"))

    def test_through_valid_svg(self):
        assert is_valid_svg(render("through", "K"))

    def test_towards_valid_svg(self):
        assert is_valid_svg(render("towards", "K"))

    def test_above_contains_word_label(self):
        svg = render("above", "K")
        assert "above" in svg.lower()

    def test_multi_word_preposition(self):
        """'in front of' is a multi-word preposition — should produce SVG."""
        svg = render("in front of", "K")
        assert svg is not None
        assert is_valid_svg(svg)

    def test_unknown_preposition_falls_back_to_generic(self):
        """Unknown word still gets a generic SVG, not None."""
        svg = render("nonexistent_prep_xyz", "K")
        assert svg is not None
        assert is_valid_svg(svg)

    def test_svg_has_correct_dimensions(self):
        svg = render("above", "K")
        assert 'width="400"' in svg
        assert 'height="300"' in svg

    def test_svg_starts_with_svg_tag(self):
        svg = render("above", "K")
        assert svg.strip().startswith("<svg")

    def test_supported_returns_true_for_k(self):
        assert supported("above", "K") is True
        assert supported("unknown_word", "K") is True


# ---------------------------------------------------------------------------
# svg_engine.render — Group N (formulas / units)
# ---------------------------------------------------------------------------

class TestGroupNFormulas:
    @pytest.mark.parametrize("formula", ["H2O", "CO2", "NaCl", "C6H12O6"])
    def test_chemical_formula_valid_svg(self, formula):
        svg = render(formula, "N")
        assert svg is not None
        assert is_valid_svg(svg), f"SVG for '{formula}' invalid:\n{svg[:200]}"

    def test_chemical_formula_contains_element_symbols(self):
        svg = render("H2O", "N")
        assert "H" in svg and "O" in svg

    def test_measurement_unit_valid_svg(self):
        svg = render("37°C", "N")
        assert svg is not None
        assert is_valid_svg(svg)

    def test_measurement_unit_contains_value(self):
        svg = render("37°C", "N")
        assert "37" in svg

    def test_math_expression_valid_svg(self):
        svg = render("3.14", "N")
        assert svg is not None
        assert is_valid_svg(svg)

    def test_generic_n_fallback(self):
        """Unrecognised N expression still gets a box display."""
        svg = render("x²+y²=z²", "N")
        assert svg is not None
        assert is_valid_svg(svg)

    def test_supported_returns_true_for_n(self):
        assert supported("H2O", "N") is True

    def test_n_svg_has_correct_dimensions(self):
        svg = render("CO2", "N")
        assert 'width="400"' in svg
        assert 'height="300"' in svg


# ---------------------------------------------------------------------------
# svg_engine.render — unsupported group
# ---------------------------------------------------------------------------

class TestUnsupportedGroup:
    def test_returns_none_for_group_a(self):
        assert render("apple", "A") is None

    def test_returns_none_for_group_m(self):
        assert render("the", "M") is None

    def test_supported_false_for_other_groups(self):
        for g in ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "L", "M"):
            assert supported("test", g) is False


# ---------------------------------------------------------------------------
# local_svg_provider — gate test: 0 network, provider="local_svg"
# ---------------------------------------------------------------------------

class TestLocalSVGProvider:
    @pytest.mark.parametrize("word,group", [
        ("above", "K"),
        ("between", "K"),
        ("in front of", "K"),
        ("H2O", "N"),
        ("37°C", "N"),
    ])
    def test_get_local_svg_returns_candidate(self, word, group):
        cand = get_local_svg(word, group)
        assert cand is not None, f"get_local_svg('{word}', '{group}') returned None"

    def test_provider_is_local_svg(self):
        cand = get_local_svg("above", "K")
        assert cand.provider == "local_svg"

    def test_visual_type_is_local_svg(self):
        cand = get_local_svg("above", "K")
        assert cand.visual_type == "local_svg"

    def test_url_is_data_uri(self):
        cand = get_local_svg("above", "K")
        assert cand.url.startswith("data:image/svg+xml;base64,")

    def test_data_uri_decodes_to_valid_svg(self):
        import base64
        cand = get_local_svg("H2O", "N")
        b64 = cand.url.split(",", 1)[1]
        svg_bytes = base64.b64decode(b64)
        svg_str = svg_bytes.decode("utf-8")
        assert is_valid_svg(svg_str)

    def test_score_is_one(self):
        """local_svg candidate always gets score=1.0 — no competition needed."""
        cand = get_local_svg("below", "K")
        assert cand.score == 1.0

    def test_license_is_public_domain(self):
        cand = get_local_svg("above", "K")
        assert cand.license == "public-domain"

    def test_returns_none_for_unsupported_group(self):
        cand = get_local_svg("apple", "A")
        assert cand is None

    def test_search_interface_local_svg(self):
        results = search("above", "local_svg", group="K")
        assert len(results) == 1
        assert results[0].provider == "local_svg"

    def test_search_interface_wrong_visual_type_returns_empty(self):
        results = search("above", "photo")
        assert results == []

    def test_zero_network_requests(self):
        """Gate test: rendering should work without any network call.
        We verify this by monkeypatching requests to raise if called."""
        import unittest.mock as mock
        with mock.patch("requests.get", side_effect=RuntimeError("Network called!")):
            cand = get_local_svg("above", "K")
        assert cand is not None  # no network = no exception


# ---------------------------------------------------------------------------
# Integration: taxonomy → local_svg_provider (G3.3 pipeline gate)
# ---------------------------------------------------------------------------

class TestPipelineKNIntegration:
    """Verify end-to-end: classify word → if local_svg → get_local_svg returns Candidate."""

    @pytest.mark.parametrize("word,expected_group", [
        ("above", "K"),
        ("below", "K"),
        ("between", "K"),
    ])
    def test_taxonomy_routes_to_local_svg_group_k(self, word, expected_group):
        from AnkiAI_ImageAddon.modules.classification.taxonomy import classify
        verdict = classify(word)
        assert verdict.group == expected_group
        assert verdict.visual_type == "local_svg"
        # Pipeline: get candidate
        cand = get_local_svg(verdict.word, verdict.group)
        assert cand is not None
        assert cand.provider == "local_svg"

    def test_taxonomy_routes_to_local_svg_group_n(self):
        from AnkiAI_ImageAddon.modules.classification.taxonomy import classify
        verdict = classify("H2O")
        assert verdict.group == "N"
        assert verdict.visual_type == "local_svg"
        cand = get_local_svg(verdict.word, verdict.group)
        assert cand is not None
        assert cand.url.startswith("data:image/svg+xml")

    def test_no_network_for_group_k(self):
        import unittest.mock as mock
        from AnkiAI_ImageAddon.modules.classification.taxonomy import classify
        with mock.patch("requests.get", side_effect=RuntimeError("Network called!")):
            verdict = classify("above")
            cand = get_local_svg(verdict.word, verdict.group)
        assert cand is not None
