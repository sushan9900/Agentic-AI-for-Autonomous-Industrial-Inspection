"""Framework-independent preprocessing and nearest-neighbor mask resizing utilities."""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ImageResizeMode(str, Enum):
    """Image resizing strategy."""
    LETTERBOX = "letterbox"        # Preserves aspect ratio with constant padding
    DIRECT_RESIZE = "direct_resize" # Stretches/scales directly to target resolution


class ImageTransformMeta:
    """Metadata tracking spatial transformations for accurate coordinate inversion."""
    def __init__(
        self,
        orig_width: int,
        orig_height: int,
        target_width: int,
        target_height: int,
        scale: float,
        pad_x: int,
        pad_y: int,
        mode: ImageResizeMode
    ):
        self.orig_width = orig_width
        self.orig_height = orig_height
        self.target_width = target_width
        self.target_height = target_height
        self.scale = scale
        self.pad_x = pad_x
        self.pad_y = pad_y
        self.mode = mode

    def to_dict(self) -> Dict[str, Any]:
        return {
            "orig_width": self.orig_width,
            "orig_height": self.orig_height,
            "target_width": self.target_width,
            "target_height": self.target_height,
            "scale": self.scale,
            "pad_x": self.pad_x,
            "pad_y": self.pad_y,
            "mode": self.mode.value
        }


def compute_letterbox_geometry(
    orig_w: int,
    orig_h: int,
    target_w: int,
    target_h: int
) -> ImageTransformMeta:
    """Computes exact letterbox scaling factor and symmetric padding offsets."""
    scale = min(target_w / orig_w, target_h / orig_h)
    new_w = int(round(orig_w * scale))
    new_h = int(round(orig_h * scale))
    pad_x = (target_w - new_w) // 2
    pad_y = (target_h - new_h) // 2

    return ImageTransformMeta(
        orig_width=orig_w,
        orig_height=orig_h,
        target_width=target_w,
        target_height=target_h,
        scale=scale,
        pad_x=pad_x,
        pad_y=pad_y,
        mode=ImageResizeMode.LETTERBOX
    )


def nearest_neighbor_resize_2d(
    grid: List[List[int]],
    target_w: int,
    target_h: int
) -> List[List[int]]:
    """
    Resizes a 2D discrete mask grid using strict nearest-neighbor interpolation.
    Guarantees no floating-point blending or interpolated intermediate values.
    """
    orig_h = len(grid)
    if orig_h == 0:
        return []
    orig_w = len(grid[0])
    if orig_w == 0:
        return []

    output: List[List[int]] = [[0] * target_w for _ in range(target_h)]
    scale_x = orig_w / target_w
    scale_y = orig_h / target_h

    for ty in range(target_h):
        sy = min(int(ty * scale_y), orig_h - 1)
        for tx in range(target_w):
            sx = min(int(tx * scale_x), orig_w - 1)
            output[ty][tx] = grid[sy][sx]

    return output


def letterbox_mask_2d(
    grid: List[List[int]],
    target_w: int,
    target_h: int,
    pad_value: int = 0
) -> Tuple[List[List[int]], ImageTransformMeta]:
    """
    Applies aspect-ratio preserving letterbox padding to a 2D mask using nearest-neighbor scaling.
    """
    orig_h = len(grid)
    orig_w = len(grid[0]) if orig_h > 0 else 0
    geom = compute_letterbox_geometry(orig_w, orig_h, target_w, target_h)

    new_w = int(round(orig_w * geom.scale))
    new_h = int(round(orig_h * geom.scale))

    resized_core = nearest_neighbor_resize_2d(grid, new_w, new_h)

    # Embed into target canvas with pad_value
    canvas: List[List[int]] = [[pad_value] * target_w for _ in range(target_h)]
    for y in range(new_h):
        for x in range(new_w):
            canvas[y + geom.pad_y][x + geom.pad_x] = resized_core[y][x]

    return canvas, geom


def validate_binary_mask_discrete_values(
    grid: List[List[int]],
    allowed_values: Tuple[int, ...] = (0, 255)
) -> List[int]:
    """Returns any unexpected pixel values outside allowed discrete set."""
    unexpected = set()
    allowed_set = set(allowed_values)
    for row in grid:
        for val in row:
            if val not in allowed_set:
                unexpected.add(val)
    return sorted(list(unexpected))
