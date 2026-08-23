"""
QuickChartProvider — chart generation via QuickChart.io         [MS §17.2]
=========================================================================
Generates chart image URLs using the QuickChart rendering service.
Creates a Chart.js configuration from the query, encodes it as a URL
parameter, and returns a Candidate with the resulting image URL.

License: MIT (QuickChart)
Rate:    1000 req/month (free tier)
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List
from urllib.parse import quote

import requests

from ..base_provider import BaseProvider, Candidate

logger = logging.getLogger(__name__)

USER_FILES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "user_files"
)


def _get_health():
    from ..health import get_health_board
    return get_health_board()


def _get_quota():
    from ...modules.quota import get_quota_manager
    return get_quota_manager()


# ---------------------------------------------------------------------------
# Chart config builder
# ---------------------------------------------------------------------------

_CHART_KEYWORDS = {
    "pie": {"pie", "percentage", "share", "proportion", "slice"},
    "doughnut": {"doughnut", "donut", "ring"},
    "bar": {"bar", "column", "compare", "comparison", "versus", "vs"},
    "line": {"line", "trend", "over time", "growth", "decline", "progress"},
    "radar": {"radar", "spider", "web", "dimensions"},
    "polarArea": {"polar", "area"},
}


def _pick_chart_type(query: str) -> str:
    """Choose a Chart.js chart type based on keyword matching."""
    lowered = query.lower()
    words = set(lowered.split())

    for chart_type, keywords in _CHART_KEYWORDS.items():
        if words & keywords:
            return chart_type

    # Default to bar chart (most broadly useful)
    return "bar"


def _build_chart_config(query: str, chart_type: str) -> Dict[str, Any]:
    """Build a Chart.js configuration dict from the query."""
    label = query.strip() or "Data"

    if chart_type in ("pie", "doughnut", "polarArea"):
        return {
            "type": chart_type,
            "data": {
                "labels": [f"Segment {i+1}" for i in range(5)],
                "datasets": [{
                    "label": label,
                    "data": [30, 25, 20, 15, 10],
                    "backgroundColor": [
                        "#4CAF50", "#2196F3", "#FF9800", "#9C27B0", "#F44336"
                    ],
                }],
            },
            "options": {
                "plugins": {
                    "title": {"display": True, "text": label},
                },
            },
        }

    if chart_type == "line":
        return {
            "type": "line",
            "data": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "datasets": [{
                    "label": label,
                    "data": [10, 25, 20, 35, 30, 45],
                    "borderColor": "#2196F3",
                    "fill": False,
                }],
            },
            "options": {
                "plugins": {
                    "title": {"display": True, "text": label},
                },
            },
        }

    if chart_type == "radar":
        return {
            "type": "radar",
            "data": {
                "labels": ["Speed", "Reliability", "Comfort", "Safety", "Efficiency"],
                "datasets": [{
                    "label": label,
                    "data": [70, 85, 60, 90, 75],
                    "borderColor": "#2196F3",
                    "backgroundColor": "rgba(33,150,243,0.2)",
                }],
            },
            "options": {
                "plugins": {
                    "title": {"display": True, "text": label},
                },
            },
        }

    # bar (default)
    return {
        "type": "bar",
        "data": {
            "labels": ["A", "B", "C", "D", "E"],
            "datasets": [{
                "label": label,
                "data": [12, 19, 8, 15, 10],
                "backgroundColor": "#2196F3",
            }],
        },
        "options": {
            "plugins": {
                "title": {"display": True, "text": label},
            },
        },
    }


class QuickChartProvider(BaseProvider):
    """Generates chart image URLs via the QuickChart.io rendering service."""

    name = "quickchart"

    SUPPORTED_VISUAL_TYPES = {"diagram_or_map"}

    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._base_url = self._config.get(
            "quickchart_base_url", "https://quickchart.io"
        )
        self._chart_width = self._config.get("chart_width", 500)
        self._chart_height = self._config.get("chart_height", 300)
        self._timeout = self._config.get("provider_timeout_s", 10)
        self._session = requests.Session()
        self._session.timeout = self._timeout

    def search(
        self,
        query: str,
        visual_type: str = "diagram_or_map",
        limit: int = 10,
    ) -> List[Candidate]:
        """Generate a chart image URL from the query.

        This is a *generation* provider — it constructs a Chart.js config
        and encodes it as a QuickChart URL parameter.

        QuotaManager is checked before generating (1000 req/month free tier).

        Args:
            query:       Description of the chart to generate.
            visual_type: Must be "diagram_or_map".
            limit:       Max candidates (at most 1 is returned).

        Returns:
            List with one Candidate whose url is a QuickChart image URL,
            or empty list on error or quota exhaustion.
        """
        t0 = time.perf_counter()
        ok = False
        try:
            if visual_type not in self.SUPPORTED_VISUAL_TYPES:
                return []

            # QuotaManager check — free tier is limited
            quota = _get_quota()
            if not quota.allow("quickchart"):
                logger.info("QuickChartProvider: quota exhausted, skipping")
                return []

            chart_type = _pick_chart_type(query)
            chart_config = _build_chart_config(query, chart_type)
            config_json = json.dumps(chart_config, separators=(",", ":"))

            # Build URL: encode the Chart.js config as a query parameter
            encoded_config = quote(config_json, safe="")
            image_url = (
                f"{self._base_url}/chart"
                f"?c={encoded_config}"
                f"&w={self._chart_width}"
                f"&h={self._chart_height}"
            )

            # Record quota usage
            quota.record("quickchart", tokens=0)

            candidate = Candidate(
                url=image_url,
                provider=self.name,
                visual_type=visual_type,
                width=self._chart_width,
                height=self._chart_height,
                license="MIT",
                attribution="QuickChart (https://quickchart.io)",
                title=f"{query} ({chart_type} chart)",
                score=0.75,
            )
            ok = True
            return [candidate]

        except Exception:
            logger.exception("QuickChartProvider: error generating chart for '%s'", query)
            return []

        finally:
            latency = time.perf_counter() - t0
            _get_health().report(self.name, latency, ok)
