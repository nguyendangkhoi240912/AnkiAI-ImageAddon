"""Latency benchmark test suite for local classification step.

Asserts that pure local classification is <= 50ms per word (Master Spec §20).
"""

import time
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


def test_classification_latency_benchmark():
    """Verify that average and p95 latency for local classification is <= 50ms per word."""
    items = load_eval_set()
    assert len(items) > 0, "Eval set must not be empty"

    # Warmup
    for item in items[:10]:
        classify(item["word"], sentence=item.get("sentence", ""))

    latencies_ms = []

    for item in items:
        word = item["word"]
        sentence = item.get("sentence", "")

        t0 = time.perf_counter()
        _ = classify(word, sentence=sentence)
        t1 = time.perf_counter()

        elapsed_ms = (t1 - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

    avg_latency = sum(latencies_ms) / len(latencies_ms)
    sorted_latencies = sorted(latencies_ms)
    p95_idx = int(len(sorted_latencies) * 0.95)
    p95_latency = sorted_latencies[p95_idx]

    print(f"\nClassification Latency Benchmark:")
    print(f"  • Total words tested: {len(latencies_ms)}")
    print(f"  • Average latency: {avg_latency:.4f} ms/word")
    print(f"  • p95 latency: {p95_latency:.4f} ms/word")
    print(f"  • Max latency: {max(latencies_ms):.4f} ms/word")

    assert avg_latency <= 50.0, f"Average latency {avg_latency:.2f}ms exceeds 50ms limit"
    assert p95_latency <= 50.0, f"p95 latency {p95_latency:.2f}ms exceeds 50ms limit"
