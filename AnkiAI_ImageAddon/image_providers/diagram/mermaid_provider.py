"""
MermaidProvider — diagram generation via Mermaid.js           [MS §17.2]
=========================================================================
Generates diagram URLs using the Mermaid.ink rendering service.
No API key required; constructs a URL from Mermaid code and encodes it
as base64 in the path.

Templates:
  - flowchart  → keywords: flow, process, workflow, algorithm, steps
  - sequence   → keywords: sequence, interaction, message, conversation
  - class      → keywords: class, object, structure, hierarchy, OOP

License: MIT (Mermaid.js)
Rate:    Unlimited
"""

from __future__ import annotations

import base64
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


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------

_FLOWCHART_KEYWORDS = {
    "flow", "process", "workflow", "algorithm", "steps", "procedure",
    "loop", "decision", "branch", "pipeline",
}
_SEQUENCE_KEYWORDS = {
    "sequence", "interaction", "message", "conversation", "protocol",
    "request", "response", "communication", "exchange",
}
_CLASS_KEYWORDS = {
    "class", "object", "structure", "hierarchy", "oop", "inheritance",
    "interface", "composition", "pattern",
}


def _pick_template(query: str) -> str:
    """Choose a Mermaid template type based on keyword matching."""
    lowered = query.lower()
    words = set(lowered.split())

    if words & _SEQUENCE_KEYWORDS:
        return "sequence"
    if words & _CLASS_KEYWORDS:
        return "class"
    # Default to flowchart (most broadly applicable)
    return "flowchart"


def _build_mermaid_code(query: str, template: str) -> str:
    """Build Mermaid.js code from the query and chosen template."""
    # Sanitize label: strip chars that break Mermaid syntax
    label = query.replace('"', "'").replace("\n", " ").strip()
    if not label:
        label = "Diagram"

    if template == "sequence":
        return (
            f'sequenceDiagram\n'
            f'    participant A as {label} (Sender)\n'
            f'    participant B as {label} (Receiver)\n'
            f'    A->>B: Request\n'
            f'    B-->>A: Response\n'
            f'    A->>B: Confirmation\n'
        )
    if template == "class":
        return (
            f'classDiagram\n'
            f'    class {label.replace(" ", "")} {{\n'
            f'        +attribute: string\n'
            f'        +method(): void\n'
            f'    }}\n'
            f'    class Related {{\n'
            f'        +data: int\n'
            f'    }}\n'
            f'    {label.replace(" ", "")} --> Related\n'
        )
    # flowchart (default)
    return (
        f'flowchart TD\n'
        f'    A[{label}] --> B{{Decision}}\n'
        f'    B -->|Yes| C[Result 1]\n'
        f'    B -->|No| D[Result 2]\n'
        f'    C --> E[End]\n'
        f'    D --> E\n'
    )


class MermaidProvider(BaseProvider):
    """Generates diagram image URLs via the Mermaid.ink rendering service."""

    name = "mermaid"

    # visual types this provider can handle
    SUPPORTED_VISUAL_TYPES = {"diagram_or_map"}

    def __init__(self, config: Dict[str, Any] = None):
        self._config = config or {}
        self._base_url = self._config.get("mermaid_base_url", "https://mermaid.ink")
        self._timeout = self._config.get("provider_timeout_s", 10)
        self._session = requests.Session()
        self._session.timeout = self._timeout

    def search(
        self,
        query: str,
        visual_type: str = "diagram_or_map",
        limit: int = 10,
    ) -> List[Candidate]:
        """Generate a Mermaid diagram URL from the query.

        This is a *generation* provider — it constructs a URL, it does not
        search an API.  No QuotaManager check is needed (unlimited rate).

        Args:
            query:       Description of the diagram to generate.
            visual_type: Must be "diagram_or_map".
            limit:       Max candidates (at most 1 is returned).

        Returns:
            List with one Candidate whose url is a Mermaid.ink image URL,
            or empty list on error.
        """
        t0 = time.perf_counter()
        ok = False
        try:
            if visual_type not in self.SUPPORTED_VISUAL_TYPES:
                return []

            template = _pick_template(query)
            mermaid_code = _build_mermaid_code(query, template)

            # Encode: Mermaid.ink expects base64 of the source in the URL path
            encoded = base64.urlsafe_b64encode(
                mermaid_code.encode("utf-8")
            ).decode("ascii")
            image_url = f"{self._base_url}/img/{encoded}?type=svg"

            candidate = Candidate(
                url=image_url,
                provider=self.name,
                visual_type=visual_type,
                width=0,  # SVG — dimensions determined by renderer
                height=0,
                license="MIT",
                attribution="Mermaid.js (https://mermaid.js.org)",
                title=f"{query} ({template})",
                score=0.8,
            )
            ok = True
            return [candidate]

        except Exception:
            logger.exception("MermaidProvider: error generating diagram for '%s'", query)
            return []

        finally:
            latency = time.perf_counter() - t0
            _get_health().report(self.name, latency, ok)
