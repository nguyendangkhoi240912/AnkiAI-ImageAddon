"""Model and NLP resource downloader with sha256 validation, resume support, and progress reporting.

According to Master Spec v9 §0 (Rule 6), §5.1, §14.
"""

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Callable, Optional, Dict

import requests

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "user_files" / "models"


class DownloadError(Exception):
    """Exception raised when downloading a model fails."""
    pass


def compute_file_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """Compute sha256 checksum of a local file."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()


def download_file_with_resume(
    url: str,
    target_path: Path,
    expected_sha256: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    timeout: int = 30,
) -> Path:
    """Download a file with HTTP Range resume support, progress callback, and sha256 validation.

    Args:
        url: Direct download URL.
        target_path: Destination file path.
        expected_sha256: Optional expected SHA256 checksum.
        progress_callback: Optional callback receiving (bytes_downloaded, total_bytes).
        timeout: Network timeout in seconds.

    Returns:
        Path to verified downloaded file.
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".part")

    # If target already exists and sha256 matches, skip download
    if target_path.exists() and expected_sha256:
        existing_sha = compute_file_sha256(target_path)
        if existing_sha.lower() == expected_sha256.lower():
            logger.info("Model file already exists with valid checksum: %s", target_path)
            return target_path

    downloaded_bytes = 0
    headers: Dict[str, str] = {}

    if temp_path.exists():
        downloaded_bytes = temp_path.stat().st_size
        headers["Range"] = f"bytes={downloaded_bytes}-"

    response = requests.get(url, headers=headers, stream=True, timeout=timeout)

    # If server doesn't support Range, restart from scratch
    if response.status_code == 200 and downloaded_bytes > 0:
        downloaded_bytes = 0
        mode = "wb"
    elif response.status_code == 206:
        mode = "ab"
    elif response.status_code in (200, 201):
        mode = "wb"
    else:
        raise DownloadError(f"HTTP error {response.status_code} downloading {url}")

    total_bytes = int(response.headers.get("content-length", 0)) + downloaded_bytes

    with open(temp_path, mode) as f:
        for chunk in response.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
                downloaded_bytes += len(chunk)
                if progress_callback:
                    progress_callback(downloaded_bytes, total_bytes)

    # Verify sha256 if provided
    if expected_sha256:
        actual_sha = compute_file_sha256(temp_path)
        if actual_sha.lower() != expected_sha256.lower():
            temp_path.unlink(missing_ok=True)
            raise DownloadError(
                f"Checksum mismatch for {url}: expected {expected_sha256}, got {actual_sha}"
            )

    # Rename temp to target atomically
    temp_path.rename(target_path)
    logger.info("Successfully downloaded and verified: %s", target_path)
    return target_path


def ensure_wordnet_installed(models_dir: Optional[Path] = None) -> bool:
    """Lazy-load or verify offline WordNet resources."""
    try:
        import nltk
        from nltk.corpus import wordnet as wn
        # Try a probe lookup
        wn.synsets("apple")
        return True
    except (ImportError, LookupError):
        logger.debug("NLTK/WordNet not available in environment; using pure Python fallback datasets.")
        return False


def ensure_spacy_installed(model_name: str = "en_core_web_sm") -> bool:
    """Lazy-load or verify spaCy model."""
    try:
        import spacy
        spacy.load(model_name)
        return True
    except (ImportError, OSError):
        logger.debug("spaCy model '%s' not available; using pure Python fallback datasets.", model_name)
        return False


# ---------------------------------------------------------------------------
# GĐ2, G2.4 — CLIP ONNX model download helpers
# ---------------------------------------------------------------------------
# Model hosted on Hugging Face Hub.
# URLs and sha256 here are placeholders — replace with final verified values
# before packaging for release.  The addon checks sha256 if non-empty.
CLIP_MODELS: Dict[str, Dict] = {
    "clip-vit-b32-fp16.onnx": {
        "url": "https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/onnx/model_fp16.onnx",
        "sha256": "",   # TODO: fill in once release URL is confirmed
        "tier": "full",
    },
    "clip-vit-b32-int8.onnx": {
        "url": "https://huggingface.co/openai/clip-vit-base-patch32/resolve/main/onnx/model_quantized.onnx",
        "sha256": "",   # TODO: fill in
        "tier": "quantized",
    },
}


def ensure_clip_model(
    tier: str = "full",
    progress_callback: Optional[Callable[[int, int], None]] = None,
    models_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Download the requested CLIP ONNX model to MODELS_DIR if not already present.

    Args:
        tier: "full" (fp16) or "quantized" (int8).
        progress_callback: Optional (bytes_done, total_bytes) callback.
        models_dir: Override default MODELS_DIR (for tests).

    Returns:
        Path to the model file, or None if download failed or was skipped.
    """
    dest_dir = Path(models_dir) if models_dir else MODELS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Find the matching model spec
    spec = next(
        (info for name, info in CLIP_MODELS.items() if info["tier"] == tier),
        None,
    )
    if spec is None:
        logger.error("Unknown CLIP tier: %s", tier)
        return None

    filename = next(name for name, info in CLIP_MODELS.items() if info["tier"] == tier)
    target = dest_dir / filename

    if target.exists():
        if not spec["sha256"]:
            logger.info("CLIP model already present (skipping checksum — sha256 not set): %s", target)
            return target
        existing_sha = compute_file_sha256(target)
        if existing_sha.lower() == spec["sha256"].lower():
            logger.info("CLIP model already present and verified: %s", target)
            return target
        logger.warning("CLIP model checksum mismatch, re-downloading: %s", target)

    logger.info("Downloading CLIP model (%s) from %s ...", tier, spec["url"])
    try:
        path = download_file_with_resume(
            url=spec["url"],
            target_path=target,
            expected_sha256=spec["sha256"] or None,
            progress_callback=progress_callback,
        )
        return path
    except DownloadError as exc:
        logger.error("CLIP model download failed: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error downloading CLIP model: %s", exc)
        return None
