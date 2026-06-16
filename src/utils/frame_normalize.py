"""动画帧裁剪与对齐 — 去除精灵图脏帧、统一画布"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PIL import Image

BBox = Tuple[int, int, int, int]


def alpha_bbox(image: Image.Image, threshold: int = 20) -> Optional[BBox]:
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    alpha = image.getchannel("A")
    return alpha.getbbox()


def normalize_sprite_frame(
    image: Image.Image,
    canvas_size: Tuple[int, int],
    *,
    max_bbox_height: Optional[int] = None,
    padding: int = 2,
) -> Optional[Image.Image]:
    """裁切透明边并居中贴回标准画布；过高 bbox 视为未切分的精灵图并丢弃。"""
    if image.mode != "RGBA":
        image = image.convert("RGBA")

    bbox = alpha_bbox(image)
    if not bbox:
        return None

    x0, y0, x1, y1 = bbox
    height = y1 - y0 + 1
    if max_bbox_height is not None and height > max_bbox_height:
        return None

    w, h = image.size
    x0 = max(0, x0 - padding)
    y0 = max(0, y0 - padding)
    x1 = min(w - 1, x1 + padding)
    y1 = min(h - 1, y1 + padding)
    cropped = image.crop((x0, y0, x1 + 1, y1 + 1))

    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    paste_x = (canvas_size[0] - cropped.width) // 2
    paste_y = (canvas_size[1] - cropped.height) // 2
    canvas.paste(cropped, (paste_x, paste_y), cropped)
    return canvas


def normalize_animation_frames(
    images: List[Image.Image],
    canvas_size: Tuple[int, int],
    *,
    max_bbox_height: Optional[int] = None,
) -> List[Image.Image]:
    out: List[Image.Image] = []
    for img in images:
        norm = normalize_sprite_frame(
            img,
            canvas_size,
            max_bbox_height=max_bbox_height,
        )
        if norm is not None:
            out.append(norm)
    return out
