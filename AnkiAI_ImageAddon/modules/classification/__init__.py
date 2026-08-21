"""Classification package for AnkiAI ImageAddon.

Provides taxonomy classification, visual_type determination, and linguistic resources.
"""

from .taxonomy import Verdict, TaxonomyClassifier, classify
from .visual_type import VISUAL_TYPES, GROUP_TO_VISUAL_TYPE, get_visual_type_for_group
from .resources import ClassificationResources, get_classification_resources

__all__ = [
    "Verdict",
    "TaxonomyClassifier",
    "classify",
    "VISUAL_TYPES",
    "GROUP_TO_VISUAL_TYPE",
    "get_visual_type_for_group",
    "ClassificationResources",
    "get_classification_resources",
]
