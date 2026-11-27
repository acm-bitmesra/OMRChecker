from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_EDGE_EPSILON = 1e-9


class NormalizedRegion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)


class PageDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    size: str = Field(min_length=1)
    orientation: Literal["portrait", "landscape"]
    coordinate_system: Literal["normalized_top_left"] = "normalized_top_left"


class OMRTemplateHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    template_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    page: PageDefinition


class RegistrationMarker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class SheetCodeDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["qr", "barcode"] = "qr"
    region: NormalizedRegion


class StudentIdentifierField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    region: NormalizedRegion


class QuestionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    number: int = Field(ge=1)
    options: list[str] = Field(min_length=2)
    bubbles: dict[str, NormalizedRegion]

    @model_validator(mode="after")
    def validate_options_and_bubbles(self) -> "QuestionDefinition":
        if len(self.options) != len(set(self.options)):
            raise ValueError(f"Question {self.number} contains duplicate option labels")
        if set(self.bubbles) != set(self.options):
            raise ValueError(
                f"Question {self.number} bubbles keys must match options exactly"
            )
        return self


class OMRTemplate(OMRTemplateHeader):
    registration_markers: list[RegistrationMarker] = Field(min_length=4)
    sheet_code: SheetCodeDefinition
    questions: list[QuestionDefinition] = Field(min_length=1)
    student_id_fields: list[StudentIdentifierField] = Field(default_factory=list)
    bubble_inset_ratio: float = Field(default=0.15, ge=0.0, lt=0.5)

    @model_validator(mode="after")
    def validate_template_geometry(self) -> "OMRTemplate":
        marker_ids = [marker.id for marker in self.registration_markers]
        if len(marker_ids) != len(set(marker_ids)):
            raise ValueError("Registration marker IDs must be unique")

        marker_coords = {(marker.x, marker.y) for marker in self.registration_markers}
        if len(marker_coords) != len(self.registration_markers):
            raise ValueError("Registration markers must have distinct coordinates")

        named_regions: list[tuple[str, NormalizedRegion]] = [
            ("sheet_code", self.sheet_code.region),
        ]
        for field in self.student_id_fields:
            named_regions.append((f"student_id:{field.name}", field.region))

        seen_questions: set[int] = set()
        for question in self.questions:
            if question.number in seen_questions:
                raise ValueError(f"Duplicate question number: {question.number}")
            seen_questions.add(question.number)
            for option in question.options:
                named_regions.append(
                    (f"q{question.number}:{option}", question.bubbles[option])
                )

        for label, region in named_regions:
            if not validate_region_within_page(region):
                raise ValueError(f"Region '{label}' exceeds normalized page boundaries")

        for idx, (label_a, region_a) in enumerate(named_regions):
            for label_b, region_b in named_regions[idx + 1 :]:
                if regions_overlap(region_a, region_b):
                    raise ValueError(
                        f"Template regions '{label_a}' and '{label_b}' overlap"
                    )

        return self


def validate_region_within_page(region: NormalizedRegion) -> bool:
    """Return whether the region fits within normalized page boundaries."""
    return (
        region.x + region.width <= 1.0 + _EDGE_EPSILON
        and region.y + region.height <= 1.0 + _EDGE_EPSILON
    )


def regions_overlap(a: NormalizedRegion, b: NormalizedRegion) -> bool:
    """Return True when two normalized bounding boxes have positive intersection area."""
    return (
        a.x < b.x + b.width - _EDGE_EPSILON
        and b.x < a.x + a.width - _EDGE_EPSILON
        and a.y < b.y + b.height - _EDGE_EPSILON
        and b.y < a.y + a.height - _EDGE_EPSILON
    )
