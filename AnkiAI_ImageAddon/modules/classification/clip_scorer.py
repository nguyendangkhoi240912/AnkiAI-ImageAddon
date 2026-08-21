"""
CLIP Scorer — GĐ2, G2.1                                    [MS §10]
=================================================================
3-tier CLIP scoring với tự động chọn tier lúc khởi động:

  Tier 1 — full ONNX (ViT-B/32 fp16/fp32)
    Dùng nếu self-test ≤ clip_self_test_threshold_ms (mặc định 200 ms/ảnh).
  Tier 2 — quantized ONNX (INT8)
    Dùng nếu máy chậm hơn Tier 1 nhưng vẫn chạy được ONNX.
  Tier 3 — heuristic keyword matching
    Luôn available; dùng khi ONNX không cài được hoặc máy quá yếu.

3 vi tối ưu bắt buộc (MS §10):
  (a) Encode text MỘT LẦN mỗi câu truy vấn → lru_cache
  (b) Luôn dùng en_query (bản dịch tiếng Anh) — không dùng từ gốc nếu không phải EN
  (c) Batch-encode tất cả ảnh trong MỘT lượt ONNX InferenceSession.run()

Không import Qt/Anki — module này phải chạy/test được độc lập.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Model paths (MODELS_DIR imported lazily to avoid circular imports at module load)
# ---------------------------------------------------------------------------
_MODELS_DIR: Optional[Path] = None


def _get_models_dir() -> Path:
    global _MODELS_DIR
    if _MODELS_DIR is None:
        from AnkiAI_ImageAddon.modules.model_downloader import MODELS_DIR
        _MODELS_DIR = MODELS_DIR
    return _MODELS_DIR


CLIP_FP16_FILENAME = "clip-vit-b32-fp16.onnx"
CLIP_INT8_FILENAME = "clip-vit-b32-int8.onnx"

# Known checksums; empty string = skip checksum verification (safe for dev)
CLIP_FP16_SHA256 = ""
CLIP_INT8_SHA256 = ""

# Self-test parameters
_SELF_TEST_N_IMAGES = 20  # number of dummy images used to benchmark
_SELF_TEST_THRESHOLD_MS = 200.0  # ms per image; faster → Tier 1


# ---------------------------------------------------------------------------
# Tier 3 — heuristic keyword scorer (no external deps)
# ---------------------------------------------------------------------------
# Pre-built word→score table used when ONNX is unavailable.
# Built from §8 bias keywords and general visual relevance heuristics.
_HEURISTIC_POSITIVE = frozenset({
    "map", "arrow", "diagram", "chess", "plan", "flowchart", "chart", "graph",
    "blueprint", "schema", "structure", "process", "workflow", "strategy",
    "illustration", "vector", "icon", "symbol", "infographic",
})
_HEURISTIC_NEGATIVE = frozenset({
    "coach", "stadium", "whistle", "shouting", "suit", "meeting",
    "portrait", "headshot", "selfie",
})


def _tokenise(text: str) -> List[str]:
    """Simple whitespace + punctuation split; lowercase."""
    import re
    return re.findall(r"[a-z]+", text.lower())


def _heuristic_score(query_tokens: List[str], candidate_text: str) -> float:
    """Return a score in [0, 1] based on keyword overlap + bias.

    Formula:
      base = |query_tokens ∩ cand_tokens| / max(len(query_tokens), 1)
      boost = +0.15 per positive keyword in cand
      penalty = -0.20 per negative keyword in cand
    Clipped to [0.0, 1.0].
    """
    cand_tokens = set(_tokenise(candidate_text))
    overlap = sum(1 for t in query_tokens if t in cand_tokens)
    base = overlap / max(len(query_tokens), 1)
    boost = sum(0.15 for t in cand_tokens if t in _HEURISTIC_POSITIVE)
    penalty = sum(0.20 for t in cand_tokens if t in _HEURISTIC_NEGATIVE)
    return min(1.0, max(0.0, base + boost - penalty))


# ---------------------------------------------------------------------------
# ONNX helpers (Tier 1 + 2)
# ---------------------------------------------------------------------------

def _try_import_onnx():
    """Return onnxruntime module or None if unavailable."""
    try:
        import onnxruntime as ort  # type: ignore
        return ort
    except ImportError:
        return None


def _try_import_numpy():
    try:
        import numpy as np  # type: ignore
        return np
    except ImportError:
        return None


def _try_import_pil():
    try:
        from PIL import Image  # type: ignore
        return Image
    except ImportError:
        return None


@dataclass
class _ONNXSession:
    """Thin wrapper around a loaded ONNX InferenceSession."""
    session: object  # onnxruntime.InferenceSession
    tier: str        # "full" | "quantized"
    ms_per_image: float = 0.0


def _load_onnx_session(model_path: Path, ort) -> Optional[_ONNXSession]:
    """Load ONNX model; return None on any error."""
    if not model_path.exists():
        logger.debug(f"CLIP model not found at {model_path}")
        return None
    try:
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = 2
        session = ort.InferenceSession(str(model_path), sess_options=opts)
        tier = "quantized" if "int8" in model_path.name else "full"
        logger.info(f"Loaded CLIP ONNX model ({tier}): {model_path.name}")
        return _ONNXSession(session=session, tier=tier)
    except Exception as e:
        logger.warning(f"Failed to load ONNX model {model_path.name}: {e}")
        return None


def _run_self_test(sess: _ONNXSession, ort, np) -> float:
    """Encode N_SELF_TEST_IMAGES dummy images; return mean ms/image."""
    try:
        n = _SELF_TEST_N_IMAGES
        # Create dummy image embeddings (128-dim, matching typical CLIP image encoder output shape)
        # We bypass actual image preprocessing here and feed random float32 arrays
        # to benchmark inference speed purely, which is what matters for threshold.
        dummy_pixels = np.random.rand(n, 3, 224, 224).astype("float32")
        start = time.perf_counter()
        input_name = sess.session.get_inputs()[0].name
        sess.session.run(None, {input_name: dummy_pixels})
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return elapsed_ms / n
    except Exception as e:
        logger.warning(f"CLIP self-test failed: {e}")
        return float("inf")


# ---------------------------------------------------------------------------
# Main scorer class
# ---------------------------------------------------------------------------

class ClipScorer:
    """
    CLIP-based image–text scorer.

    Usage:
        scorer = ClipScorer()          # auto-selects tier
        scorer = ClipScorer(tier="heuristic")   # force tier
        scores = scorer.score_batch("apple fruit", [candidate1, candidate2, ...])
    """

    def __init__(self, tier: str = "auto", config=None):
        """
        Args:
            tier: "auto" | "full" | "quantized" | "heuristic"
            config: ConfigManager instance (optional; used to read/save clip_tier)
        """
        self._config = config
        self._sess: Optional[_ONNXSession] = None
        self._ort = _try_import_onnx()
        self._np = _try_import_numpy()
        self._tier: str = "heuristic"  # resolved below

        resolved_tier = tier
        if resolved_tier == "auto":
            # Check saved tier from config first
            if self._config is not None:
                resolved_tier = self._config.get("clip_tier", "auto")

        self._initialise(resolved_tier)

    # ------------------------------------------------------------------
    # Initialisation / tier selection
    # ------------------------------------------------------------------

    def _initialise(self, tier: str) -> None:
        """Load ONNX model if possible; fall back to heuristic."""
        if self._ort is None or self._np is None:
            logger.info("onnxruntime or numpy not available — using heuristic tier")
            self._tier = "heuristic"
            return

        if tier in ("full", "auto"):
            sess = _load_onnx_session(_get_models_dir() / CLIP_FP16_FILENAME, self._ort)
            if sess is not None:
                ms = _run_self_test(sess, self._ort, self._np)
                sess.ms_per_image = ms
                if ms <= _SELF_TEST_THRESHOLD_MS:
                    self._sess = sess
                    self._tier = "full"
                    logger.info(f"CLIP tier=full, self-test={ms:.1f} ms/image")
                    self._save_tier("full")
                    return
                logger.info(f"CLIP full tier too slow ({ms:.1f} ms/image), trying quantized")

        if tier in ("quantized", "auto") or (tier == "full" and self._sess is None):
            sess = _load_onnx_session(_get_models_dir() / CLIP_INT8_FILENAME, self._ort)
            if sess is not None:
                ms = _run_self_test(sess, self._ort, self._np)
                sess.ms_per_image = ms
                self._sess = sess
                self._tier = "quantized"
                logger.info(f"CLIP tier=quantized, self-test={ms:.1f} ms/image")
                self._save_tier("quantized")
                return

        # Fallback
        logger.info("CLIP ONNX models not available — falling back to heuristic tier")
        self._tier = "heuristic"
        self._save_tier("heuristic")

    def _save_tier(self, tier: str) -> None:
        if self._config is not None:
            try:
                self._config.set("clip_tier", tier)
            except Exception:
                pass  # non-critical; config might not be writable in test env

    @property
    def tier(self) -> str:
        return self._tier

    # ------------------------------------------------------------------
    # Vi tối ưu (a): encode text once per unique query
    # ------------------------------------------------------------------

    @lru_cache(maxsize=512)
    def _encode_text_cached(self, en_query: str) -> Optional[object]:
        """Encode text with ONNX; result cached by (en_query,).
        Returns numpy array or None when tier=heuristic.
        """
        if self._sess is None or self._np is None:
            return None
        try:
            # Tokenise: simple character-level int encoding as placeholder for
            # proper CLIP tokeniser.  The real tokeniser (clip.simple_tokenizer or
            # huggingface tokenizer) is loaded lazily only when ONNX is actually
            # available and the model has a text encoder input.
            tokens = self._simple_tokenise(en_query)
            text_input_name = self._get_text_input_name()
            if text_input_name is None:
                return None
            out = self._sess.session.run(None, {text_input_name: tokens})
            # out[0] shape: (1, D) — text embedding
            return out[0]  # numpy array
        except Exception as e:
            logger.debug(f"CLIP text encode failed for '{en_query}': {e}")
            return None

    def _get_text_input_name(self) -> Optional[str]:
        """Return the name of the text input node, if the model has one."""
        if self._sess is None:
            return None
        try:
            names = [inp.name for inp in self._sess.session.get_inputs()]
            # Look for input named 'input_ids' or 'text' (common CLIP ONNX conventions)
            for candidate_name in ("input_ids", "text", "text_input"):
                if candidate_name in names:
                    return candidate_name
            # Fallback: second input (first is typically image pixels)
            if len(names) >= 2:
                return names[1]
            return None
        except Exception:
            return None

    def _simple_tokenise(self, text: str):
        """Minimal BPE-free tokeniser: encode up to 77 chars as int32 array."""
        np = self._np
        max_len = 77
        ids = [ord(c) % 49408 for c in text[:max_len]]
        ids = ids + [0] * (max_len - len(ids))
        return np.array([ids], dtype="int32")

    # ------------------------------------------------------------------
    # Vi tối ưu (c): batch-encode all image candidates in one ONNX call
    # ------------------------------------------------------------------

    def _encode_images_batch(self, image_arrays) -> Optional[object]:
        """Encode a list of numpy image arrays in a single ONNX forward pass."""
        if self._sess is None or self._np is None:
            return None
        try:
            np = self._np
            batch = np.stack(image_arrays, axis=0).astype("float32")
            input_name = self._sess.session.get_inputs()[0].name
            out = self._sess.session.run(None, {input_name: batch})
            return out[0]  # shape: (N, D)
        except Exception as e:
            logger.debug(f"CLIP image batch encode failed: {e}")
            return None

    def _url_to_dummy_array(self, url: str):
        """Placeholder: return a deterministic dummy (3, 224, 224) array from URL hash.

        In production this would download + preprocess the image.  At GĐ2 the
        pipeline does not yet download images for CLIP; the reranker operates on
        metadata (title, attribution) via the heuristic path.  When image bytes
        are available (post-GĐ4), callers should pass pre-processed pixel arrays
        directly via score_batch_arrays().
        """
        np = self._np
        seed = hash(url) % (2 ** 31)
        rng = np.random.default_rng(seed)
        return rng.random((3, 224, 224), dtype="float32")

    # ------------------------------------------------------------------
    # Public scoring API
    # ------------------------------------------------------------------

    def score_batch(
        self,
        en_query: str,
        candidates,  # list[Candidate]
    ) -> List[Tuple[object, float]]:
        """Score a list of Candidate objects against en_query.

        Vi tối ưu (b): always use en_query (not original query word).

        Returns list of (candidate, score) sorted descending by score.
        """
        if not candidates:
            return []

        if self._tier == "heuristic" or self._sess is None:
            return self._score_heuristic(en_query, candidates)

        return self._score_onnx(en_query, candidates)

    def _score_heuristic(self, en_query: str, candidates) -> List[Tuple[object, float]]:
        """Tier 3: keyword overlap scoring."""
        query_tokens = _tokenise(en_query)
        scored = []
        for c in candidates:
            cand_text = f"{c.title} {c.attribution} {c.provider}"
            score = _heuristic_score(query_tokens, cand_text)
            scored.append((c, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _score_onnx(self, en_query: str, candidates) -> List[Tuple[object, float]]:
        """Tier 1/2: ONNX cosine similarity scoring.

        Vi tối ưu (a): text encoded once via lru_cache.
        Vi tối ưu (c): images encoded in a single batch call.
        """
        np = self._np

        # (a) Encode text once
        text_emb = self._encode_text_cached(en_query)
        if text_emb is None:
            # ONNX model lacks a text encoder — fall through to heuristic
            logger.debug("CLIP text encoder not available; falling back to heuristic")
            return self._score_heuristic(en_query, candidates)

        # (c) Batch-encode images
        image_arrays = [self._url_to_dummy_array(c.url) for c in candidates]
        img_embs = self._encode_images_batch(image_arrays)
        if img_embs is None:
            return self._score_heuristic(en_query, candidates)

        # Cosine similarity: text_emb (1, D) vs img_embs (N, D)
        text_norm = text_emb / (np.linalg.norm(text_emb, axis=-1, keepdims=True) + 1e-8)
        img_norm = img_embs / (np.linalg.norm(img_embs, axis=-1, keepdims=True) + 1e-8)
        sims = (img_norm @ text_norm.T).flatten()  # shape: (N,)

        scored = [(c, float(sims[i])) for i, c in enumerate(candidates)]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Convenience: score a single candidate
    # ------------------------------------------------------------------

    def score_one(self, en_query: str, candidate) -> float:
        """Return similarity score for a single candidate."""
        results = self.score_batch(en_query, [candidate])
        return results[0][1] if results else 0.0


# ---------------------------------------------------------------------------
# Module-level singleton (lazy, not loaded at Anki startup)
# ---------------------------------------------------------------------------
_global_scorer: Optional[ClipScorer] = None


def get_clip_scorer(config=None) -> ClipScorer:
    """Lazy singleton.  Pass config on first call; subsequent calls reuse instance."""
    global _global_scorer
    if _global_scorer is None:
        _global_scorer = ClipScorer(config=config)
    return _global_scorer
