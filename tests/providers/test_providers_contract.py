"""Unit and contract tests for Candidate dataclass and BaseProvider interface.

Verifies adherence to Master Spec v9 §17.2 interface requirements.
"""

import pytest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch
from typing import List

from AnkiAI_ImageAddon.image_providers.base_provider import (
    Candidate,
    BaseProvider,
    ImageProviderError,
)


class TestCandidateContract:
    """Test the Candidate dataclass contract."""

    def test_candidate_instantiation_and_fields(self):
        cand = Candidate(
            url="https://example.com/image.jpg",
            provider="test_provider",
            visual_type="photo",
            width=800,
            height=600,
            license="CC-BY-4.0",
            attribution="Author Name",
            title="Sample Title",
            score=0.95,
        )
        assert cand.url == "https://example.com/image.jpg"
        assert cand.provider == "test_provider"
        assert cand.visual_type == "photo"
        assert cand.width == 800
        assert cand.height == 600
        assert cand.license == "CC-BY-4.0"
        assert cand.attribution == "Author Name"
        assert cand.title == "Sample Title"
        assert cand.score == 0.95

    def test_candidate_is_frozen(self):
        cand = Candidate(
            url="https://example.com/test.png",
            provider="pixabay",
            visual_type="photo",
        )
        with pytest.raises((FrozenInstanceError, AttributeError)):
            cand.score = 1.0

    def test_candidate_to_dict_and_from_dict(self):
        orig = Candidate(
            url="https://example.com/apple.jpg",
            provider="wikimedia",
            visual_type="photo",
            width=640,
            height=480,
            license="Public Domain",
            attribution="Wikimedia Commons",
            title="Red Apple",
            score=0.85,
        )
        d = orig.to_dict()
        assert isinstance(d, dict)
        assert d["url"] == orig.url
        assert d["provider"] == orig.provider
        assert d["score"] == 0.85

        recovered = Candidate.from_dict(d)
        assert recovered == orig


class DummyProvider(BaseProvider):
    """Concrete implementation of BaseProvider for testing."""

    name = "dummy"

    def search(
        self,
        query: str,
        visual_type: str = "photo",
        limit: int = 10,
    ) -> List[Candidate]:
        if not query:
            return []
        return [
            Candidate(
                url=f"https://dummy.org/{query}_{i}.jpg",
                provider=self.name,
                visual_type=visual_type,
                title=f"{query} result {i}",
            )
            for i in range(min(limit, 3))
        ]


class TestBaseProviderContract:
    """Test BaseProvider contract and behavior."""

    def test_cannot_instantiate_abstract_base_provider(self):
        with pytest.raises(TypeError):
            BaseProvider()

    def test_concrete_provider_implements_search(self):
        provider = DummyProvider()
        results = provider.search("tactics", visual_type="diagram_or_map", limit=2)
        assert len(results) == 2
        assert isinstance(results[0], Candidate)
        assert results[0].provider == "dummy"
        assert results[0].visual_type == "diagram_or_map"
        assert "tactics" in results[0].url


class TestProviderSubpackagesImports:
    """Test that image_providers subpackages import properly."""

    def test_import_static_providers(self):
        from AnkiAI_ImageAddon.image_providers.static import (
            UnsplashProvider,
            PexelsProvider,
            PixabayProvider,
        )
        assert UnsplashProvider is not None
        assert PexelsProvider is not None
        assert PixabayProvider is not None

    def test_import_animated_providers(self):
        from AnkiAI_ImageAddon.image_providers.animated import (
            KLIPYProvider,
            GIPHYProvider,
            PixabayAnimatedProvider,
            IconScoutProvider,
        )
        assert KLIPYProvider is not None
        assert GIPHYProvider is not None
        assert PixabayAnimatedProvider is not None
        assert IconScoutProvider is not None

    def test_import_scientific_providers(self):
        from AnkiAI_ImageAddon.image_providers.scientific import (
            PubChemProvider,
            NASAImagesProvider,
            CodeCogsProvider,
        )
        assert PubChemProvider is not None
        assert NASAImagesProvider is not None
        assert CodeCogsProvider is not None

    def test_import_wikimedia_provider(self):
        from AnkiAI_ImageAddon.image_providers.wikimedia import (
            WikimediaCommonsProvider,
            WikimediaSmartProvider,
        )
        assert WikimediaCommonsProvider is not None
        assert WikimediaSmartProvider is not None


class TestProviderMockHTTP:
    """Test providers with mocked HTTP responses."""

    @patch("requests.Session.get")
    def test_pixabay_mock_search(self, mock_get):
        from AnkiAI_ImageAddon.image_providers.static import PixabayProvider

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "hits": [
                {
                    "webformatURL": "https://pixabay.com/photo.jpg",
                    "tags": "cat, pet",
                    "imageWidth": 640,
                    "imageHeight": 480,
                }
            ]
        }
        mock_get.return_value = mock_resp

        provider = PixabayProvider(api_key="test_key")
        results = provider.search("cat")
        assert len(results) >= 1
        assert results[0]["url"] == "https://pixabay.com/photo.jpg"

    @patch("requests.Session.get")
    def test_klipy_mock_search(self, mock_get):
        from AnkiAI_ImageAddon.image_providers.animated import KLIPYProvider

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "data": [
                    {
                        "title": "happy dog",
                        "file": {
                            "md": {
                                "gif": {"url": "https://media.klipy.ai/gif/dog.gif"}
                            }
                        },
                    }
                ]
            }
        }
        mock_get.return_value = mock_resp

        provider = KLIPYProvider(app_key="test_klipy")
        results = provider.search("dog")
        assert len(results) >= 1
        assert "klipy" in results[0]["url"] or results[0]["provider"] == "klipy"

    @patch("requests.Session.get")
    def test_wikimedia_mock_search(self, mock_get):
        from AnkiAI_ImageAddon.image_providers.wikimedia import WikimediaCommonsProvider

        resp1 = Mock()
        resp1.status_code = 200
        resp1.json.return_value = {
            "query": {
                "search": [
                    {"title": "File:Biology_cell.svg"}
                ]
            }
        }

        resp2 = Mock()
        resp2.status_code = 200
        resp2.json.return_value = {
            "query": {
                "pages": {
                    "123": {
                        "title": "File:Biology_cell.svg",
                        "imageinfo": [
                            {
                                "url": "https://upload.wikimedia.org/cell.svg",
                                "descriptionurl": "https://commons.wikimedia.org/cell",
                            }
                        ],
                    }
                }
            }
        }
        mock_get.side_effect = [resp1, resp2]

        provider = WikimediaCommonsProvider()
        results = provider.search("cell")
        assert len(results) >= 1
        assert results[0]["url"] == "https://upload.wikimedia.org/cell.svg"



