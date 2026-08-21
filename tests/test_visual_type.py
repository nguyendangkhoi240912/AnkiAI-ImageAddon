"""Visual type regression test suite, specifically for 'Luật tactics' and proxy mapping.

Verifies adherence to Master Spec v9 §6, §7, and §8.
"""

import pytest
from AnkiAI_ImageAddon.modules.classification.taxonomy import classify
from AnkiAI_ImageAddon.modules.classification.visual_type import (
    get_visual_type_for_group,
    VISUAL_TYPES,
)


class TestTacticsRuleRegression:
    """Test regression on tactics and related systemic/strategic terms."""

    def test_tactics_classified_as_group_f_diagram(self):
        """'tactics' must be classified as Group F with forced visual_type 'diagram_or_map' (Master Spec §7)."""
        verdict = classify("tactics", sentence="The coach explained his tactics.")
        assert verdict.group == "F"
        assert verdict.visual_type == "diagram_or_map"
        assert "diagram" in verdict.query or "map" in verdict.query

    def test_strategic_systemic_family_regression(self):
        """Systemic concepts (workflow, strategy, supply chain, hierarchy, protocol) must map to diagram_or_map."""
        systemic_words = ["strategy", "workflow", "supply chain", "hierarchy", "protocol", "logistics"]
        for word in systemic_words:
            verdict = classify(word)
            assert verdict.group == "F", f"Expected '{word}' to be Group F, got {verdict.group}"
            assert verdict.visual_type == "diagram_or_map", f"Expected '{word}' visual_type to be diagram_or_map, got {verdict.visual_type}"

    def test_abstract_emotions_map_to_metaphor_photo(self):
        """Pure emotions/values (happiness, freedom, justice, truth) must map to metaphor_photo (Group E)."""
        abstract_emotions = ["happiness", "freedom", "justice", "truth", "honesty", "wisdom"]
        for word in abstract_emotions:
            verdict = classify(word)
            assert verdict.group == "E", f"Expected '{word}' to be Group E, got {verdict.group}"
            assert verdict.visual_type == "metaphor_photo"

    def test_prepositions_map_to_local_svg(self):
        """Prepositions/spatial relations must map to Group K with visual_type local_svg (0 request)."""
        prepositions = ["above", "below", "between", "inside", "across", "behind", "under"]
        for prep in prepositions:
            verdict = classify(prep)
            assert verdict.group == "K", f"Expected '{prep}' to be Group K, got {verdict.group}"
            assert verdict.visual_type == "local_svg"

    def test_function_words_map_to_none(self):
        """Grammar/function words (and, the, however, because) must map to Group M with visual_type none."""
        function_words = ["and", "the", "however", "because", "although", "therefore"]
        for word in function_words:
            verdict = classify(word)
            assert verdict.group == "M", f"Expected '{word}' to be Group M, got {verdict.group}"
            assert verdict.visual_type == "none"

    def test_chemical_formulas_map_to_group_n(self):
        """Chemical formulas/units (H2O, CO2, 37°C, 100km/h) must map to Group N with local_svg."""
        formulas = ["H2O", "CO2", "NaCl", "37°C", "100km/h"]
        for item in formulas:
            verdict = classify(item)
            assert verdict.group == "N", f"Expected '{item}' to be Group N, got {verdict.group}"
            assert verdict.visual_type == "local_svg"
