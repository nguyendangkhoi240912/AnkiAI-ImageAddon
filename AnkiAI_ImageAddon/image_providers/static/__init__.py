"""Static image providers package."""

from ...modules.providers.general import (
    PixabayProvider,
    GoogleCSEProvider,
    DuckDuckGoImagesProvider,
    YandexImagesProvider,
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

# New providers (BaseProvider interface)
from .wikipedia_provider import WikipediaProvider
from .wikidata_provider import WikidataProvider
from .smithsonian_provider import SmithsonianProvider
from .art_museum_provider import ArtMuseumProvider
from .flickr_provider import NewFlickrProvider
from .themealdb_provider import TheMealDBProvider
from .biodiversity_provider import BiodiversityProvider

__all__ = [
    # Legacy (modules/providers/)
    "PixabayProvider",
    "GoogleCSEProvider",
    "DuckDuckGoImagesProvider",
    "YandexImagesProvider",
    "PexelsProvider",
    "UnsplashProvider",
    "OpenverseProvider",
    "LoremPicsumProvider",
    "LibraryOfCongressProvider",
    "MetMuseumProvider",
    "EuropeanaProvider",
    # New (BaseProvider interface)
    "WikipediaProvider",
    "WikidataProvider",
    "SmithsonianProvider",
    "ArtMuseumProvider",
    "NewFlickrProvider",
    "TheMealDBProvider",
    "BiodiversityProvider",
]
