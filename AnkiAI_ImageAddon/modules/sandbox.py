"""CLI sandbox tool for testing pipeline stages independently without running Anki.

Usage:
  python3 -m AnkiAI_ImageAddon.modules.sandbox --word tactics --sentence "The coach explained his tactics." --stage all

According to Master Spec v9 §17.3.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, List

try:
    from .classification.taxonomy import classify, Verdict
    from .classification.visual_type import get_visual_type_for_group
except (ImportError, ValueError):
    from modules.classification.taxonomy import classify, Verdict
    from modules.classification.visual_type import get_visual_type_for_group

try:
    from image_providers.base_provider import Candidate
except (ImportError, ValueError):
    try:
        from ..image_providers.base_provider import Candidate
    except (ImportError, ValueError):
        from AnkiAI_ImageAddon.image_providers.base_provider import Candidate

# G3.3: Local SVG provider for groups K and N
try:
    from image_providers.local_svg_provider import get_local_svg
except (ImportError, ValueError):
    try:
        from ..image_providers.local_svg_provider import get_local_svg
    except (ImportError, ValueError):
        from AnkiAI_ImageAddon.image_providers.local_svg_provider import get_local_svg

logger = logging.getLogger("sandbox")


def run_classification_stage(word: str, sentence: str = "") -> Verdict:
    """Run stage 1: Taxonomy classification & visual_type determination."""
    verdict = classify(word, sentence=sentence)
    return verdict


def format_sandbox_output(
    word: str,
    sentence: str,
    stage: str,
    verdict: Verdict,
    candidates: List[Candidate] = None,
    latency_ms: float = 0.0,
) -> str:
    """Format human-readable sandbox inspection output."""
    lines = [
        "=" * 60,
        f"🔬 AnkiAI Pipeline Sandbox — Word: '{word}'",
        "=" * 60,
        f"Input Sentence : {sentence or '(none)'}",
        f"Selected Stage : {stage}",
        f"Latency        : {latency_ms:.2f} ms",
        "-" * 60,
        "📊 Stage 1: Classification & Visual Type",
        f"  • Assigned Group : {verdict.group} (Group A–N)",
        f"  • Visual Type    : {verdict.visual_type}",
        f"  • Final Query    : {verdict.query}",
        f"  • Alternate Query: {verdict.alt}",
        f"  • Confidence     : {verdict.confidence:.2f}",
        f"  • Resolved By    : {verdict.resolved_by}",
        f"  • Sense ID       : {verdict.sense_id or '(none)'}",
        f"  • English Query  : {verdict.en_query}",
    ]

    if candidates:
        lines.append("-" * 60)
        lines.append(f"🖼️  Stage 2: Top-{len(candidates)} Image Candidates")
        for idx, cand in enumerate(candidates, start=1):
            lines.append(
                f"  [{idx}] Provider: {cand.provider:<12} | Score: {cand.score:.2f} | Title: {cand.title[:30]}"
            )
            lines.append(f"      URL: {cand.url[:80]}{'...' if len(cand.url) > 80 else ''}")

    # G3.3: local SVG result
    if verdict.visual_type == "local_svg":
        lines.append("-" * 60)
        lines.append("🎨  Stage 2 (local_svg): SVG generated — 0 network requests")
        svg_cand = get_local_svg(verdict.word, verdict.group)
        if svg_cand:
            lines.append(f"  • Provider : {svg_cand.provider}")
            lines.append(f"  • Size     : {svg_cand.width}×{svg_cand.height}px")
            lines.append(f"  • License  : {svg_cand.license}")
            url_preview = svg_cand.url[:60] + "..." if len(svg_cand.url) > 60 else svg_cand.url
            lines.append(f"  • URL      : {url_preview}")
        else:
            lines.append("  ⚠ SVG generation returned None")

    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="AnkiAI Pipeline Sandbox (runs pipeline stages without Anki UI)"
    )
    parser.add_argument("--word", "-w", required=True, help="Vocabulary word to test")
    parser.add_argument("--sentence", "-s", default="", help="Context sentence")
    parser.add_argument(
        "--stage",
        choices=["classify", "search", "rerank", "qc", "all"],
        default="all",
        help="Pipeline stage to execute (default: all)",
    )
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")

    args = parser.parse_args()

    t0 = time.perf_counter()
    verdict = run_classification_stage(args.word, sentence=args.sentence)
    t1 = time.perf_counter()
    latency_ms = (t1 - t0) * 1000.0

    if args.json:
        out = {
            "word": args.word,
            "sentence": args.sentence,
            "stage": args.stage,
            "latency_ms": latency_ms,
            "verdict": verdict.to_dict(),
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(
            format_sandbox_output(
                word=args.word,
                sentence=args.sentence,
                stage=args.stage,
                verdict=verdict,
                latency_ms=latency_ms,
            )
        )


if __name__ == "__main__":
    main()
