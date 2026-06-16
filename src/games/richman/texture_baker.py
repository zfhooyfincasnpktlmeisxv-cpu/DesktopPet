"""H5 级棋盘贴图烘焙 — 程序生成原创美术（渐变/高光/描边）"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .board_data import TileDef, TileKind, all_tiles
from .tile_style import tile_icon, tile_subtitle

ATLAS_COLS = 6
ATLAS_ROWS = 4
TILE_SIZE = 256

ASSETS_REL = Path("assets") / "richman" / "textures"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def textures_dir() -> Path:
    return _project_root() / ASSETS_REL


def _fonts() -> tuple:
    try:
        title = ImageFont.truetype("msyhbd.ttc", 28)
        body = ImageFont.truetype("msyh.ttc", 22)
        small = ImageFont.truetype("msyh.ttc", 16)
        tag = ImageFont.truetype("msyhbd.ttc", 14)
        emoji = ImageFont.truetype("seguiemj.ttf", 42)
    except OSError:
        try:
            title = ImageFont.truetype("msyh.ttc", 28)
            body = ImageFont.truetype("msyh.ttc", 22)
            small = ImageFont.truetype("msyh.ttc", 16)
            tag = ImageFont.truetype("msyh.ttc", 14)
            emoji = body
        except OSError:
            d = ImageFont.load_default()
            return d, d, d, d, d
    return title, body, small, tag, emoji


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _gradient_rect(
    draw: ImageDraw.ImageDraw,
    box: Tuple[int, int, int, int],
    c1: Tuple[int, int, int],
    c2: Tuple[int, int, int],
    vertical: bool = True,
) -> None:
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    for i in range(h if vertical else w):
        t = i / max(1, (h if vertical else w) - 1)
        c = (
            _lerp(c1[0], c2[0], t),
            _lerp(c1[1], c2[1], t),
            _lerp(c1[2], c2[2], t),
        )
        if vertical:
            draw.line([(x0, y0 + i), (x1, y0 + i)], fill=c)
        else:
            draw.line([(x0 + i, y0), (x0 + i, y1)], fill=c)


def _gloss_overlay(size: int = TILE_SIZE) -> Image.Image:
    gloss = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(gloss)
    d.ellipse([18, 8, size - 18, size // 2], fill=(255, 255, 255, 38))
    d.ellipse([size // 4, size // 5, size * 3 // 4, size // 2], fill=(255, 255, 255, 22))
    return gloss.filter(ImageFilter.GaussianBlur(6))


_GLOSS = None


def gloss_layer() -> Image.Image:
    global _GLOSS
    if _GLOSS is None:
        _GLOSS = _gloss_overlay()
    return _GLOSS


def _kind_accent(tile: TileDef) -> Tuple[int, int, int]:
    accents = {
        TileKind.START: (46, 210, 150),
        TileKind.CHANCE: (255, 186, 72),
        TileKind.FATE: (255, 120, 170),
        TileKind.TAX: (255, 96, 88),
        TileKind.JAIL: (148, 162, 188),
        TileKind.GO_TO_JAIL: (210, 72, 96),
        TileKind.PARKING: (108, 148, 210),
    }
    return accents.get(tile.kind, tile.color)


def _draw_pattern(d: ImageDraw.ImageDraw, tile: TileDef, inner: Tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = inner
    if tile.kind == TileKind.CHANCE:
        for i in range(-y1, x1, 18):
            d.line([(x0 + i, y0), (x0 + i + (y1 - y0), y1)], fill=(255, 255, 255, 18), width=2)
    elif tile.kind == TileKind.FATE:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        for r in range(20, 80, 18):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255, 24), width=2)
    elif tile.kind == TileKind.START:
        d.polygon(
            [(x0 + 20, y1 - 20), (x1 - 20, y1 - 20), (x1 - 40, y0 + 30), (x0 + 40, y0 + 30)],
            fill=(255, 255, 255, 20),
        )


def bake_tile_texture(tile: TileDef) -> Image.Image:
    title_f, body_f, small_f, tag_f, emoji_f = _fonts()
    img = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 外阴影
    shadow = Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle([14, 18, 242, 246], radius=28, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(shadow)

    # 外框
    d.rounded_rectangle([10, 12, 246, 244], radius=26, fill=(18, 24, 38, 255))
    d.rounded_rectangle([12, 14, 244, 242], radius=24, outline=(60, 80, 120, 180), width=2)

    accent = _kind_accent(tile)
    dark = (max(0, accent[0] - 50), max(0, accent[1] - 50), max(0, accent[2] - 50))
    band_box = (18, 18, 238, 62)
    _gradient_rect(d, band_box, accent, dark, vertical=False)

    if tile.kind == TileKind.PROPERTY and tile.group:
        d.text((24, 22), tile.group, fill=(255, 255, 255, 230), font=tag_f)

    inner = (20, 66, 236, 220)
    base = (
        min(255, accent[0] + 40),
        min(255, accent[1] + 40),
        min(255, accent[2] + 40),
    )
    deep = (max(0, accent[0] - 20), max(0, accent[1] - 20), max(0, accent[2] - 20))
    d.rounded_rectangle(inner, radius=20, fill=(*deep, 255))
    _gradient_rect(d, inner, base, deep, vertical=True)
    _draw_pattern(d, tile, inner)

    # 图标圆盘
    cx, cy = TILE_SIZE // 2, 118
    d.ellipse([cx - 44, cy - 44, cx + 44, cy + 44], fill=(255, 255, 255, 28))
    d.ellipse([cx - 40, cy - 40, cx + 40, cy + 40], fill=(12, 18, 30, 120))
    icon = tile_icon(tile)
    d.text((cx, cy), icon, fill=(255, 255, 255, 245), anchor="mm", font=emoji_f)

    # 城市名
    name = tile.name
    d.text((cx + 1, 171), name, fill=(0, 0, 0, 120), anchor="mm", font=title_f)
    d.text((cx, 170), name, fill=(248, 252, 255, 255), anchor="mm", font=title_f)

    sub = tile_subtitle(tile)
    if sub:
        pill_w = max(72, len(sub) * 14 + 24)
        px0 = cx - pill_w // 2
        d.rounded_rectangle([px0, 196, px0 + pill_w, 228], radius=14, fill=(0, 0, 0, 90))
        d.rounded_rectangle([px0 + 2, 198, px0 + pill_w - 2, 226], radius=12, fill=(0, 200, 255, 70))
        d.text((cx, 212), sub, fill=(230, 245, 255, 255), anchor="mm", font=small_f)

    img.alpha_composite(gloss_layer())
    return img


def bake_center_board() -> Image.Image:
    title_f, _, small_f, _, _ = _fonts()
    w, h = 512, 360
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, w - 8, h - 8], fill=(10, 16, 30, 240))
    d.ellipse([12, 12, w - 12, h - 12], outline=(0, 200, 255, 90), width=3)
    for r in range(40, 220, 36):
        d.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], outline=(0, 160, 220, 30), width=1)
    d.text((w // 2, h // 2 - 18), "大富翁", fill=(0, 220, 255, 255), anchor="mm", font=title_f)
    d.text((w // 2, h // 2 + 28), "中国城市巡回赛", fill=(140, 160, 190, 255), anchor="mm", font=small_f)
    gloss = gloss_layer().resize((w, h))
    img.alpha_composite(gloss)
    return img


def bake_atlas() -> Image.Image:
    atlas = Image.new("RGBA", (ATLAS_COLS * TILE_SIZE, ATLAS_ROWS * TILE_SIZE), (0, 0, 0, 0))
    for tile in all_tiles():
        cell = bake_tile_texture(tile)
        col = tile.index % ATLAS_COLS
        row = tile.index // ATLAS_COLS
        atlas.paste(cell, (col * TILE_SIZE, row * TILE_SIZE), cell)
    return atlas


def uv_rect(tile_index: int) -> Tuple[float, float, float, float]:
    col = tile_index % ATLAS_COLS
    row = tile_index // ATLAS_COLS
    u0 = col / ATLAS_COLS
    v0 = row / ATLAS_ROWS
    u1 = (col + 1) / ATLAS_COLS
    v1 = (row + 1) / ATLAS_ROWS
    return u0, v0, u1, v1


def bake_all_assets(force: bool = False) -> Path:
    out = textures_dir()
    out.mkdir(parents=True, exist_ok=True)
    atlas_path = out / "board_atlas.png"
    meta_path = out / "atlas_meta.json"
    center_path = out / "center_board.png"

    if force or not atlas_path.exists():
        bake_atlas().save(atlas_path)
    if force or not center_path.exists():
        bake_center_board().save(center_path)

    meta = {
        "tile_size": TILE_SIZE,
        "cols": ATLAS_COLS,
        "rows": ATLAS_ROWS,
        "tiles": {str(t.index): uv_rect(t.index) for t in all_tiles()},
    }
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return atlas_path


def tile_crop_rect(tile_index: int) -> Tuple[int, int, int, int]:
    col = tile_index % ATLAS_COLS
    row = tile_index // ATLAS_COLS
    return (
        col * TILE_SIZE,
        row * TILE_SIZE,
        (col + 1) * TILE_SIZE,
        (row + 1) * TILE_SIZE,
    )
