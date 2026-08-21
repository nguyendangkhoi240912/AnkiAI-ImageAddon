"""Static and heavy linguistic resource loader for classification.

Provides lazy-loaded access to:
- Static datasets: Brysbaert concreteness, function words, stative verbs,
  spatial prepositions, domain lexicon, gazetteer, idioms.
- Heavy resources: NLTK WordNet, spaCy en_core_web_sm (lazy-loaded).
- Group N regex patterns (numbers, chemical formulas, units).
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

# Pre-compiled Regex patterns for Group N
CHEMICAL_FORMULA_RE = re.compile(
    r"^(?:[A-Z][a-z]?[\d₀-₉]*)+(?:[+–-]\d*|\d*[+–-])?$"
)
MEASUREMENT_UNIT_RE = re.compile(
    r"^\d+(?:\.\d+)?\s*(?:°C|°F|K|kg|g|mg|µg|km|m|cm|mm|nm|µm|s|ms|min|h|hr|Hz|kHz|MHz|GHz|V|kV|mV|A|mA|µA|W|kW|MW|J|kJ|cal|kcal|Pa|kPa|MPa|atm|bar|psi|L|mL|µL|mol|mmol|rpm|dB|%|ppm|mph|km/h|m/s)$",
    re.IGNORECASE,
)
MATH_EXPRESSION_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?|\bpi\b|\be\b|\bphi\b|[0-9]+/[0-9]+|√\d+|\d+[²³⁴⁵]|[\d\.]+\s*[\+\-\*\/]\s*[\d\.]+)$",
    re.IGNORECASE,
)


class ClassificationResources:
    """Manages static datasets and heavy linguistic models with lazy initialization."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR

        # Cached datasets (loaded on demand)
        self._concreteness: Optional[Dict[str, float]] = None
        self._function_words: Optional[Set[str]] = None
        self._stative_verbs: Optional[Set[str]] = None
        self._spatial_prepositions: Optional[Set[str]] = None
        self._domain_lexicon: Optional[Dict[str, Set[str]]] = None
        self._domain_terms_all: Optional[Set[str]] = None
        self._gazetteer: Optional[Set[str]] = None
        self._idioms: Optional[List[str]] = None

        # Heavy NLP models (lazy loaded)
        self._spacy_nlp = None
        self._wordnet = None

    def _load_json(self, filename: str) -> Any:
        path = self.data_dir / filename
        if not path.exists():
            logger.warning("Resource file not found: %s", path)
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def concreteness(self) -> Dict[str, float]:
        """Brysbaert concreteness norm dictionary (word -> score 1.0..5.0)."""
        if self._concreteness is None:
            raw = self._load_json("concreteness.json")
            self._concreteness = {k.lower(): float(v) for k, v in raw.items()}
        return self._concreteness

    @property
    def function_words(self) -> Set[str]:
        """Set of function words for Group M (articles, conjunctions, pronouns, etc.)."""
        if self._function_words is None:
            raw = self._load_json("function_words.json")
            words: Set[str] = set()
            if isinstance(raw, dict):
                for cat_words in raw.values():
                    words.update(w.lower() for w in cat_words)
            elif isinstance(raw, list):
                words.update(w.lower() for w in raw)
            self._function_words = words
        return self._function_words

    @property
    def stative_verbs(self) -> Set[str]:
        """Set of stative verbs for Group H (believe, know, think, etc.)."""
        if self._stative_verbs is None:
            raw = self._load_json("stative_verbs.json")
            verbs: Set[str] = set()
            if isinstance(raw, dict):
                for cat_verbs in raw.values():
                    verbs.update(v.lower() for v in cat_verbs)
            elif isinstance(raw, list):
                verbs.update(v.lower() for v in raw)
            self._stative_verbs = verbs
        return self._stative_verbs

    @property
    def spatial_prepositions(self) -> Set[str]:
        """Set of spatial prepositions and directional phrases for Group K."""
        if self._spatial_prepositions is None:
            raw = self._load_json("spatial_prepositions.json")
            preps: Set[str] = set()
            if isinstance(raw, dict):
                for cat_preps in raw.values():
                    preps.update(p.lower() for p in cat_preps)
            elif isinstance(raw, list):
                preps.update(p.lower() for p in raw)
            self._spatial_prepositions = preps
        return self._spatial_prepositions

    @property
    def domain_lexicon(self) -> Dict[str, Set[str]]:
        """Categorized domain lexicon for Group D."""
        if self._domain_lexicon is None:
            raw = self._load_json("domain_lexicon.json")
            self._domain_lexicon = {
                cat: {term.lower() for term in terms}
                for cat, terms in raw.items()
            }
        return self._domain_lexicon

    @property
    def domain_terms_all(self) -> Set[str]:
        """Flattened set of all domain terms for quick Group D check."""
        if self._domain_terms_all is None:
            terms: Set[str] = set()
            for cat_terms in self.domain_lexicon.values():
                terms.update(cat_terms)
            self._domain_terms_all = terms
        return self._domain_terms_all

    @property
    def gazetteer(self) -> Set[str]:
        """Set of geographical and proper noun entries for Group C."""
        if self._gazetteer is None:
            raw = self._load_json("gazetteer.json")
            entries: Set[str] = set()
            if isinstance(raw, dict):
                for cat_entries in raw.values():
                    entries.update(e.lower() for e in cat_entries)
            elif isinstance(raw, list):
                entries.update(e.lower() for e in raw)
            self._gazetteer = entries
        return self._gazetteer

    @property
    def idioms(self) -> List[str]:
        """List of idioms and figurative collocations for Group L."""
        if self._idioms is None:
            raw = self._load_json("idioms.json")
            self._idioms = [item.lower().strip() for item in raw] if isinstance(raw, list) else []
        return self._idioms

    # Group N Regex Helpers
    def is_group_n_formula_or_unit(self, text: str) -> bool:
        """Check if text matches Group N (chemical formulas, units, numbers)."""
        clean = text.strip()
        if not clean:
            return False
        if CHEMICAL_FORMULA_RE.match(clean) and any(c.isupper() for c in clean):
            # Check if it has at least 2 distinct element symbols or a digit (e.g. H2O, NaCl, CO2)
            has_digits = any(c.isdigit() or c in "₀₁₂₃₄₅₆₇₈₉" for c in clean)
            upper_count = sum(1 for c in clean if c.isupper())
            if has_digits or upper_count >= 2:
                return True
        if MEASUREMENT_UNIT_RE.match(clean):
            return True
        if MATH_EXPRESSION_RE.match(clean):
            return True
        return False

    def get_concreteness(self, word: str, default: float = 3.0) -> float:
        """Lookup concreteness rating (1.0..5.0)."""
        return self.concreteness.get(word.lower().strip(), default)

    def is_function_word(self, word: str) -> bool:
        """Check if word is a function word (Group M)."""
        return word.lower().strip() in self.function_words

    def is_stative_verb(self, word: str) -> bool:
        """Check if word is a stative verb (Group H)."""
        return word.lower().strip() in self.stative_verbs

    def is_spatial_preposition(self, phrase: str) -> bool:
        """Check if phrase is a spatial preposition (Group K)."""
        return phrase.lower().strip() in self.spatial_prepositions

    def is_domain_term(self, word: str) -> bool:
        """Check if word is a specialized scientific/technical domain term (Group D)."""
        return word.lower().strip() in self.domain_terms_all

    def is_gazetteer_entity(self, name: str) -> bool:
        """Check if name matches gazetteer entities (Group C)."""
        return name.lower().strip() in self.gazetteer

    def find_matching_idiom(self, text: str) -> Optional[str]:
        """Check if text contains or matches an idiom (Group L)."""
        lower = text.lower()
        for idiom in self.idioms:
            if idiom in lower:
                return idiom
        return None


# Global singleton instance
_global_resources: Optional[ClassificationResources] = None


def get_classification_resources() -> ClassificationResources:
    """Get or initialize the global ClassificationResources singleton."""
    global _global_resources
    if _global_resources is None:
        _global_resources = ClassificationResources()
    return _global_resources
