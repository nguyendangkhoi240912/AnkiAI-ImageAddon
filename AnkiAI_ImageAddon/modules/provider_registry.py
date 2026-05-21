"""
Provider registry v5.0 - domain routing and SmartImageSelector builder.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from .image_providers import SmartImageSelector, ImageProviderError
from .providers import (
    PexelsProvider,
    UnsplashProvider,
    OpenverseProvider,
    LoremPicsumProvider,
    LibraryOfCongressProvider,
    MetMuseumProvider,
    EuropeanaProvider,
    WikimediaCommonsProvider,
    WikimediaSmartProvider,
    PixabayProvider,
    FlickrProvider,
    GoogleCSEProvider,
    DuckDuckGoImagesProvider,
    YandexImagesProvider,
    NounProjectProvider,
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
from .providers.scientific import SCIENTIFIC_PRECISE_PROVIDERS

logger = logging.getLogger(__name__)

# Which provider IDs are active for each AI-routed domain
DOMAIN_PROVIDERS: Dict[str, List[str]] = {
    "general": [
        "pexels",
        "unsplash",
        "pixabay",
        "flickr",
        "google_cse",
        "duckduckgo",
        "yandex",
        "openverse",
        "wikimedia",
        "noun_project",
        "lorem_picsum",
        "loc",
        "metmuseum",
        "europeana",
    ],
    "medical": ["wikimedia_smart", "wikimedia", "isic", "europe_pmc", "pubchem"],
    "chemistry": ["pubchem", "chembl", "wikimedia"],
    "biology": ["bioicons", "rcsb", "phylopic", "wikimedia", "pubchem"],
    "taxonomy": ["phylopic", "wikimedia"],
    "dermatology": ["isic", "wikimedia_smart", "wikimedia"],
    "space": ["nasa", "wikimedia"],
    "math": ["codecogs", "wikimedia"],
}

FALLBACK_PROVIDERS = ["openverse", "wikimedia", "duckduckgo"]

VALID_DOMAINS = set(DOMAIN_PROVIDERS.keys())


def resolve_domains(
    primary_domain: str,
    enable_routing: bool = True,
    include_general_fallback: bool = False,
) -> Set[str]:
    """Map primary domain to provider domain tags for filtering."""
    if not enable_routing or primary_domain not in VALID_DOMAINS:
        return set(DOMAIN_PROVIDERS.keys())
    if primary_domain == "general":
        return {"general"}
    domains = {primary_domain}
    if primary_domain in ("dermatology", "medical"):
        domains.add("medical")
    if primary_domain == "biology":
        domains.add("taxonomy")
    if include_general_fallback:
        domains.add("general")
    return domains


def get_provider_ids_for_domains(domains: Set[str]) -> Set[str]:
    """Union of provider IDs across domain keys."""
    ids: Set[str] = set()
    for domain in domains:
        ids.update(DOMAIN_PROVIDERS.get(domain, []))
    return ids


def _try_add(selector: SmartImageSelector, name: str, factory) -> None:
    try:
        provider = factory()
        if provider:
            domain_tags = PROVIDER_DOMAINS.get(name, {"general"})
            selector.add_provider(name, provider, domains=domain_tags)
    except Exception as e:
        logger.warning(f"{name} init failed: {e}")


# Provider name -> domain tags (for filtering)
PROVIDER_DOMAINS: Dict[str, Set[str]] = {}
for _domain, _ids in DOMAIN_PROVIDERS.items():
    for _pid in _ids:
        PROVIDER_DOMAINS.setdefault(_pid, set()).add(_domain)


def build_smart_selector(
    config: Dict[str, Any],
    enable_adaptive_delay: bool = True,
    base_delay_ms: int = 100,
    max_delay_ms: int = 2000,
) -> SmartImageSelector:
    """Build SmartImageSelector with all configured providers."""
    max_workers = config.get("max_concurrent_providers", 10)
    selector = SmartImageSelector(
        max_workers=max_workers,
        enable_adaptive_delay=enable_adaptive_delay,
        base_delay_ms=base_delay_ms,
        max_delay_ms=max_delay_ms,
    )

    pexels_key = config.get("pexels_api_key", "")
    unsplash_key = config.get("unsplash_api_key", "")
    pixabay_key = config.get("pixabay_api_key", "")
    flickr_key = config.get("flickr_api_key", "")
    google_key = config.get("google_api_key", "")
    google_cx = config.get("google_cx", "")
    europeana_key = config.get("europeana_api_key", "")
    noun_key = config.get("noun_project_api_key", "")
    noun_secret = config.get("noun_project_api_secret", "")
    openverse_token = config.get("openverse_api_token", "")

    if pexels_key:
        _try_add(selector, "pexels", lambda: PexelsProvider(pexels_key))
    if unsplash_key:
        _try_add(selector, "unsplash", lambda: UnsplashProvider(unsplash_key))
    if pixabay_key:
        _try_add(selector, "pixabay", lambda: PixabayProvider(pixabay_key))
    if flickr_key:
        _try_add(selector, "flickr", lambda: FlickrProvider(flickr_key))
    if google_key and google_cx:
        _try_add(
            selector,
            "google_cse",
            lambda: GoogleCSEProvider(google_key, google_cx),
        )

    _try_add(selector, "duckduckgo", lambda: DuckDuckGoImagesProvider())
    _try_add(selector, "yandex", lambda: YandexImagesProvider())
    _try_add(
        selector,
        "openverse",
        lambda: OpenverseProvider(openverse_token),
    )
    _try_add(selector, "wikimedia", lambda: WikimediaCommonsProvider())
    _try_add(selector, "wikimedia_smart", lambda: WikimediaSmartProvider())
    _try_add(selector, "lorem_picsum", lambda: LoremPicsumProvider())
    _try_add(selector, "loc", lambda: LibraryOfCongressProvider())
    _try_add(selector, "metmuseum", lambda: MetMuseumProvider())

    if noun_key and noun_secret:
        _try_add(
            selector,
            "noun_project",
            lambda: NounProjectProvider(noun_key, noun_secret),
        )

    if europeana_key:
        _try_add(selector, "europeana", lambda: EuropeanaProvider(europeana_key))

    # Scientific (always registered; filtered by AI routing)
    _try_add(selector, "pubchem", lambda: PubChemProvider())
    _try_add(selector, "chembl", lambda: ChEMBLProvider())
    _try_add(selector, "rcsb", lambda: RCSBProvider())
    _try_add(selector, "phylopic", lambda: PhyloPicProvider())
    _try_add(selector, "isic", lambda: ISICProvider())
    _try_add(selector, "europe_pmc", lambda: EuropePMCProvider())
    _try_add(selector, "nasa", lambda: NASAImagesProvider())
    _try_add(selector, "codecogs", lambda: CodeCogsProvider())
    _try_add(selector, "bioicons", lambda: BioiconsProvider())

    if not selector.providers:
        raise ImageProviderError("No image providers configured")

    logger.info(
        f"Provider registry: {len(selector.providers)} providers registered"
    )
    return selector


def has_any_image_provider(config: Dict[str, Any]) -> bool:
    """True if at least one keyed or free provider is available."""
    keyed = any(
        config.get(k)
        for k in (
            "pexels_api_key",
            "unsplash_api_key",
            "pixabay_api_key",
            "flickr_api_key",
            "google_api_key",
            "europeana_api_key",
            "noun_project_api_key",
        )
    )
    return keyed or True  # free providers always available
