"""Base provider interface and candidate contract for AnkiAI ImageAddon.

Defines the core Candidate dataclass and BaseProvider abstract base class
according to Master Spec v9 §17.2.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Candidate:
    """Represents a candidate image found by any provider."""
    url: str
    provider: str
    visual_type: str
    width: int = 0
    height: int = 0
    license: str = "unknown"
    attribution: str = ""
    title: str = ""
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert Candidate to dict for backwards compatibility with legacy code."""
        return {
            "url": self.url,
            "provider": self.provider,
            "visual_type": self.visual_type,
            "width": self.width,
            "height": self.height,
            "license": self.license,
            "attribution": self.attribution,
            "title": self.title,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_visual_type: str = "photo") -> "Candidate":
        """Create Candidate from a legacy result dict."""
        return cls(
            url=data.get("url", ""),
            provider=data.get("provider", "unknown"),
            visual_type=data.get("visual_type", default_visual_type),
            width=int(data.get("width", 0)),
            height=int(data.get("height", 0)),
            license=data.get("license", "unknown"),
            attribution=data.get("attribution", ""),
            title=data.get("title", ""),
            score=float(data.get("score", 0.0)),
        )


class ImageProviderError(Exception):
    """Exception raised by image providers on network/parsing failure."""
    pass


class BaseProvider(ABC):
    """Abstract base class that all image providers must implement."""

    name: str = "base"

    @abstractmethod
    def search(
        self,
        query: str,
        visual_type: str = "photo",
        limit: int = 10,
    ) -> List[Candidate]:
        """Search for candidate images matching query and visual_type.

        Args:
            query: Search query string.
            visual_type: Target visual type (photo, gif, icon, diagram_or_map, metaphor_photo, local_svg).
            limit: Maximum number of candidates to return.

        Returns:
            List of Candidate objects.
        """
        pass
