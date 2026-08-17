"""Tests for API handler cache key normalization."""

from AnkiAI_ImageAddon.modules.api_handler import SearchContextCache
from AnkiAI_ImageAddon.modules.ai_providers import SearchContext


def test_search_context_cache_normalizes_html_and_spacing():
    cache = SearchContextCache()
    key = cache.make_key("  <b>Hello</b>   world ", "A   definition")
    cache.set(key, SearchContext(keyword="hello world", domain="general"))

    equivalent = cache.make_key("Hello world", "A definition")

    assert cache.get(equivalent).keyword == "hello world"
