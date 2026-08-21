"""
Groq Client — GĐ4, G4.1                                    [MS §4, §11]
=========================================================================
Batch text LLM client cho Groq API với:
  • Auto batch-size dựa trên TPM đo được lúc chạy
  • Pacing (token/phút) để không vượt rate limit
  • Model fallback: workhorse → hard → Gemini (nếu có)
  • Model probe đầu phiên: xác nhận model còn sống + đo latency
  • Deadline per call (groq_realtime_deadline_ms cho đơn thẻ,
    groq_batch_deadline_ms cho lô)

Không import Qt/Anki.
"""
from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from AnkiAI_ImageAddon.modules.http_session_manager import HTTPSessionManager

logger = logging.getLogger(__name__)

_GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
_DEFAULT_TEMPERATURE = 0.3
_DEFAULT_MAX_TOKENS = 512
_RETRY_ON_SCHEMA_ERROR = 1   # retry once if response fails schema validation


class GroqError(Exception):
    """Raised for Groq API errors (rate limit, model removed, network)."""
    pass


# ---------------------------------------------------------------------------
# Token-per-minute pacer
# ---------------------------------------------------------------------------

class _TPMPacer:
    """Simple sliding-window token pacer.

    Tracks tokens consumed in the last 60 s and sleeps when approaching limit.
    """

    def __init__(self, tpm_limit: int = 6000):
        self._limit = tpm_limit
        self._window: List[Tuple[float, int]] = []   # (timestamp, tokens)
        self._lock = Lock()

    def record(self, tokens: int) -> None:
        with self._lock:
            now = time.monotonic()
            self._window = [(t, n) for t, n in self._window if now - t < 60.0]
            self._window.append((now, tokens))

    def wait_if_needed(self, estimated_tokens: int) -> None:
        """Block until there is budget for estimated_tokens."""
        while True:
            with self._lock:
                now = time.monotonic()
                self._window = [(t, n) for t, n in self._window if now - t < 60.0]
                used = sum(n for _, n in self._window)
                if used + estimated_tokens <= self._limit:
                    return
            time.sleep(0.5)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

class GroqClient:
    """
    Groq LLM client for batch text generation.

    Args:
        api_key:          Groq API key.
        workhorse_model:  Fast model for most requests (from config).
        hard_model:       Slower/smarter model for difficult words.
        vision_model:     Vision model name (optional, may be unavailable).
        tpm_limit:        Token per minute limit for pacing.
        realtime_deadline_ms: Max ms for single-card calls.
        batch_deadline_ms:   Max ms for batch calls.
    """

    def __init__(
        self,
        api_key: str,
        workhorse_model: str = "openai/gpt-oss-20b",
        hard_model: str = "openai/gpt-oss-120b",
        vision_model: str = "qwen/qwen3.6-27b",
        tpm_limit: int = 6000,
        realtime_deadline_ms: int = 1800,
        batch_deadline_ms: int = 8000,
    ):
        if not api_key or not api_key.strip():
            raise GroqError("Groq API key not configured")
        self._api_key = api_key.strip()
        self._workhorse_model = workhorse_model
        self._hard_model = hard_model
        self._vision_model = vision_model
        self._realtime_deadline_ms = realtime_deadline_ms
        self._batch_deadline_ms = batch_deadline_ms
        self._pacer = _TPMPacer(tpm_limit)
        self._session = HTTPSessionManager.get_session("groq_llm")
        # Probe results (set by probe_models)
        self._available_models: Dict[str, bool] = {}
        self._model_latency: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # Model probe (MS §4 — run at session start)
    # ------------------------------------------------------------------

    def probe_models(self, timeout_s: float = 5.0) -> Dict[str, bool]:
        """Probe all configured models with a minimal request.

        Returns dict of {model_name: is_alive}.
        Stores results for use by send_batch().
        """
        models = [self._workhorse_model, self._hard_model]
        if self._vision_model:
            models.append(self._vision_model)

        def _probe(model: str) -> Tuple[str, bool, float]:
            try:
                t0 = time.perf_counter()
                resp = self._call_api(
                    model=model,
                    messages=[{"role": "user", "content": "x"}],
                    max_tokens=5,
                    timeout_s=timeout_s,
                )
                latency = time.perf_counter() - t0
                alive = resp is not None
                return model, alive, latency
            except Exception as e:
                logger.debug(f"Probe failed for {model}: {e}")
                return model, False, float("inf")

        results = {}
        with ThreadPoolExecutor(max_workers=len(models)) as ex:
            futures = {ex.submit(_probe, m): m for m in models}
            for fut in as_completed(futures):
                model, alive, latency = fut.result()
                results[model] = alive
                self._available_models[model] = alive
                self._model_latency[model] = latency
                status = "✓" if alive else "✗"
                logger.info(f"Model probe {status} {model} ({latency*1000:.0f} ms)")
                if not alive:
                    logger.warning(
                        f"Model '{model}' appears unavailable — will be skipped in fallback chain"
                    )

        return results

    def is_model_available(self, model: str) -> bool:
        """Return probe result; True if not yet probed (optimistic)."""
        return self._available_models.get(model, True)

    # ------------------------------------------------------------------
    # Core API call
    # ------------------------------------------------------------------

    def _call_api(
        self,
        model: str,
        messages: List[Dict],
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
        timeout_s: float = 10.0,
        system: Optional[str] = None,
    ) -> Optional[Dict]:
        """Execute one Groq API call; return parsed JSON response or None."""
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        payload = {
            "model": model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            resp = self._session.post(
                _GROQ_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout_s,
            )
            if resp.status_code == 429:
                raise GroqError(f"Rate limited (429) on {model}")
            if resp.status_code == 404:
                self._available_models[model] = False
                raise GroqError(f"Model not found (404): {model}")
            if resp.status_code != 200:
                raise GroqError(f"HTTP {resp.status_code} from Groq: {resp.text[:200]}")
            data = resp.json()
            # Record token usage for pacer
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            if tokens:
                self._pacer.record(tokens)
            return data
        except requests.exceptions.Timeout:
            raise GroqError(f"Timeout ({timeout_s}s) calling {model}")
        except requests.exceptions.ConnectionError as e:
            raise GroqError(f"Connection error: {e}")

    def _extract_text(self, response: Dict) -> str:
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise GroqError(f"Unexpected response shape: {e}")

    # ------------------------------------------------------------------
    # Batch generation with fallback
    # ------------------------------------------------------------------

    def send_batch(
        self,
        system: str,
        user_content: str,
        tier: str = "workhorse",
        parse_fn: Optional[Callable[[str], list]] = None,
        deadline_ms: Optional[int] = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> list:
        """Send a batch prompt and return parsed results.

        Args:
            system:       System prompt string.
            user_content: User turn (already formatted, e.g. from prompts.py).
            tier:         "workhorse" | "hard" — selects primary model.
            parse_fn:     Function to parse the raw text response into a list.
                          If None, returns [raw_text].
            deadline_ms:  Override default deadline.
            max_tokens:   Max tokens in completion.

        Returns:
            Parsed list (from parse_fn) or [] on total failure.
        """
        if deadline_ms is None:
            deadline_ms = (
                self._realtime_deadline_ms if tier == "workhorse"
                else self._batch_deadline_ms
            )

        # Build fallback chain based on tier + availability
        if tier == "workhorse":
            chain = [self._workhorse_model]
            if self._hard_model != self._workhorse_model:
                chain.append(self._hard_model)
        else:
            chain = [self._hard_model, self._workhorse_model]

        # Skip probed-dead models
        chain = [m for m in chain if self.is_model_available(m)]
        if not chain:
            logger.error("No available Groq models in chain")
            return []

        timeout_s = deadline_ms / 1000.0
        messages = [{"role": "user", "content": user_content}]

        for model in chain:
            try:
                # Pacing: estimate tokens (rough: 1 token ≈ 4 chars)
                estimated = len(user_content) // 4 + max_tokens
                self._pacer.wait_if_needed(estimated)

                resp = self._call_api(
                    model=model,
                    messages=messages,
                    system=system,
                    max_tokens=max_tokens,
                    timeout_s=timeout_s,
                )
                if resp is None:
                    continue
                text = self._extract_text(resp)

                if parse_fn is None:
                    return [text]

                # Try parse; retry once on schema error
                result = parse_fn(text)
                if result:
                    return result

                # Retry once
                logger.debug(f"Parse failed on {model}, retrying...")
                resp2 = self._call_api(
                    model=model, messages=messages, system=system,
                    max_tokens=max_tokens, timeout_s=timeout_s,
                )
                if resp2:
                    result2 = parse_fn(self._extract_text(resp2))
                    if result2:
                        return result2

                logger.warning(f"Schema validation failed after retry on {model}, trying next model")

            except GroqError as e:
                logger.warning(f"Groq {model} failed: {e}")
                continue

        logger.error("All Groq models failed for this batch")
        return []

    # ------------------------------------------------------------------
    # Convenience wrappers
    # ------------------------------------------------------------------

    def classify_batch(self, items: List[dict], tier: str = "workhorse", deadline_ms: Optional[int] = None) -> list:
        """Run P1 classify+query batch. Returns list of verdict dicts."""
        from AnkiAI_ImageAddon.modules.llm.prompts import (
            P1_SYSTEM, build_p1_user, parse_p1_response,
        )
        return self.send_batch(
            system=P1_SYSTEM,
            user_content=build_p1_user(items),
            tier=tier,
            parse_fn=parse_p1_response,
            deadline_ms=deadline_ms,
        )

    def abstract_batch(self, items: List[dict], deadline_ms: Optional[int] = None) -> list:
        """Run P2 abstract/idiom batch. Returns list of proxy dicts."""
        from AnkiAI_ImageAddon.modules.llm.prompts import (
            P2_SYSTEM, build_p2_user, parse_p2_response,
        )
        return self.send_batch(
            system=P2_SYSTEM,
            user_content=build_p2_user(items),
            tier="hard",
            parse_fn=parse_p2_response,
            deadline_ms=deadline_ms,
        )


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_global_client: Optional[GroqClient] = None


def get_groq_client(config=None) -> Optional[GroqClient]:
    """Lazy singleton. Returns None if API key not configured."""
    global _global_client
    if _global_client is not None:
        return _global_client
    if config is None:
        try:
            from AnkiAI_ImageAddon.modules.config import get_config_manager
            config = get_config_manager()
        except Exception:
            return None
    api_key = config.get("groq_api_key", "")
    if not api_key:
        return None
    _global_client = GroqClient(
        api_key=api_key,
        workhorse_model=config.get("groq_workhorse_model", "openai/gpt-oss-20b"),
        hard_model=config.get("groq_hard_model", "openai/gpt-oss-120b"),
        vision_model=config.get("groq_vision_model", "qwen/qwen3.6-27b"),
        realtime_deadline_ms=config.get("groq_realtime_deadline_ms", 1800),
        batch_deadline_ms=config.get("groq_batch_deadline_ms", 8000),
    )
    return _global_client
