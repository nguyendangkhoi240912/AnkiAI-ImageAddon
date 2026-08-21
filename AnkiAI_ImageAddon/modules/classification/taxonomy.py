"""Taxonomy classification engine for AnkiAI ImageAddon (14 Groups A-N).

Implements pure Python 100% local classification according to Master Spec v9 §5, §6, §7, §17.2.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .resources import get_classification_resources, ClassificationResources
from .visual_type import get_visual_type_for_group

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Verdict:
    """Represents the classification and search directive for a card."""
    word: str
    group: str              # A–N
    visual_type: str        # photo | gif | icon | diagram_or_map | metaphor_photo | local_svg | none
    query: str              # Final search query
    alt: str                # Alternate / fallback query
    confidence: float       # Confidence score (0.0 .. 1.0)
    sense_id: str           # WordNet / sense ID if resolved, else empty
    resolved_by: str        # "rule" | "groq-batch" | "gemini-vision-qc" | ...
    en_query: str           # Normalized English search query

    def to_dict(self) -> Dict[str, Any]:
        """Convert Verdict to dictionary."""
        return {
            "word": self.word,
            "group": self.group,
            "visual_type": self.visual_type,
            "query": self.query,
            "alt": self.alt,
            "confidence": self.confidence,
            "sense_id": self.sense_id,
            "resolved_by": self.resolved_by,
            "en_query": self.en_query,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Verdict":
        """Reconstruct Verdict from dictionary."""
        return cls(
            word=data.get("word", ""),
            group=data.get("group", "A"),
            visual_type=data.get("visual_type", "photo"),
            query=data.get("query", ""),
            alt=data.get("alt", ""),
            confidence=float(data.get("confidence", 1.0)),
            sense_id=data.get("sense_id", ""),
            resolved_by=data.get("resolved_by", "rule"),
            en_query=data.get("en_query", ""),
        )


# Known strategic / systemic concepts that pass the "box + arrow" test (§7) -> Group F
SYSTEMIC_STRATEGIC_TERMS = {
    "tactics", "strategy", "workflow", "process", "pipeline", "supply chain",
    "hierarchy", "framework", "architecture", "protocol", "algorithm",
    "distribution", "negotiation", "governance", "infrastructure",
    "procedure", "logistics", "coordination", "integration", "optimization",
    "methodology", "delegation", "synergy", "system", "ecosystem",
}

# Common descriptive adjectives with visual polarities (Group I)
DESCRIPTIVE_ADJECTIVES = {
    "big", "small", "huge", "tiny", "hot", "cold", "warm", "cool",
    "fast", "slow", "heavy", "light", "tall", "short", "wide", "narrow",
    "bright", "dark", "clean", "dirty", "wet", "dry", "sharp", "dull",
    "hard", "soft", "thick", "thin", "rough", "smooth", "loud", "quiet",
    "old", "young", "new", "empty", "full", "rich", "poor", "strong", "weak",
    "sweet", "sour", "bitter", "salty", "round", "square", "flat", "straight",
}

# Action verb indicators (Group G)
ACTION_VERBS = {
    "run", "jump", "walk", "cook", "swim", "fly", "dance", "climb",
    "drive", "write", "read", "sing", "laugh", "cry", "fight", "eat",
    "drink", "sleep", "throw", "catch", "push", "pull", "kick", "punch",
    "cut", "paint", "draw", "build", "break", "fix", "clean", "wash",
    "open", "close", "lift", "drop", "shake", "wave", "nod", "smile",
}


class TaxonomyClassifier:
    """Rule-based taxonomy and visual_type classifier for groups A-N."""

    def __init__(self, resources: Optional[ClassificationResources] = None):
        self.resources = resources or get_classification_resources()

    def classify(
        self,
        word: str,
        sentence: str = "",
        deck_or_tags: str = "",
    ) -> Verdict:
        """Classify a word into one of 14 taxonomy groups (A-N) and determine its visual_type.

        Args:
            word: Target vocabulary word or phrase.
            sentence: Context sentence from flashcard.
            deck_or_tags: Deck name or tags for domain hints.

        Returns:
            Verdict object with group, visual_type, queries, and confidence.
        """
        clean_word = (word or "").strip()
        word_lower = clean_word.lower()

        if not clean_word:
            return Verdict(
                word="",
                group="M",
                visual_type="none",
                query="",
                alt="",
                confidence=1.0,
                sense_id="",
                resolved_by="rule",
                en_query="",
            )

        # 1. Group N — Numbers / Units / Chemical Formulas
        if self.resources.is_group_n_formula_or_unit(clean_word):
            return Verdict(
                word=clean_word,
                group="N",
                visual_type=get_visual_type_for_group("N"),
                query=clean_word,
                alt=clean_word,
                confidence=0.98,
                sense_id="",
                resolved_by="rule",
                en_query=clean_word,
            )

        # 2. Group L — Idioms / Figurative Collocations
        matched_idiom = self.resources.find_matching_idiom(word_lower)
        if matched_idiom or (" " in word_lower and len(word_lower.split()) >= 3):
            idiom_text = matched_idiom or word_lower
            return Verdict(
                word=clean_word,
                group="L",
                visual_type=get_visual_type_for_group("L"),
                query=idiom_text,
                alt=f"{idiom_text} meaning illustration",
                confidence=0.95,
                sense_id="",
                resolved_by="rule",
                en_query=idiom_text,
            )

        # 3. Group K — Spatial Prepositions / Directional (evaluated before generic function words)
        if self.resources.is_spatial_preposition(word_lower):
            return Verdict(
                word=clean_word,
                group="K",
                visual_type=get_visual_type_for_group("K"),
                query=word_lower,
                alt=f"{word_lower} preposition diagram",
                confidence=0.98,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # 4. Group M — Function words (articles, conjunctions, pronouns)
        if self.resources.is_function_word(word_lower):
            return Verdict(
                word=clean_word,
                group="M",
                visual_type=get_visual_type_for_group("M"),
                query="",
                alt="",
                confidence=1.0,
                sense_id="",
                resolved_by="rule",
                en_query=clean_word,
            )

        # 5. Group C — Proper Nouns / Gazetteer
        is_title_case = clean_word[0].isupper() and len(clean_word) > 1 and not clean_word.isupper()
        if self.resources.is_gazetteer_entity(word_lower) or (is_title_case and not self.resources.is_function_word(word_lower)):
            return Verdict(
                word=clean_word,
                group="C",
                visual_type=get_visual_type_for_group("C"),
                query=clean_word,
                alt=f"{clean_word} landmark",
                confidence=0.95,
                sense_id="",
                resolved_by="rule",
                en_query=clean_word,
            )

        # 6. Group D — Domain Lexicon / Scientific
        is_domain = self.resources.is_domain_term(word_lower)
        if not is_domain and deck_or_tags:
            dt_lower = deck_or_tags.lower()
            if any(k in dt_lower for k in ("biology", "chemistry", "physics", "medical", "anatomy", "science")):
                is_domain = True
        if is_domain:
            return Verdict(
                word=clean_word,
                group="D",
                visual_type=get_visual_type_for_group("D"),
                query=f"{word_lower} diagram",
                alt=word_lower,
                confidence=0.92,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # 7. Polysemous Concrete Nouns (Group B)
        polysemous_set = {
            "bank", "bat", "spring", "bar", "crane", "trunk", "bow", "nail",
            "palm", "club", "scale", "match", "ring", "drill", "file", "rock",
            "chest", "court", "park", "pitcher", "seal", "tank", "watch"
        }
        if word_lower in polysemous_set:
            return Verdict(
                word=clean_word,
                group="B",
                visual_type=get_visual_type_for_group("B"),
                query=word_lower,
                alt=f"{word_lower} object",
                confidence=0.88,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # 8. Group F — Abstract Systems / Strategic / Process ("Box + Arrow" Test §7)
        if word_lower in SYSTEMIC_STRATEGIC_TERMS or word_lower.endswith(("flow", "chain", "protocol", "system")):
            return Verdict(
                word=clean_word,
                group="F",
                visual_type=get_visual_type_for_group("F"),  # diagram_or_map
                query=f"{word_lower} diagram",
                alt=f"{word_lower} map",
                confidence=0.95,
                sense_id="",
                resolved_by="rule",
                en_query=f"{word_lower} diagram",
            )

        # 9. Group H — Stative Verbs (believe, know, think, want...)
        if self.resources.is_stative_verb(word_lower):
            # If used as abstract noun in low-concreteness list (e.g. hope, faith, love)
            if word_lower in {"hope", "faith", "love", "fear", "pity", "mind"}:
                # Check sentence context for noun usage
                s_lower = (sentence or "").lower()
                if any(ind in s_lower for ind in (f"to {word_lower}", f"held on to {word_lower}", f"lost {word_lower}", f"the {word_lower}", f"my {word_lower}", f"their {word_lower}")):
                    return Verdict(
                        word=clean_word,
                        group="E",
                        visual_type=get_visual_type_for_group("E"),
                        query=word_lower,
                        alt=f"{word_lower} metaphor",
                        confidence=0.90,
                        sense_id="",
                        resolved_by="rule",
                        en_query=word_lower,
                    )
            return Verdict(
                word=clean_word,
                group="H",
                visual_type=get_visual_type_for_group("H"),
                query=f"{word_lower} concept icon",
                alt=word_lower,
                confidence=0.92,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # 10. Concreteness Norm & POS-based resolution (Groups A, B, E, G, I, J)
        concreteness = self.resources.get_concreteness(word_lower, default=3.0)

        # Descriptive adjectives (Group I)
        if word_lower in DESCRIPTIVE_ADJECTIVES:
            return Verdict(
                word=clean_word,
                group="I",
                visual_type=get_visual_type_for_group("I"),
                query=word_lower,
                alt=f"{word_lower} photo",
                confidence=0.92,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # Action verbs (Group G)
        if word_lower in ACTION_VERBS:
            return Verdict(
                word=clean_word,
                group="G",
                visual_type=get_visual_type_for_group("G"),
                query=word_lower,
                alt=f"{word_lower} action",
                confidence=0.92,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # Descriptive adjectives (Group I)
        if word_lower in DESCRIPTIVE_ADJECTIVES:
            return Verdict(
                word=clean_word,
                group="I",
                visual_type=get_visual_type_for_group("I"),
                query=word_lower,
                alt=f"{word_lower} photo",
                confidence=0.92,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # Concrete nouns (Groups A & B)
        if concreteness >= 3.8:
            # Polysemous high-ambiguity words -> Group B (e.g. bank, bat, spring, bar, crane)
            polysemous_candidates = {"bank", "bat", "spring", "bar", "crane", "trunk", "bow", "nail", "palm"}
            if word_lower in polysemous_candidates:
                return Verdict(
                    word=clean_word,
                    group="B",
                    visual_type=get_visual_type_for_group("B"),
                    query=word_lower,
                    alt=f"{word_lower} object",
                    confidence=0.88,
                    sense_id="",
                    resolved_by="rule",
                    en_query=word_lower,
                )
            # Default concrete object -> Group A
            return Verdict(
                word=clean_word,
                group="A",
                visual_type=get_visual_type_for_group("A"),
                query=word_lower,
                alt=f"{word_lower} photo",
                confidence=0.95,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # Abstract concepts (Groups E & J)
        if concreteness < 3.0:
            # Abstract adjective endings (-ic, -able, -ive, -al, -ous) -> Group J
            if word_lower.endswith(("ic", "able", "ible", "ive", "al", "ous", "ful", "less")):
                return Verdict(
                    word=clean_word,
                    group="J",
                    visual_type=get_visual_type_for_group("J"),
                    query=word_lower,
                    alt=f"{word_lower} concept",
                    confidence=0.90,
                    sense_id="",
                    resolved_by="rule",
                    en_query=word_lower,
                )
            # Abstract emotions / values / states -> Group E
            return Verdict(
                word=clean_word,
                group="E",
                visual_type=get_visual_type_for_group("E"),
                query=word_lower,
                alt=f"{word_lower} metaphor",
                confidence=0.90,
                sense_id="",
                resolved_by="rule",
                en_query=word_lower,
            )

        # Fallback for mid-range concreteness -> Group A with moderate confidence
        return Verdict(
            word=clean_word,
            group="A",
            visual_type="photo",
            query=word_lower,
            alt=word_lower,
            confidence=0.85,
            sense_id="",
            resolved_by="rule",
            en_query=word_lower,
        )


# Global classifier instance
_global_classifier: Optional[TaxonomyClassifier] = None


def classify(word: str, sentence: str = "", deck_or_tags: str = "") -> Verdict:
    """Classify a word into groups A-N using the global classifier singleton."""
    global _global_classifier
    if _global_classifier is None:
        _global_classifier = TaxonomyClassifier()
    return _global_classifier.classify(word, sentence=sentence, deck_or_tags=deck_or_tags)
