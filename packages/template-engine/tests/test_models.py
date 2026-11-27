from template_engine.models import NormalizedRegion, validate_region_within_page


def test_region_within_page() -> None:
    region = NormalizedRegion(x=0.1, y=0.2, width=0.3, height=0.4)
    assert validate_region_within_page(region)


def test_region_overflow_is_detected() -> None:
    region = NormalizedRegion(x=0.8, y=0.2, width=0.3, height=0.4)
    assert not validate_region_within_page(region)
