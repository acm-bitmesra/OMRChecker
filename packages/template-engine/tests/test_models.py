import pytest
from pydantic import ValidationError

from template_engine.models import (
    NormalizedRegion,
    OMRTemplate,
    regions_overlap,
    validate_region_within_page,
)


def _valid_template_payload() -> dict:
    return {
        "schema_version": 1,
        "template_id": "tpl_physics_a4",
        "version": 1,
        "page": {
            "size": "A4",
            "orientation": "portrait",
            "coordinate_system": "normalized_top_left",
        },
        "registration_markers": [
            {"id": "tl", "x": 0.04, "y": 0.04},
            {"id": "tr", "x": 0.96, "y": 0.04},
            {"id": "bl", "x": 0.04, "y": 0.96},
            {"id": "br", "x": 0.96, "y": 0.96},
        ],
        "sheet_code": {
            "type": "qr",
            "region": {"x": 0.78, "y": 0.06, "width": 0.14, "height": 0.14},
        },
        "questions": [
            {
                "number": 1,
                "options": ["A", "B", "C", "D"],
                "bubbles": {
                    "A": {"x": 0.18, "y": 0.31, "width": 0.025, "height": 0.025},
                    "B": {"x": 0.23, "y": 0.31, "width": 0.025, "height": 0.025},
                    "C": {"x": 0.28, "y": 0.31, "width": 0.025, "height": 0.025},
                    "D": {"x": 0.33, "y": 0.31, "width": 0.025, "height": 0.025},
                },
            }
        ],
    }


def test_region_within_page() -> None:
    region = NormalizedRegion(x=0.1, y=0.2, width=0.3, height=0.4)
    assert validate_region_within_page(region)


def test_region_overflow_is_detected() -> None:
    region = NormalizedRegion(x=0.8, y=0.2, width=0.3, height=0.4)
    assert not validate_region_within_page(region)


def test_touching_regions_do_not_overlap() -> None:
    left = NormalizedRegion(x=0.1, y=0.1, width=0.1, height=0.1)
    right = NormalizedRegion(x=0.2, y=0.1, width=0.1, height=0.1)
    assert not regions_overlap(left, right)


def test_valid_template_schema() -> None:
    template = OMRTemplate.model_validate(_valid_template_payload())
    assert template.template_id == "tpl_physics_a4"
    assert len(template.questions) == 1
    assert template.bubble_inset_ratio == pytest.approx(0.15)


def test_template_rejects_overlapping_bubbles() -> None:
    payload = _valid_template_payload()
    payload["questions"][0]["bubbles"]["B"]["x"] = 0.19
    with pytest.raises(ValidationError, match="overlap"):
        OMRTemplate.model_validate(payload)


def test_template_rejects_out_of_bounds_region() -> None:
    payload = _valid_template_payload()
    payload["sheet_code"]["region"] = {"x": 0.90, "y": 0.06, "width": 0.15, "height": 0.10}
    with pytest.raises(ValidationError, match="exceeds normalized page boundaries"):
        OMRTemplate.model_validate(payload)


def test_template_rejects_duplicate_question_numbers_and_mismatched_options() -> None:
    payload = _valid_template_payload()
    q2 = dict(payload["questions"][0])
    q2["bubbles"] = {
        opt: {"x": 0.18 + idx * 0.05, "y": 0.40, "width": 0.025, "height": 0.025}
        for idx, opt in enumerate(["A", "B", "C", "D"])
    }
    payload["questions"].append(q2)
    with pytest.raises(ValidationError, match="Duplicate question number"):
        OMRTemplate.model_validate(payload)

    payload2 = _valid_template_payload()
    del payload2["questions"][0]["bubbles"]["D"]
    with pytest.raises(ValidationError, match="must match options"):
        OMRTemplate.model_validate(payload2)


def test_template_rejects_duplicate_marker_ids_or_coords() -> None:
    payload = _valid_template_payload()
    payload["registration_markers"][1]["id"] = "tl"
    with pytest.raises(ValidationError, match="Registration marker IDs"):
        OMRTemplate.model_validate(payload)

    payload2 = _valid_template_payload()
    payload2["registration_markers"][1]["x"] = 0.04
    with pytest.raises(ValidationError, match="distinct coordinates"):
        OMRTemplate.model_validate(payload2)
