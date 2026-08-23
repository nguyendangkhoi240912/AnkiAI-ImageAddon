"""
Contract tests for 21 new providers — §10.1 Integration Spec
=============================================================
Every provider must:
  - Inherit from BaseProvider
  - Implement search() → List[Candidate]
  - Return valid visual_type (one of 7 per §6)
  - Not use asyncio
  - Return [] on error (never crash)
  - Have correct name attribute
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add addon source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AnkiAI_ImageAddon.image_providers.base_provider import BaseProvider, Candidate

# Valid visual types per §6
VALID_VISUAL_TYPES = {"photo", "gif", "icon", "diagram_or_map", "metaphor_photo", "local_svg", "none"}


# ── Fixtures: mock quota & health to avoid full Anki stack ──

@pytest.fixture(autouse=True)
def mock_quota_and_health(monkeypatch):
    """Patch QuotaManager and HealthBoard so providers can init without Anki."""
    mock_quota = MagicMock()
    mock_quota.allow.return_value = True
    mock_quota.record = MagicMock()
    mock_quota.degrade_level.return_value = 0

    mock_health = MagicMock()
    mock_health.report = MagicMock()

    # Patch lazy getters in each provider module
    # We patch at the module level after import
    monkeypatch.setattr(
        "AnkiAI_ImageAddon.modules.quota.get_quota_manager",
        lambda config=None: mock_quota,
    )
    monkeypatch.setattr(
        "AnkiAI_ImageAddon.image_providers.health.get_health_board",
        lambda: mock_health,
    )


def _make_mock_session(json_data=None, content_data=None, raise_error=None):
    """Create a mock requests.Session for provider tests."""
    mock_session = MagicMock()
    mock_resp = MagicMock()
    if json_data is not None:
        mock_resp.json.return_value = json_data
    if content_data is not None:
        mock_resp.content = content_data
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 200
    if raise_error:
        mock_session.get.side_effect = raise_error
        mock_session.post.side_effect = raise_error
    else:
        mock_session.get.return_value = mock_resp
        mock_session.post.return_value = mock_resp
    return mock_session


# ══════════════════════════════════════════════════════════
# Static providers
# ══════════════════════════════════════════════════════════

class TestWikipediaProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.wikipedia_provider import WikipediaProvider
        p = WikipediaProvider(config={})
        return p

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "wikipedia"

    def test_returns_empty_on_error(self, provider):
        provider.session = _make_mock_session(raise_error=Exception("fail"))
        results = provider.search("test", "photo")
        assert results == []

    def test_search_returns_candidates(self, provider):
        mock_resp_search = MagicMock()
        mock_resp_search.json.return_value = {"query": {"search": [{"title": "Cat", "pageid": 123}]}}
        mock_resp_search.raise_for_status = MagicMock()
        mock_resp_summary = MagicMock()
        mock_resp_summary.json.return_value = {
            "title": "Cat",
            "thumbnail": {"source": "https://example.com/cat.jpg", "width": 300, "height": 200},
        }
        mock_resp_summary.raise_for_status = MagicMock()
        provider.session = MagicMock()
        provider.session.get.side_effect = [mock_resp_search, mock_resp_summary]
        results = provider.search("cat", "photo", limit=5)
        assert len(results) >= 1
        assert all(isinstance(c, Candidate) for c in results)
        assert all(c.visual_type in VALID_VISUAL_TYPES for c in results)
        assert all(c.provider == "wikipedia" for c in results)


class TestWikidataProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.wikidata_provider import WikidataProvider
        return WikidataProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "wikidata"

    def test_returns_empty_on_error(self, provider):
        provider.session = _make_mock_session(raise_error=Exception("fail"))
        assert provider.search("test", "photo") == []


class TestSmithsonianProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.smithsonian_provider import SmithsonianProvider
        return SmithsonianProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "smithsonian"


class TestArtMuseumProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.art_museum_provider import ArtMuseumProvider
        return ArtMuseumProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "artic"


class TestNewFlickrProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.flickr_provider import NewFlickrProvider
        return NewFlickrProvider(config={"flickr_api_key": "test_key"})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "flickr_cc"

    def test_returns_empty_without_key(self):
        from AnkiAI_ImageAddon.image_providers.static.flickr_provider import NewFlickrProvider
        p = NewFlickrProvider(config={})
        assert p.search("test", "photo") == []


class TestTheMealDBProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.themealdb_provider import TheMealDBProvider
        return TheMealDBProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "themealdb"

    def test_search_mock(self, provider):
        provider.session = _make_mock_session(json_data={
            "meals": [{"strMeal": "Sushi", "strMealThumb": "https://example.com/sushi.jpg", "strArea": "Japanese"}]
        })
        results = provider.search("sushi", "photo", limit=5)
        assert len(results) >= 1
        assert results[0].license == "CC-BY"


class TestBiodiversityProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.static.biodiversity_provider import BiodiversityProvider
        return BiodiversityProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "biodiversity"


# ══════════════════════════════════════════════════════════
# Icon providers
# ══════════════════════════════════════════════════════════

class TestIconifyProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.icon.iconify_provider import IconifyProvider
        return IconifyProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "iconify"


class TestNewNounProjectProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.icon.noun_project_provider import NewNounProjectProvider
        return NewNounProjectProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "noun_project"


class TestOpenMojiProvider:
    @pytest.fixture
    def provider(self, tmp_path):
        from AnkiAI_ImageAddon.image_providers.icon.openmoji_provider import OpenMojiProvider
        # Point index to temp dir to avoid downloading
        cfg = {}
        p = OpenMojiProvider(config=cfg)
        # Pre-populate a minimal index
        p.index = [{"name": "grinning face", "hexcode": "1F600", "annotation": "grinning"}]
        return p

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "openmoji"

    def test_search_local(self, provider):
        results = provider.search("grinning", "icon", limit=5)
        assert len(results) >= 1
        assert all(c.visual_type == "icon" for c in results)


class TestNotoEmojiProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.icon.noto_emoji_provider import NotoEmojiProvider
        p = NotoEmojiProvider(config={})
        p.index = [{"name": "grinning face", "hexcode": "1F600", "annotation": "grinning"}]
        return p

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "noto_emoji"


class TestFlagCDNProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.icon.flagcdn_provider import FlagCDNProvider
        p = FlagCDNProvider(config={})
        # Pre-load index so search doesn't hit real API
        p._index = {"us": {"name": "United States"}, "vn": {"name": "Vietnam"}, "fr": {"name": "France"}}
        return p

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "flagcdn"

    def test_search_local(self, provider):
        results = provider.search("France", "icon", limit=5)
        assert len(results) >= 1
        assert results[0].url == "https://flagcdn.com/fr.svg"
        assert results[0].visual_type == "icon"


class TestGameIconsProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.icon.gameicons_provider import GameIconsProvider
        p = GameIconsProvider(config={})
        # Pre-load index so search doesn't hit real API
        p._index = [{"name": "sword", "path": "sword", "author": "test"}]
        return p

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "gameicons"

    def test_search_local(self, provider):
        results = provider.search("sword", "icon", limit=5)
        assert len(results) >= 1
        assert results[0].license == "CC-BY-3.0"


class TestOpenclipartProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.icon.openclipart_provider import OpenclipartProvider
        return OpenclipartProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "openclipart"


# ══════════════════════════════════════════════════════════
# Diagram providers
# ══════════════════════════════════════════════════════════

class TestMermaidProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.diagram.mermaid_provider import MermaidProvider
        return MermaidProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "mermaid"

    def test_generates_not_searches(self, provider):
        results = provider.search("workflow", "diagram_or_map", limit=2)
        assert len(results) >= 1
        assert all("mermaid.ink" in c.url for c in results)
        assert all(c.visual_type == "diagram_or_map" for c in results)

    def test_returns_empty_for_wrong_visual_type(self, provider):
        results = provider.search("workflow", "photo", limit=2)
        assert results == []


class TestQuickChartProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.diagram.quickchart_provider import QuickChartProvider
        return QuickChartProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "quickchart"

    def test_generates_not_searches(self, provider):
        results = provider.search("revenue", "diagram_or_map", limit=2)
        assert len(results) >= 1
        assert all("quickchart.io" in c.url for c in results)


class TestStorysetProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.diagram.storyset_provider import StorysetProvider
        return StorysetProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "storyset"


class TestUnDrawProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.diagram.undraw_provider import UnDrawProvider
        p = UnDrawProvider(config={})
        # Pre-load index to avoid real HTTP download
        p._index = [{"title": "working", "image": "https://undraw.co/illustrations/working"}]
        return p

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "undraw"

    def test_search_local(self, provider):
        results = provider.search("working", "icon", limit=5)
        assert len(results) >= 1
        assert all(c.visual_type in VALID_VISUAL_TYPES for c in results)


# ══════════════════════════════════════════════════════════
# AI generation providers
# ══════════════════════════════════════════════════════════

class TestPollinationsProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.ai_generation.pollinations_provider import PollinationsProvider
        return PollinationsProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "pollinations"

    def test_visual_type_is_metaphor_photo(self, provider):
        results = provider.search("happiness", "metaphor_photo", limit=2)
        assert len(results) >= 1
        assert all(c.visual_type == "metaphor_photo" for c in results)
        # CRITICAL: never "ai_generated" — §6
        assert all(c.visual_type != "ai_generated" for c in results)

    def test_url_contains_pollinations(self, provider):
        results = provider.search("happiness", "metaphor_photo", limit=2)
        assert all("pollinations.ai" in c.url for c in results)

    def test_license_is_cc_by(self, provider):
        results = provider.search("test", "metaphor_photo", limit=1)
        assert all(c.license == "CC-BY" for c in results)


class TestHuggingFaceProvider:
    @pytest.fixture
    def provider(self):
        from AnkiAI_ImageAddon.image_providers.ai_generation.huggingface_provider import HuggingFaceProvider
        return HuggingFaceProvider(config={})

    def test_inherits_base_provider(self, provider):
        assert isinstance(provider, BaseProvider)

    def test_name(self, provider):
        assert provider.name == "huggingface"

    def test_returns_empty_without_token(self, provider):
        results = provider.search("test", "metaphor_photo")
        assert results == []


# ══════════════════════════════════════════════════════════
# Cross-cutting contract tests
# ══════════════════════════════════════════════════════════

class TestProviderChains:
    """Verify PROVIDER_CHAINS follow §4.2 rules."""

    def test_group_m_has_no_providers(self):
        from AnkiAI_ImageAddon.modules.provider_registry import PROVIDER_CHAINS
        assert PROVIDER_CHAINS["M"] == []

    def test_ai_providers_at_end_of_chain(self):
        from AnkiAI_ImageAddon.modules.provider_registry import PROVIDER_CHAINS
        ai_providers = {"pollinations", "huggingface"}
        for group, chain in PROVIDER_CHAINS.items():
            if group == "M":
                continue
            for i, p in enumerate(chain):
                if p in ai_providers:
                    assert i >= len(chain) // 2, f"{p} too early in group {group} chain"

    def test_all_groups_have_chains(self):
        from AnkiAI_ImageAddon.modules.provider_registry import PROVIDER_CHAINS
        for group in "ABCDEFGHIJKLMN":
            assert group in PROVIDER_CHAINS, f"Missing chain for group {group}"


class TestCandidateInterface:
    def test_candidate_frozen(self):
        c = Candidate(url="http://example.com", provider="test", visual_type="photo")
        with pytest.raises(AttributeError):
            c.url = "changed"

    def test_candidate_to_dict(self):
        c = Candidate(url="http://example.com", provider="test", visual_type="photo",
                       width=100, height=100, license="CC0", attribution="test",
                       title="Test", score=0.5)
        d = c.to_dict()
        assert d["url"] == "http://example.com"
        assert d["provider"] == "test"
        assert d["visual_type"] == "photo"

    def test_candidate_from_dict(self):
        d = {"url": "http://example.com", "provider": "test", "visual_type": "photo"}
        c = Candidate.from_dict(d)
        assert c.url == "http://example.com"
