"""
Provider registry v6.0 - domain routing and SmartImageSelector builder.
+ 21 new providers (BaseProvider interface) via adapter.
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
    KLIPYProvider,
    GIPHYProvider,
    PixabayAnimatedProvider,
    IconScoutProvider,
    HPAPIProvider,
    PotterAPIProvider,
    WaifuPicsProvider,
    NekosBestProvider,
    StudioGhibliAPIProvider,
    PokeAPIProvider,
)
from .providers.scientific import SCIENTIFIC_PRECISE_PROVIDERS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapter: wraps BaseProvider (Candidate interface) for SmartImageSelector
# ---------------------------------------------------------------------------

class _BaseProviderAdapter:
    """Wraps a BaseProvider so SmartImageSelector can call search(keyword, per_page=N)."""

    def __init__(self, provider, visual_type: str = "photo"):
        self._provider = provider
        self._visual_type = visual_type
        self.name = provider.name

    def search(self, keyword: str, per_page: int = 5):
        candidates = self._provider.search(keyword, self._visual_type, limit=per_page)
        return [c.to_dict() for c in candidates]


# ---------------------------------------------------------------------------
# Domain → provider ID mapping
# ---------------------------------------------------------------------------

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
        "klipy",
        "giphy",
        "pixabay_animated",
        "iconscout",
        "hp_api",
        "potter_api",
        "waifu_pics",
        "nekos_best",
        "studio_ghibli",
        "poke_api",
        # New providers
        "wikipedia",
        "wikidata",
        "smithsonian",
        "artic",
        "flickr_cc",
        "themealdb",
        "biodiversity",
        "iconify",
        "noun_project_new",
        "openmoji",
        "noto_emoji",
        "flagcdn",
        "gameicons",
        "openclipart",
        "mermaid",
        "quickchart",
        "storyset",
        "undraw",
        "pollinations",
        "huggingface",
    ],
    "animated": [
        "klipy",
        "giphy",
        "pixabay_animated",
        "iconscout",
        "waifu_pics",
        "nekos_best",
    ],
    "medical": ["wikimedia_smart", "wikimedia", "isic", "europe_pmc", "pubchem", "wikipedia", "biodiversity"],
    "chemistry": ["pubchem", "chembl", "wikimedia"],
    "biology": ["bioicons", "rcsb", "phylopic", "wikimedia", "pubchem", "biodiversity", "wikipedia"],
    "taxonomy": ["phylopic", "wikimedia", "biodiversity"],
    "dermatology": ["isic", "wikimedia_smart", "wikimedia"],
    "space": ["nasa", "wikimedia", "wikipedia"],
    "math": ["codecogs", "wikimedia", "mermaid", "quickchart"],
    "photo": ["wikipedia", "wikidata", "smithsonian", "artic", "flickr_cc", "themealdb", "biodiversity"],
    "icon": ["iconify", "gameicons", "openmoji", "noto_emoji", "flagcdn", "openclipart", "undraw", "noun_project_new"],
    "diagram": ["mermaid", "quickchart", "storyset", "undraw", "biodiversity"],
    "metaphor": ["storyset", "pollinations", "huggingface"],
}

FALLBACK_PROVIDERS = ["openverse", "wikimedia", "duckduckgo", "wikipedia"]
ANIMATED_FALLBACK_PROVIDERS = ["giphy", "pixabay_animated"]

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


def _try_add_base(selector: SmartImageSelector, name: str, factory, visual_type: str = "photo") -> None:
    """Register a BaseProvider via adapter so SmartImageSelector can call it."""
    try:
        provider = factory()
        if provider:
            adapter = _BaseProviderAdapter(provider, visual_type=visual_type)
            domain_tags = PROVIDER_DOMAINS.get(name, {"general"})
            selector.add_provider(name, adapter, domains=domain_tags)
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

    # ── Legacy provider keys ──
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
    klipy_key = config.get("klipy_app_key", "")
    giphy_key = config.get("giphy_api_key", "")
    if config.get("tenor_api_key"):
        logger.warning("Ignoring legacy tenor_api_key: Tenor is no longer supported")
    iconscout_token = config.get("iconscout_api_token", "")

    # ── Legacy providers (modules/providers/) ──
    if pexels_key:
        _try_add(selector, "pexels", lambda: PexelsProvider(pexels_key))
    if unsplash_key:
        _try_add(selector, "unsplash", lambda: UnsplashProvider(unsplash_key))
    if pixabay_key:
        _try_add(selector, "pixabay", lambda: PixabayProvider(pixabay_key))
    if flickr_key:
        _try_add(selector, "flickr", lambda: FlickrProvider(flickr_key))
    if google_key and google_cx:
        _try_add(selector, "google_cse", lambda: GoogleCSEProvider(google_key, google_cx))

    _try_add(selector, "duckduckgo", lambda: DuckDuckGoImagesProvider())
    _try_add(selector, "yandex", lambda: YandexImagesProvider())
    _try_add(selector, "openverse", lambda: OpenverseProvider(openverse_token))
    _try_add(selector, "wikimedia", lambda: WikimediaCommonsProvider())
    _try_add(selector, "wikimedia_smart", lambda: WikimediaSmartProvider())
    _try_add(selector, "lorem_picsum", lambda: LoremPicsumProvider())
    _try_add(selector, "loc", lambda: LibraryOfCongressProvider())
    _try_add(selector, "metmuseum", lambda: MetMuseumProvider())

    if noun_key and noun_secret:
        _try_add(selector, "noun_project", lambda: NounProjectProvider(noun_key, noun_secret))

    if europeana_key:
        _try_add(selector, "europeana", lambda: EuropeanaProvider(europeana_key))

    if klipy_key:
        _try_add(selector, "klipy", lambda: KLIPYProvider(klipy_key))
    if giphy_key:
        _try_add(selector, "giphy", lambda: GIPHYProvider(giphy_key))
    if pixabay_key:
        _try_add(selector, "pixabay_animated", lambda: PixabayAnimatedProvider(pixabay_key))
    _try_add(selector, "iconscout", lambda: IconScoutProvider(iconscout_token))

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

    # Entertainment providers (free, no API key required)
    _try_add(selector, "hp_api", lambda: HPAPIProvider())
    _try_add(selector, "potter_api", lambda: PotterAPIProvider())
    _try_add(selector, "waifu_pics", lambda: WaifuPicsProvider())
    _try_add(selector, "nekos_best", lambda: NekosBestProvider())
    _try_add(selector, "studio_ghibli", lambda: StudioGhibliAPIProvider())
    _try_add(selector, "poke_api", lambda: PokeAPIProvider())

    # ── New providers (BaseProvider interface via adapter) ──
    _cfg = config  # capture for closures

    # Static/photo providers
    _try_add_base(selector, "wikipedia", lambda: _new_provider("wikipedia", _cfg), "photo")
    _try_add_base(selector, "wikidata", lambda: _new_provider("wikidata", _cfg), "photo")
    _try_add_base(selector, "smithsonian", lambda: _new_provider("smithsonian", _cfg), "photo")
    _try_add_base(selector, "artic", lambda: _new_provider("artic", _cfg), "photo")
    _try_add_base(selector, "flickr_cc", lambda: _new_provider("flickr_cc", _cfg), "photo")
    _try_add_base(selector, "themealdb", lambda: _new_provider("themealdb", _cfg), "photo")
    _try_add_base(selector, "biodiversity", lambda: _new_provider("biodiversity", _cfg), "photo")

    # Icon providers
    _try_add_base(selector, "iconify", lambda: _new_provider("iconify", _cfg), "icon")
    _try_add_base(selector, "noun_project_new", lambda: _new_provider("noun_project", _cfg), "icon")
    _try_add_base(selector, "openmoji", lambda: _new_provider("openmoji", _cfg), "icon")
    _try_add_base(selector, "noto_emoji", lambda: _new_provider("noto_emoji", _cfg), "icon")
    _try_add_base(selector, "flagcdn", lambda: _new_provider("flagcdn", _cfg), "icon")
    _try_add_base(selector, "gameicons", lambda: _new_provider("gameicons", _cfg), "icon")
    _try_add_base(selector, "openclipart", lambda: _new_provider("openclipart", _cfg), "icon")

    # Diagram providers
    _try_add_base(selector, "mermaid", lambda: _new_provider("mermaid", _cfg), "diagram_or_map")
    _try_add_base(selector, "quickchart", lambda: _new_provider("quickchart", _cfg), "diagram_or_map")
    _try_add_base(selector, "storyset", lambda: _new_provider("storyset", _cfg), "diagram_or_map")
    _try_add_base(selector, "undraw", lambda: _new_provider("undraw", _cfg), "icon")

    # AI generation providers (chốt chặn cuối cùng — §16)
    _try_add_base(selector, "pollinations", lambda: _new_provider("pollinations", _cfg), "metaphor_photo")
    _try_add_base(selector, "huggingface", lambda: _new_provider("huggingface", _cfg), "metaphor_photo")

    if not selector.providers:
        raise ImageProviderError("No image providers configured")

    logger.info(
        f"Provider registry: {len(selector.providers)} providers registered"
    )
    return selector


# ---------------------------------------------------------------------------
# Provider factory — lazy imports to avoid circular deps
# ---------------------------------------------------------------------------

_PROVIDER_FACTORIES = None


def _ensure_factories():
    global _PROVIDER_FACTORIES
    if _PROVIDER_FACTORIES is not None:
        return

    from AnkiAI_ImageAddon.image_providers.static.wikipedia_provider import WikipediaProvider
    from AnkiAI_ImageAddon.image_providers.static.wikidata_provider import WikidataProvider
    from AnkiAI_ImageAddon.image_providers.static.smithsonian_provider import SmithsonianProvider
    from AnkiAI_ImageAddon.image_providers.static.art_museum_provider import ArtMuseumProvider
    from AnkiAI_ImageAddon.image_providers.static.flickr_provider import NewFlickrProvider
    from AnkiAI_ImageAddon.image_providers.static.themealdb_provider import TheMealDBProvider
    from AnkiAI_ImageAddon.image_providers.static.biodiversity_provider import BiodiversityProvider
    from AnkiAI_ImageAddon.image_providers.icon.iconify_provider import IconifyProvider
    from AnkiAI_ImageAddon.image_providers.icon.noun_project_provider import NewNounProjectProvider
    from AnkiAI_ImageAddon.image_providers.icon.openmoji_provider import OpenMojiProvider
    from AnkiAI_ImageAddon.image_providers.icon.noto_emoji_provider import NotoEmojiProvider
    from AnkiAI_ImageAddon.image_providers.icon.flagcdn_provider import FlagCDNProvider
    from AnkiAI_ImageAddon.image_providers.icon.gameicons_provider import GameIconsProvider
    from AnkiAI_ImageAddon.image_providers.icon.openclipart_provider import OpenclipartProvider
    from AnkiAI_ImageAddon.image_providers.diagram.mermaid_provider import MermaidProvider
    from AnkiAI_ImageAddon.image_providers.diagram.quickchart_provider import QuickChartProvider
    from AnkiAI_ImageAddon.image_providers.diagram.storyset_provider import StorysetProvider
    from AnkiAI_ImageAddon.image_providers.diagram.undraw_provider import UnDrawProvider
    from AnkiAI_ImageAddon.image_providers.ai_generation.pollinations_provider import PollinationsProvider
    from AnkiAI_ImageAddon.image_providers.ai_generation.huggingface_provider import HuggingFaceProvider

    _PROVIDER_FACTORIES = {
        "wikipedia": WikipediaProvider,
        "wikidata": WikidataProvider,
        "smithsonian": SmithsonianProvider,
        "artic": ArtMuseumProvider,
        "flickr_cc": NewFlickrProvider,
        "themealdb": TheMealDBProvider,
        "biodiversity": BiodiversityProvider,
        "iconify": IconifyProvider,
        "noun_project": NewNounProjectProvider,
        "openmoji": OpenMojiProvider,
        "noto_emoji": NotoEmojiProvider,
        "flagcdn": FlagCDNProvider,
        "gameicons": GameIconsProvider,
        "openclipart": OpenclipartProvider,
        "mermaid": MermaidProvider,
        "quickchart": QuickChartProvider,
        "storyset": StorysetProvider,
        "undraw": UnDrawProvider,
        "pollinations": PollinationsProvider,
        "huggingface": HuggingFaceProvider,
    }


def _new_provider(name: str, config: Dict[str, Any]):
    """Instantiate a new BaseProvider by name."""
    _ensure_factories()
    cls = _PROVIDER_FACTORIES.get(name)
    if cls is None:
        logger.warning(f"Unknown new provider: {name}")
        return None
    return cls(config=config)


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
            "klipy_app_key",
            "giphy_api_key",
            "iconscout_api_token",
            "huggingface_api_token",
        )
    )
    return keyed or True  # free providers always available


def has_any_animated_provider(config: Dict[str, Any]) -> bool:
    """True if at least one animated provider is configured."""
    return any(
        config.get(k)
        for k in (
            "klipy_app_key",
            "giphy_api_key",
            "pixabay_api_key",
            "iconscout_api_token",
        )
    )


# ---------------------------------------------------------------------------
# Provider chains per word group (§4.2 Integration Spec)
# ---------------------------------------------------------------------------

PROVIDER_CHAINS: Dict[str, List[str]] = {
    "A": ["wikipedia", "wikidata", "flickr_cc", "pixabay", "pexels"],
    "B": ["wikipedia", "wikidata", "flickr_cc", "pixabay", "pexels"],
    "C": ["wikipedia", "flagcdn", "smithsonian", "artic", "wikidata"],
    "D": ["biodiversity", "smithsonian", "wikipedia", "wikimedia"],
    "E": ["storyset", "pollinations", "huggingface"],
    "F": ["mermaid", "quickchart", "storyset", "wikimedia"],
    "G": ["klipy", "giphy", "pixabay_animated"],
    "H": ["iconify", "gameicons", "noun_project_new", "iconscout"],
    "I": ["pixabay", "pexels", "flickr_cc", "wikipedia"],
    "J": ["storyset", "pollinations", "huggingface"],
    "K": ["svg_engine"],
    "L": ["storyset", "openverse", "giphy", "pollinations"],
    "M": [],
    "N": ["svg_engine", "quickchart", "pubchem"],
}
