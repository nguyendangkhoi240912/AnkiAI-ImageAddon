"""Taxonomy classification accuracy evaluation against eval_set_v1.json.

Ensures classification group accuracy meets or exceeds the 0.90 threshold (Master Spec §20).
"""

import json
from pathlib import Path
import pytest

from AnkiAI_ImageAddon.modules.classification.taxonomy import classify

EVAL_SET_PATH = (
    Path(__file__).parent.parent
    / "AnkiAI_ImageAddon"
    / "user_files"
    / "eval_set"
    / "eval_set_v1.json"
)


def load_eval_set():
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_eval_set_group_accuracy():
    """Verify that taxonomy classification accuracy on eval_set_v1.json is >= 0.90."""
    eval_items = load_eval_set()
    assert len(eval_items) > 0, "Eval set must not be empty"

    correct = 0
    mismatches = []

    for item in eval_items:
        word = item["word"]
        sentence = item.get("sentence", "")
        expected_group = item["expected_group"]

        verdict = classify(word, sentence=sentence)
        if verdict.group == expected_group:
            correct += 1
        else:
            mismatches.append(
                f"Word: '{word}' -> Got Group: '{verdict.group}', Expected: '{expected_group}' (Sentence: '{sentence}')"
            )

    accuracy = correct / len(eval_items)
    print(f"\nTaxonomy Evaluation: {correct}/{len(eval_items)} correct ({accuracy * 100:.2f}%)")

    if mismatches:
        print("\nMismatches:")
        for m in mismatches[:10]:
            print(f"  • {m}")

    assert accuracy >= 0.90, f"Taxonomy accuracy {accuracy:.4f} is below required threshold 0.90"
