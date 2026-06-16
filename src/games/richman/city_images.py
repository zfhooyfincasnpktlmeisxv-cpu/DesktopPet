"""城市地标照片加载与等比绘制"""
from __future__ import annotations

import json
import logging
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QLinearGradient, QPainter, QPainterPath, QPixmap, QColor

from .board_data import TileDef, TileKind
from .city_image_sources import CITY_IMAGE_SOURCES, ImageSource
from .city_landmarks import draw_city_landmark
from src.utils.constants import get_bundle_dir

logger = logging.getLogger(__name__)

_pixmap_cache: Dict[str, QPixmap] = {}
_loaded = False

ASSETS_REL = Path("assets") / "richman" / "cities"
USER_AGENT = "DesktopPet-Richman/1.0 (local cache; Pexels/Wikimedia)"
MIN_BYTES = 2048


def _project_root() -> Path:
    return get_bundle_dir()


def cities_dir() -> Path:
    return _project_root() / ASSETS_REL


def _lookup_key(tile: TileDef) -> Optional[str]:
    if tile.name in CITY_IMAGE_SOURCES:
        return tile.name
    if tile.kind == TileKind.CHANCE:
        return "机会"
    if tile.kind == TileKind.FATE:
        return "命运"
    if tile.kind == TileKind.TAX:
        return tile.name if tile.name in CITY_IMAGE_SOURCES else "所得税"
    if tile.kind == TileKind.JAIL:
        return "监狱"
    if tile.kind == TileKind.GO_TO_JAIL:
        return "进监狱"
    if tile.kind == TileKind.PARKING:
        return "免费停车"
    if tile.kind == TileKind.START:
        return "起点"
    return None


def _download_bytes(url: str) -> Optional[bytes]:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            data = resp.read()
        if len(data) < MIN_BYTES:
            return None
        return data
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.debug("下载失败 %s: %s", url[:80], exc)
        return None


def _download_one(key: str, src: ImageSource, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for url in src["urls"]:
        data = _download_bytes(url)
        if data:
            dest.write_bytes(data)
            logger.info("已下载城市图 %s -> %s", key, dest.name)
            return True
    return False


def ensure_city_images(force: bool = False) -> Path:
    """确保本地 cities/ 有所需图片；缺失则联网下载（Pexels 优先）。"""
    out = cities_dir()
    out.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, object] = {"sources": {}}

    for key, src in CITY_IMAGE_SOURCES.items():
        dest = out / src["file"]
        if force or not dest.exists() or dest.stat().st_size < MIN_BYTES:
            _download_one(key, src, dest)
        if dest.exists() and dest.stat().st_size >= MIN_BYTES:
            manifest["sources"][key] = {
                "file": src["file"],
                "license": src["license"],
                "credit": src["credit"],
                "urls": src["urls"],
            }

    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    _load_cache(clear=True)
    return out


def _load_cache(clear: bool = False) -> None:
    global _loaded
    if clear:
        _pixmap_cache.clear()
        _loaded = False
    if _loaded:
        return
    folder = cities_dir()
    for key, src in CITY_IMAGE_SOURCES.items():
        path = folder / src["file"]
        if path.exists() and path.stat().st_size >= MIN_BYTES:
            pm = QPixmap(str(path))
            if not pm.isNull():
                _pixmap_cache[key] = pm
    _loaded = True


def city_pixmap(tile: TileDef) -> Optional[QPixmap]:
    _load_cache()
    key = _lookup_key(tile)
    if not key:
        return None
    pm = _pixmap_cache.get(key)
    if pm is None or pm.isNull():
        return None
    return pm


def draw_city_art(painter: QPainter, tile: TileDef, art_rect: QRectF) -> None:
    """真实照片等比居中裁剪；无图则程序插画兜底。"""
    pm = city_pixmap(tile)
    if pm is None:
        draw_city_landmark(painter, tile, art_rect)
        return

    painter.save()
    clip = QPainterPath()
    clip.addRoundedRect(art_rect, 4, 4)
    painter.setClipPath(clip)

    tw = max(1, int(art_rect.width()))
    th = max(1, int(art_rect.height()))
    scaled = pm.scaled(
        tw,
        th,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    ox = (scaled.width() - tw) // 2
    oy = (scaled.height() - th) // 2
    painter.drawPixmap(int(art_rect.x()), int(art_rect.y()), scaled, ox, oy, tw, th)

    fade = QLinearGradient(art_rect.x(), art_rect.y(), art_rect.x(), art_rect.bottom())
    fade.setColorAt(0.0, QColor(0, 0, 0, 0))
    fade.setColorAt(0.5, QColor(0, 0, 0, 0))
    fade.setColorAt(1.0, QColor(0, 0, 0, 100))
    painter.fillRect(art_rect, fade)

    top = QLinearGradient(art_rect.x(), art_rect.y(), art_rect.x(), art_rect.y() + art_rect.height() * 0.3)
    top.setColorAt(0.0, QColor(255, 255, 255, 30))
    top.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.fillRect(art_rect, top)

    painter.restore()
