"""Static image providers package."""

from ...modules.providers.general import (
    PixabayProvider,
    FlickrProvider,
    GoogleCSEProvider,
    DuckDuckGoImagesProvider,
    YandexImagesProvider,
    NounProjectProvider,
)
from ...modules.providers.legacy_free import (
    PexelsProvider,
    UnsplashProvider,
    OpenverseProvider,
    LoremPicsumProvider,
    LibraryOfCongressProvider,
    MetMuseumProvider,
    EuropeanaProvider,
)

__all__ = [
    "PixabayProvider",
    "FlickrProvider",
    "GoogleCSEProvider",
    "DuckDuckGoImagesProvider",
    "YandexImagesProvider",
    "NounProjectProvider",
    "PexelsProvider",
    "UnsplashProvider",
    "OpenverseProvider",
    "LoremPicsumProvider",
    "LibraryOfCongressProvider",
    "MetMuseumProvider",
    "EuropeanaProvider",
]
