"""Versioned OMR template definitions and PDF generation boundary."""

from template_engine.models import (
    NormalizedRegion,
    OMRTemplate,
    OMRTemplateHeader,
    PageDefinition,
    QuestionDefinition,
    RegistrationMarker,
    SheetCodeDefinition,
    StudentIdentifierField,
    regions_overlap,
    validate_region_within_page,
)

__version__ = "0.1.0"

__all__ = [
    "NormalizedRegion",
    "OMRTemplate",
    "OMRTemplateHeader",
    "PageDefinition",
    "QuestionDefinition",
    "RegistrationMarker",
    "SheetCodeDefinition",
    "StudentIdentifierField",
    "regions_overlap",
    "validate_region_within_page",
]
