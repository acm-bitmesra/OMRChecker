from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class NormalizedBox:
    """Normalized top-left bounding box with coordinates in [0.0, 1.0]."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.x <= 1.0 and 0.0 <= self.y <= 1.0):
            raise ValueError("x and y must be between 0.0 and 1.0")
        if not (0.0 < self.width <= 1.0 and 0.0 < self.height <= 1.0):
            raise ValueError("width and height must be in (0.0, 1.0]")
        if self.x + self.width > 1.0 + 1e-9 or self.y + self.height > 1.0 + 1e-9:
            raise ValueError("normalized box exceeds page boundaries")


@dataclass(frozen=True, slots=True)
class PixelBox:
    """Half-open pixel bounding box [left, right) x [top, bottom)."""

    left: int
    top: int
    right: int
    bottom: int

    def __post_init__(self) -> None:
        if self.left < 0 or self.top < 0:
            raise ValueError("pixel coordinates must be non-negative")
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("pixel box must have positive width and height")

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class BubbleMeasurement:
    """Measured interior fill statistics for a single OMR bubble."""

    option: str
    fill_ratio: float
    dark_pixels: int
    sampled_pixels: int
    mean_intensity: float
    sampled_box: PixelBox


def normalized_to_pixel_box(
    region: NormalizedBox,
    image_width: int,
    image_height: int,
) -> PixelBox:
    """Convert normalized top-left template coordinates into pixel bounds."""
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image_width and image_height must be positive")

    left = max(0, min(image_width - 1, round(region.x * image_width)))
    top = max(0, min(image_height - 1, round(region.y * image_height)))
    right = max(left + 1, min(image_width, round((region.x + region.width) * image_width)))
    bottom = max(top + 1, min(image_height, round((region.y + region.height) * image_height)))
    return PixelBox(left=left, top=top, right=right, bottom=bottom)


def apply_inset(box: PixelBox, inset_ratio: float = 0.15) -> PixelBox:
    """Shrink a bubble box inward to exclude printed border outlines."""
    if not 0.0 <= inset_ratio < 0.5:
        raise ValueError("inset_ratio must be in [0.0, 0.5)")

    dx = int(box.width * inset_ratio)
    dy = int(box.height * inset_ratio)

    left = box.left + dx
    right = box.right - dx
    top = box.top + dy
    bottom = box.bottom - dy

    if right <= left:
        mid_x = (box.left + box.right) // 2
        left, right = mid_x, mid_x + 1
    if bottom <= top:
        mid_y = (box.top + box.bottom) // 2
        top, bottom = mid_y, mid_y + 1

    return PixelBox(left=left, top=top, right=right, bottom=bottom)


def _validate_grayscale_image(image: Sequence[Sequence[int]]) -> tuple[int, int]:
    if not image:
        raise ValueError("image must contain at least one row")
    height = len(image)
    width = len(image[0])
    if width == 0:
        raise ValueError("image rows must be non-empty")
    for row in image:
        if len(row) != width:
            raise ValueError("image rows must all have equal width")
    return width, height


def measure_bubble_fill(
    image: Sequence[Sequence[int]],
    region: NormalizedBox,
    *,
    option: str = "",
    inset_ratio: float = 0.15,
    dark_threshold: int = 128,
) -> BubbleMeasurement:
    """Measure fill_ratio = dark_pixels / sampled_pixels inside the inset bubble ROI."""
    if not 0 <= dark_threshold <= 255:
        raise ValueError("dark_threshold must be between 0 and 255")

    width, height = _validate_grayscale_image(image)
    outer = normalized_to_pixel_box(region, width, height)
    sampled = apply_inset(outer, inset_ratio=inset_ratio)

    dark_pixels = 0
    intensity_sum = 0
    sampled_pixels = sampled.area

    for y in range(sampled.top, sampled.bottom):
        row = image[y]
        for x in range(sampled.left, sampled.right):
            pixel = row[x]
            if not 0 <= pixel <= 255:
                raise ValueError(f"pixel intensity {pixel} out of range [0, 255]")
            intensity_sum += pixel
            if pixel <= dark_threshold:
                dark_pixels += 1

    return BubbleMeasurement(
        option=option,
        fill_ratio=dark_pixels / sampled_pixels,
        dark_pixels=dark_pixels,
        sampled_pixels=sampled_pixels,
        mean_intensity=intensity_sum / sampled_pixels,
        sampled_box=sampled,
    )


def measure_question_bubbles(
    image: Sequence[Sequence[int]],
    bubble_regions: Mapping[str, NormalizedBox],
    *,
    inset_ratio: float = 0.15,
    dark_threshold: int = 128,
) -> list[tuple[str, float]]:
    """Measure all option bubbles for a question, returning (option, fill_ratio) pairs."""
    if not bubble_regions:
        raise ValueError("bubble_regions must not be empty")

    return [
        (
            option,
            measure_bubble_fill(
                image,
                region,
                option=option,
                inset_ratio=inset_ratio,
                dark_threshold=dark_threshold,
            ).fill_ratio,
        )
        for option, region in bubble_regions.items()
    ]
