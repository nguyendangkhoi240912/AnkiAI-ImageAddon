"""Optional NDJSON debug logging (off by default)."""
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

_ENABLED = False
_LOG_PATH: Optional[str] = None
_SESSION = "ankiai"


def _addon_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_log_path() -> str:
    return os.path.join(_addon_root(), "logs", "agent-debug.ndjson")


def configure(
    enabled: bool = False,
    log_path: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Enable or disable agent debug logging."""
    global _ENABLED, _LOG_PATH, _SESSION
    _ENABLED = bool(enabled)
    _LOG_PATH = log_path or default_log_path()
    if session_id:
        _SESSION = session_id


def is_enabled() -> bool:
    return _ENABLED


def dbg(
    location: str,
    message: str,
    data: dict,
    hypothesis_id: str,
    run_id: str = "default",
) -> None:
    if not _ENABLED:
        return

    path = _LOG_PATH or default_log_path()
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        entry = {
            "sessionId": _SESSION,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.debug("agent debug log write failed: %s", e)
