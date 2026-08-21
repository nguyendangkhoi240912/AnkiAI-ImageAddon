"""
Logging Setup — GĐ4, G4.9                                  [MS §12, §17.1]
=========================================================================
Rotating log handler ghi vào user_files/logs/ (3 × 1 MB) với bộ lọc
tự động redact API key trước khi ghi.

Không import Qt/Anki.

Usage:
    from AnkiAI_ImageAddon.modules.logging_setup import setup_addon_logging
    setup_addon_logging()   # gọi một lần khi addon khởi động

Sau khi setup, mọi logger trong package đều tự động ghi vào file + console.
"""
from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_LOG_DIR_NAME = "logs"
_LOG_FILENAME = "ankiai.log"
_MAX_BYTES = 1 * 1024 * 1024   # 1 MB per file
_BACKUP_COUNT = 3               # 3 rotating files → tối đa 3 MB
_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Patterns used to redact secrets from log messages
_SECRET_PATTERNS = [
    # Generic API key patterns: 20+ chars alphanumeric/dash/underscore after keyword
    re.compile(
        r'((?:api[_-]?key|apikey|token|secret|password|Authorization)["\s:=]+)[A-Za-z0-9_\-\.]{10,}',
        re.IGNORECASE,
    ),
    # Bearer tokens
    re.compile(r'(Bearer\s+)[A-Za-z0-9_\-\.]{10,}', re.IGNORECASE),
    # Groq/Gemini key format: gsk_... or AIza...
    re.compile(r'\b(gsk_[A-Za-z0-9]{20,})\b'),
    re.compile(r'\b(AIza[A-Za-z0-9_\-]{30,})\b'),
]


# ---------------------------------------------------------------------------
# Redaction filter
# ---------------------------------------------------------------------------

class _RedactFilter(logging.Filter):
    """Scrub API keys and tokens from log records before writing."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
            for pat in _SECRET_PATTERNS:
                msg = pat.sub(lambda m: m.group(0)[:m.start(1) - m.start(0) + len(m.group(1))] + "***REDACTED***", msg)
            # Replace the pre-formatted message so RotatingFileHandler sees it
            record.msg = msg
            record.args = ()
        except Exception:
            pass  # never let logging setup break the app
        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_setup_done = False


def setup_addon_logging(
    user_files_dir: Optional[Path] = None,
    level: int = logging.DEBUG,
) -> None:
    """Configure rotating file + console handlers for the addon.

    Call once at addon startup (idempotent — safe to call multiple times).

    Args:
        user_files_dir: Path to user_files/. Defaults to
            ``AnkiAI_ImageAddon/user_files/`` relative to this file.
        level: Log level for the file handler. Console uses WARNING.
    """
    global _setup_done
    if _setup_done:
        return

    if user_files_dir is None:
        user_files_dir = Path(__file__).parent.parent / "user_files"

    log_dir = user_files_dir / _LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _LOG_FILENAME

    root_logger = logging.getLogger("AnkiAI_ImageAddon")
    root_logger.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    redact = _RedactFilter()

    # --- Rotating file handler ---
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(redact)
        root_logger.addHandler(file_handler)
    except OSError as exc:
        # Non-fatal: log dir might not be writable in all Anki environments
        logging.getLogger(__name__).warning(
            f"Could not create log file at {log_path}: {exc}"
        )

    # --- Console handler (WARNING+ only, no redact needed for dev) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Prevent propagation to root logger (avoids duplicate Anki log spam)
    root_logger.propagate = False

    _setup_done = True
    root_logger.info("AnkiAI logging initialised → %s", log_path)


def get_log_path(user_files_dir: Optional[Path] = None) -> Path:
    """Return the expected log file path without creating anything."""
    if user_files_dir is None:
        user_files_dir = Path(__file__).parent.parent / "user_files"
    return user_files_dir / _LOG_DIR_NAME / _LOG_FILENAME
