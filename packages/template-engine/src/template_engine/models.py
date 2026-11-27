from pydantic import BaseModel, ConfigDict, Field


class NormalizedRegion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)


class PageDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    size: str
    orientation: str
    coordinate_system: str = "normalized_top_left"


class OMRTemplateHeader(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    template_id: str = Field(min_length=1)
    version: int = Field(ge=1)
    page: PageDefinition


def validate_region_within_page(region: NormalizedRegion) -> bool:
    """Return whether the region fits within normalized page boundaries."""
    return region.x + region.width <= 1.0 and region.y + region.height <= 1.0
