"""棋盘贴图加载（OpenGL + QPainter 共用）"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtOpenGL import QOpenGLTexture

from .texture_baker import (
    bake_all_assets,
    textures_dir,
    tile_crop_rect,
    uv_rect,
    ATLAS_COLS,
    ATLAS_ROWS,
    TILE_SIZE,
)

_atlas_image: Optional[QImage] = None
_atlas_pixmap: Optional[QPixmap] = None
_center_pixmap: Optional[QPixmap] = None


def ensure_textures(force: bool = False) -> Path:
    atlas = textures_dir() / "board_atlas.png"
    if force or not atlas.exists():
        bake_all_assets(force=True)
    return atlas


def _load_images() -> None:
    global _atlas_image, _atlas_pixmap, _center_pixmap
    ensure_textures()
    atlas_path = textures_dir() / "board_atlas.png"
    center_path = textures_dir() / "center_board.png"
    _atlas_image = QImage(str(atlas_path)).convertToFormat(QImage.Format.Format_RGBA8888)
    _atlas_pixmap = QPixmap.fromImage(_atlas_image)
    if center_path.exists():
        _center_pixmap = QPixmap(str(center_path))
    else:
        _center_pixmap = None


def atlas_qimage() -> QImage:
    if _atlas_image is None:
        _load_images()
    assert _atlas_image is not None
    return _atlas_image


def tile_pixmap(tile_index: int) -> QPixmap:
    if _atlas_pixmap is None:
        _load_images()
    assert _atlas_pixmap is not None
    x0, y0, x1, y1 = tile_crop_rect(tile_index)
    return _atlas_pixmap.copy(x0, y0, x1 - x0, y1 - y0)


def center_pixmap() -> Optional[QPixmap]:
    if _center_pixmap is None:
        _load_images()
    return _center_pixmap


def tile_uv(tile_index: int) -> Tuple[float, float, float, float]:
    return uv_rect(tile_index)


def create_atlas_texture(parent=None) -> QOpenGLTexture:
    del parent  # QOpenGLTexture 无 QObject 父级，由当前 GL 上下文管理
    img = atlas_qimage()
    tex = QOpenGLTexture(img)
    tex.setMinificationFilter(QOpenGLTexture.Filter.Linear)
    tex.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
    tex.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
    return tex


def create_center_texture(parent=None) -> Optional[QOpenGLTexture]:
    del parent
    pm = center_pixmap()
    if pm is None or pm.isNull():
        return None
    tex = QOpenGLTexture(pm.toImage())
    tex.setMinificationFilter(QOpenGLTexture.Filter.Linear)
    tex.setMagnificationFilter(QOpenGLTexture.Filter.Linear)
    tex.setWrapMode(QOpenGLTexture.WrapMode.ClampToEdge)
    return tex


def atlas_info() -> Dict[str, int]:
    return {"cols": ATLAS_COLS, "rows": ATLAS_ROWS, "tile_size": TILE_SIZE}
