"""Debug session logging (NDJSON)."""
import json
import os
import time

_LOG_PATH = "/Users/nguyenkhanh/Desktop/AnkiAI-ImageAddon/.cursor/debug-7814f7.log"
_SESSION = "7814f7"


def dbg(location: str, message: str, data: dict, hypothesis_id: str, run_id: str = "pre-fix"):
    # #region agent log
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        entry = {
            "sessionId": _SESSION,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # #endregion
