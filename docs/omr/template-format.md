# OMR template format

Templates describe geometry and semantics of a supported printed sheet. A template version is immutable after publication.

## Required properties
- Explicit page size, orientation, coordinate unit, and schema version.
- Stable template ID and version.
- Registration marker definitions.
- QR or machine-readable sheet ID region.
- Student identifier field definitions.
- Question and option identifiers.
- Normalized bubble coordinates.
- Bubble interior inset/measurement region.
- Optional print profile and calibration metadata.

## Illustrative JSON

```json
{
  "schema_version": 1,
  "template_id": "tpl_physics_a4",
  "version": 1,
  "page": {
    "size": "A4",
    "orientation": "portrait",
    "coordinate_system": "normalized_top_left"
  },
  "registration_markers": [
    { "id": "tl", "x": 0.04, "y": 0.04 },
    { "id": "tr", "x": 0.96, "y": 0.04 },
    { "id": "bl", "x": 0.04, "y": 0.96 },
    { "id": "br", "x": 0.96, "y": 0.96 }
  ],
  "sheet_code": {
    "type": "qr",
    "region": { "x": 0.78, "y": 0.06, "width": 0.14, "height": 0.14 }
  },
  "questions": [
    {
      "number": 1,
      "options": ["A", "B", "C", "D"],
      "bubbles": {
        "A": { "x": 0.18, "y": 0.31, "width": 0.025, "height": 0.025 },
        "B": { "x": 0.23, "y": 0.31, "width": 0.025, "height": 0.025 },
        "C": { "x": 0.28, "y": 0.31, "width": 0.025, "height": 0.025 },
        "D": { "x": 0.33, "y": 0.31, "width": 0.025, "height": 0.025 }
      }
    }
  ]
}
```

Illustrative only, not a production layout. Production validation must check bounds, overlaps, required markers, option uniqueness, question numbering, and page profiles.

## Versioning rules
- Published versions are immutable.
- Geometry or semantics changes create a new version.
- Processing stores the exact template version used.
- Never infer the template only from a client-provided filename.
- Embedded sheet identity must be checked against the selected exam and batch.
