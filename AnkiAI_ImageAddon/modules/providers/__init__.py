"""Image provider implementations v5.0 - 20+ sources with domain routing."""

from .base import ImageProviderError, _ImageProviderSessionManager, WIKIMEDIA_HEADERS
from .wikimedia import WikimediaCommonsProvider, WikimediaSmartProvider
from .legacy_free import (
    PexelsProvider,
    UnsplashProvider,
    OpenverseProvider,
    LoremPicsumProvider,
    LibraryOfCongressProvider,
    MetMuseumProvider,
    EuropeanaProvider,
)
from .general import (
    PixabayProvider,
    FlickrProvider,
    GoogleCSEProvider,
    DuckDuckGoImagesProvider,
    YandexImagesProvider,
    NounProjectProvider,
)
from .scientific import (
    PubChemProvider,
    ChEMBLProvider,
    RCSBProvider,
    PhyloPicProvider,
    ISICProvider,
    EuropePMCProvider,
    NASAImagesProvider,
    CodeCogsProvider,
    BioiconsProvider,
)
from .animated import (
    KLIPYProvider,
    GIPHYProvider,
    PixabayAnimatedProvider,
    IconScoutProvider,
)
from .entertainment import (
    HPAPIProvider,
    PotterAPIProvider,
    WaifuPicsProvider,
    NekosBestProvider,
    StudioGhibliAPIProvider,
    PokeAPIProvider,
)

__all__ = [
    "ImageProviderError",
    "_ImageProviderSessionManager",
    "WikimediaCommonsProvider",
    "WikimediaSmartProvider",
    "PexelsProvider",
    "UnsplashProvider",
    "OpenverseProvider",
    "LoremPicsumProvider",
    "LibraryOfCongressProvider",
    "MetMuseumProvider",
    "EuropeanaProvider",
    "PixabayProvider",
    "FlickrProvider",
    "GoogleCSEProvider",
    "DuckDuckGoImagesProvider",
    "YandexImagesProvider",
    "NounProjectProvider",
    "PubChemProvider",
    "ChEMBLProvider",
    "RCSBProvider",
    "PhyloPicProvider",
    "ISICProvider",
    "EuropePMCProvider",
    "NASAImagesProvider",
    "CodeCogsProvider",
    "BioiconsProvider",
    "KLIPYProvider",
    "GIPHYProvider",
    "PixabayAnimatedProvider",
    "IconScoutProvider",
    "HPAPIProvider",
    "PotterAPIProvider",
    "WaifuPicsProvider",
    "NekosBestProvider",
    "StudioGhibliAPIProvider",
    "PokeAPIProvider",
]
