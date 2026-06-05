"""Entertainment image providers: Harry Potter, Anime, Studio Ghibli, Pokémon."""

import logging
from typing import Dict, List

from .base import ImageProviderError, _ImageProviderSessionManager, result_dict

logger = logging.getLogger(__name__)


class HPAPIProvider:
    """Harry Potter API - Characters with images (Hogwarts)."""

    def __init__(self):
        self.name = "hp_api"
        self.session = _ImageProviderSessionManager.get_session("hp_api")
        self.base_urls = [
            "https://hp-api.onrender.com/",
            "https://hp-api.herokuapp.com/",
        ]

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        """
        Search for Harry Potter characters.
        Keyword examples: 'Harry Potter', 'Hermione', 'Dumbledore', etc.
        """
        try:
            # Try primary URL first, fallback to secondary
            for base_url in self.base_urls:
                try:
                    response = self.session.get(
                        f"{base_url}api/characters",
                        timeout=5,
                    )
                    if response.status_code == 200:
                        break
                except Exception:
                    continue
            
            if response.status_code != 200:
                raise ImageProviderError(f"HP-API {response.status_code}")
            
            characters = response.json()
            if not characters:
                raise ImageProviderError("No results")
            
            # Filter by keyword (case-insensitive)
            keyword_lower = keyword.lower()
            filtered = [
                c for c in characters
                if keyword_lower in (c.get("name", "") or "").lower()
                or keyword_lower in (c.get("actor", "") or "").lower()
            ]
            
            if not filtered:
                # If no exact match, just take first results
                filtered = characters[:per_page * 2]
            
            images = []
            for char in filtered[:per_page]:
                if char.get("image"):
                    images.append(
                        result_dict(
                            char.get("image"),
                            char.get("name") or keyword,
                            self.name,
                        )
                    )
            
            if not images:
                raise ImageProviderError("No HP characters with images found")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class PotterAPIProvider:
    """PotterAPI - Harry Potter API by Fedeperin (Books, Characters, Spells, Houses)."""

    def __init__(self):
        self.name = "potter_api"
        self.session = _ImageProviderSessionManager.get_session("potter_api")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        """
        Search for Harry Potter characters, spells, or houses.
        """
        try:
            # Try to fetch characters by default
            response = self.session.get(
                "https://potterapi-fedeperin.vercel.app/en/characters",
                timeout=5,
            )
            
            if response.status_code != 200:
                raise ImageProviderError(f"PotterAPI {response.status_code}")
            
            data = response.json()
            
            # data can be a list or dict with results
            if isinstance(data, dict):
                items = data.get("data", data.get("results", []))
            else:
                items = data
            
            if not items:
                raise ImageProviderError("No results")
            
            # Filter by keyword
            keyword_lower = keyword.lower()
            filtered = [
                item for item in items
                if keyword_lower in (item.get("name", "") or "").lower()
                or keyword_lower in (item.get("fullName", "") or "").lower()
                or keyword_lower in (item.get("actor", "") or "").lower()
            ]
            
            if not filtered:
                filtered = items[:per_page * 2]
            
            images = []
            for item in filtered[:per_page]:
                # Try multiple possible image field names
                image_url = (
                    item.get("image")
                    or item.get("image_url")
                    or item.get("imageUrl")
                    or item.get("thumbnail")
                )
                
                if image_url:
                    images.append(
                        result_dict(
                            image_url,
                            item.get("name") or item.get("fullName") or keyword,
                            self.name,
                        )
                    )
            
            if not images:
                raise ImageProviderError("No PotterAPI images found")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class WaifuPicsProvider:
    """Waifu.pics - Anime images and GIFs with emotion/action categories."""

    def __init__(self):
        self.name = "waifu_pics"
        self.session = _ImageProviderSessionManager.get_session("waifu_pics")
        # Common categories: happy, sad, angry, love, hug, kiss, slap, dance, wave, smile, etc.
        self.categories = [
            "happy", "hug", "dance", "smile", "wave", "pat", "poke",
            "kiss", "lick", "wink", "blush", "bonk", "punch", "slap",
        ]

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        """
        Search for anime GIFs. Maps keywords to categories.
        """
        try:
            # Map keyword to category
            keyword_lower = keyword.lower()
            category = "happy"  # default
            
            for cat in self.categories:
                if cat in keyword_lower:
                    category = cat
                    break
            
            images = []
            for i in range(per_page):
                response = self.session.get(
                    f"https://api.waifu.pics/sfw/{category}",
                    timeout=5,
                )
                
                if response.status_code != 200:
                    if i == 0:  # Only raise if first request fails
                        raise ImageProviderError(f"Waifu.pics {response.status_code}")
                    break
                
                data = response.json()
                if data.get("url"):
                    images.append(
                        result_dict(
                            data.get("url"),
                            f"Anime {category}",
                            self.name,
                        )
                    )
            
            if not images:
                raise ImageProviderError("No Waifu.pics images found")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class NekosBestProvider:
    """Nekos.best - Cute anime (Neko) and roleplay GIFs."""

    def __init__(self):
        self.name = "nekos_best"
        self.session = _ImageProviderSessionManager.get_session("nekos_best")
        # Common categories: neko, kitsune, hug, pat, poke, smile, laugh, wink, etc.
        self.categories = [
            "neko", "kitsune", "hug", "pat", "poke", "smile", "laugh",
            "wink", "dance", "kiss", "blush", "angry", "sad",
        ]

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        """
        Search for anime neko and roleplay GIFs.
        """
        try:
            # Map keyword to category
            keyword_lower = keyword.lower()
            category = "neko"  # default
            
            for cat in self.categories:
                if cat in keyword_lower:
                    category = cat
                    break
            
            images = []
            for i in range(per_page):
                response = self.session.get(
                    f"https://nekos.best/api/v2/{category}",
                    timeout=5,
                )
                
                if response.status_code != 200:
                    if i == 0:
                        raise ImageProviderError(f"Nekos.best {response.status_code}")
                    break
                
                data = response.json()
                results = data.get("results", [])
                if results:
                    result = results[0]
                    images.append(
                        result_dict(
                            result.get("url"),
                            f"Anime {category}",
                            self.name,
                        )
                    )
            
            if not images:
                raise ImageProviderError("No Nekos.best images found")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class StudioGhibliAPIProvider:
    """Studio Ghibli API - Films with images from beloved animated movies."""

    def __init__(self):
        self.name = "studio_ghibli"
        self.session = _ImageProviderSessionManager.get_session("studio_ghibli")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        """
        Search for Studio Ghibli films.
        Examples: 'Spirited Away', 'Totoro', 'Princess Mononoke', etc.
        """
        try:
            response = self.session.get(
                "https://ghibliapi.vercel.app/films",
                timeout=5,
            )
            
            if response.status_code != 200:
                raise ImageProviderError(f"Studio Ghibli API {response.status_code}")
            
            films = response.json()
            if not films:
                raise ImageProviderError("No results")
            
            # Filter by keyword
            keyword_lower = keyword.lower()
            filtered = [
                film for film in films
                if keyword_lower in (film.get("title", "") or "").lower()
                or keyword_lower in (film.get("original_title", "") or "").lower()
                or keyword_lower in (film.get("original_title_romanised", "") or "").lower()
            ]
            
            if not filtered:
                # If no match, just take first results
                filtered = films[:per_page * 2]
            
            images = []
            for film in filtered[:per_page]:
                # Studio Ghibli API provides image URLs
                if film.get("image"):
                    images.append(
                        result_dict(
                            film.get("image"),
                            film.get("title") or keyword,
                            self.name,
                        )
                    )
            
            if not images:
                raise ImageProviderError("No Studio Ghibli images found")
            return images
        except Exception as e:
            raise ImageProviderError(str(e))


class PokeAPIProvider:
    """PokéAPI - Pokémon data with sprites, artwork, and animated GIFs."""

    def __init__(self):
        self.name = "poke_api"
        self.session = _ImageProviderSessionManager.get_session("poke_api")

    def search(self, keyword: str, per_page: int = 3) -> List[Dict]:
        """
        Search for Pokémon by name.
        Examples: 'Pikachu', 'Charizard', 'Dragonite', etc.
        """
        try:
            # First, search for the Pokémon
            response = self.session.get(
                f"https://pokeapi.co/api/v2/pokemon/{keyword.lower()}",
                timeout=5,
            )
            
            if response.status_code != 200:
                raise ImageProviderError(f"PokéAPI {response.status_code}")
            
            pokemon = response.json()
            images = []
            
            # Try multiple image sources in priority order
            sprites = pokemon.get("sprites", {})
            
            # Try animated official artwork first (if available)
            if sprites.get("other", {}).get("official-artwork", {}).get("front_default"):
                images.append(
                    result_dict(
                        sprites.get("other", {}).get("official-artwork", {}).get("front_default"),
                        pokemon.get("name", keyword),
                        self.name,
                    )
                )
            
            # Then try other sprites
            sprite_keys = [
                ("front_default", "Front"),
                ("front_shiny", "Shiny"),
                ("back_default", "Back"),
            ]
            
            for sprite_key, sprite_label in sprite_keys:
                if len(images) >= per_page:
                    break
                if sprites.get(sprite_key):
                    images.append(
                        result_dict(
                            sprites.get(sprite_key),
                            f"{pokemon.get('name', keyword).title()} - {sprite_label}",
                            self.name,
                        )
                    )
            
            if not images:
                raise ImageProviderError("No PokéAPI sprites found")
            
            return images[:per_page]
        except Exception as e:
            raise ImageProviderError(str(e))
