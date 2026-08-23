"""Icon image providers package."""

from .iconify_provider import IconifyProvider
from .noun_project_provider import NewNounProjectProvider
from .openmoji_provider import OpenMojiProvider
from .noto_emoji_provider import NotoEmojiProvider
from .flagcdn_provider import FlagCDNProvider
from .gameicons_provider import GameIconsProvider
from .openclipart_provider import OpenclipartProvider

__all__ = [
    "IconifyProvider",
    "NewNounProjectProvider",
    "OpenMojiProvider",
    "NotoEmojiProvider",
    "FlagCDNProvider",
    "GameIconsProvider",
    "OpenclipartProvider",
]
