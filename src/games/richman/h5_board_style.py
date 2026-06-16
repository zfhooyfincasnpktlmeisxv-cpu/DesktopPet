"""H5 大富翁棋盘美术 — 经典方形平铺，文字横排可读"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
    QRadialGradient,
)

from .board_data import TileDef, TileKind
from .city_images import draw_city_art

PLAYER_COLORS = [
    QColor(255, 120, 150),
    QColor(100, 180, 255),
    QColor(120, 220, 160),
    QColor(255, 200, 80),
]


def _tile_accent(tile: TileDef) -> QColor:
    r, g, b = tile.color
    return QColor(r, g, b)


def tile_kind_label(tile: TileDef) -> str:
    labels = {
        TileKind.START: "起点",
        TileKind.CHANCE: "机会",
        TileKind.FATE: "命运",
        TileKind.TAX: "税款",
        TileKind.JAIL: "监狱",
        TileKind.GO_TO_JAIL: "入狱",
        TileKind.PARKING: "停车",
    }
    return labels.get(tile.kind, tile.name)


def tile_kind_icon(tile: TileDef) -> str:
    icons = {
        TileKind.START: "🏁",
        TileKind.CHANCE: "?",
        TileKind.FATE: "?",
        TileKind.TAX: "💰",
        TileKind.JAIL: "🔒",
        TileKind.GO_TO_JAIL: "👮",
        TileKind.PARKING: "P",
    }
    return icons.get(tile.kind, "★")


def draw_forest_background(painter: QPainter, w: int, h: int) -> None:
    sky = QLinearGradient(0, 0, 0, h)
    sky.setColorAt(0.0, QColor(130, 205, 255))
    sky.setColorAt(0.4, QColor(170, 225, 185))
    sky.setColorAt(1.0, QColor(82, 158, 82))
    painter.fillRect(0, 0, w, h, sky)

    for tx, ty, sc in [(50, h - 70, 0.85), (w - 60, h - 75, 0.8), (w - 100, 55, 0.65), (70, 60, 0.7)]:
        _draw_tree(painter, tx, ty, sc)


def _draw_tree(painter: QPainter, x: float, y: float, scale: float) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(90, 55, 30))
    painter.drawRoundedRect(QRectF(x - 4 * scale, y, 8 * scale, 18 * scale), 2, 2)
    painter.setBrush(QColor(45, 135, 58))
    painter.drawEllipse(QRectF(x - 14 * scale, y - 22 * scale, 28 * scale, 24 * scale))


def draw_board_tray(painter: QPainter, x: float, y: float, w: float, h: float) -> None:
    """整块棋盘底板。"""
    depth = 6.0
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 35))
    painter.drawRoundedRect(QRectF(x + 4, y + depth + 4, w, h), 14, 14)

    lip = QPolygonF(
        [
            QPointF(x, y + h),
            QPointF(x + w, y + h),
            QPointF(x + w, y + h + depth),
            QPointF(x, y + h + depth),
        ]
    )
    painter.setBrush(QColor(120, 90, 60))
    painter.drawPolygon(lip)

    tray = QLinearGradient(x, y, x, y + h)
    tray.setColorAt(0.0, QColor(210, 175, 120))
    tray.setColorAt(1.0, QColor(175, 140, 90))
    painter.setBrush(tray)
    painter.setPen(QPen(QColor(140, 105, 65), 2))
    painter.drawRoundedRect(QRectF(x, y, w, h), 12, 12)


def draw_center_field(painter: QPainter, x: float, y: float, w: float, h: float, turn: int) -> None:
    field = QLinearGradient(x, y, x, y + h)
    field.setColorAt(0.0, QColor(215, 238, 158))
    field.setColorAt(1.0, QColor(180, 215, 105))
    painter.setBrush(field)
    painter.setPen(QPen(QColor(130, 170, 85), 2))
    painter.drawRoundedRect(QRectF(x, y, w, h), 10, 10)

    painter.setFont(QFont("Microsoft YaHei UI", max(14, int(min(w, h) * 0.14)), QFont.Weight.Bold))
    painter.setPen(QColor(55, 110, 45))
    painter.drawText(QRectF(x, y + h * 0.22, w, h * 0.22), Qt.AlignmentFlag.AlignCenter, "大富翁")

    painter.setFont(QFont("Microsoft YaHei UI", max(8, int(min(w, h) * 0.07))))
    painter.setPen(QColor(75, 125, 55))
    painter.drawText(QRectF(x, y + h * 0.44, w, h * 0.12), Qt.AlignmentFlag.AlignCenter, "中国城市巡回赛")

    bw, bh = min(w * 0.62, 120), 26
    bx, by = x + (w - bw) / 2, y + h * 0.66
    banner = QLinearGradient(bx, by, bx, by + bh)
    banner.setColorAt(0.0, QColor(255, 155, 195))
    banner.setColorAt(1.0, QColor(255, 105, 155))
    painter.setBrush(banner)
    painter.setPen(QPen(QColor(255, 225, 235), 1.5))
    painter.drawRoundedRect(QRectF(bx, by, bw, bh), 12, 12)
    painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(QRectF(bx, by, bw, bh), Qt.AlignmentFlag.AlignCenter, f"第 {turn} 轮")


def draw_h5_tile(
    painter: QPainter,
    cx: float,
    cy: float,
    tile: TileDef,
    *,
    cell: float,
    owned: bool = False,
    level: int = 0,
    owner_color: Optional[QColor] = None,
    owner_name: str = "",
    highlight: bool = False,
) -> None:
    """平铺地块：城市地标插画 + 醒目归属标识。"""
    tw = cell * 0.94
    th = cell * 0.94
    x = cx - tw / 2
    y = cy - th / 2
    accent = _tile_accent(tile)
    band_h = max(9.0, th * 0.18)
    ribbon_h = max(11.0, th * 0.2) if owned else 0.0
    art_top = y + band_h + 2
    art_bottom = y + th - (price_sz := max(7.0, th * 0.15)) - 6 - ribbon_h
    art_rect = QRectF(x + 3, art_top, tw - 6, max(8.0, art_bottom - art_top))

    if highlight:
        painter.setPen(QPen(QColor(255, 210, 40), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(x - 3, y - 3, tw + 6, th + 6), 6, 6)

    if owned and owner_color is not None:
        painter.setPen(QPen(owner_color, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(x - 2, y - 2, tw + 4, th + 4), 6, 6)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 28))
    painter.drawRoundedRect(QRectF(x + 2, y + 3, tw, th), 5, 5)

    body = QLinearGradient(x, y, x, y + th)
    body.setColorAt(0.0, QColor(255, 253, 248))
    body.setColorAt(1.0, QColor(242, 236, 225))
    painter.setBrush(body)
    painter.setPen(QPen(QColor(175, 165, 150), 1.2))
    painter.drawRoundedRect(QRectF(x, y, tw, th), 5, 5)

    painter.setBrush(accent)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(QRectF(x + 1.5, y + 1.5, tw - 3, band_h), 4, 4)

    name_sz = max(8, int(th * 0.17))
    if tile.kind == TileKind.PROPERTY:
        label = tile.name if len(tile.name) <= 4 else tile.name[:3] + "…"
        if tile.group:
            painter.setFont(QFont("Microsoft YaHei UI", max(6, int(band_h * 0.52)), QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(QRectF(x, y + 1, tw * 0.55, band_h), Qt.AlignmentFlag.AlignCenter, tile.group)
        painter.setFont(QFont("Microsoft YaHei UI", name_sz, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(x + tw * 0.42, y + 1, tw * 0.55, band_h), Qt.AlignmentFlag.AlignCenter, label)
    else:
        painter.setFont(QFont("Microsoft YaHei UI", max(6, int(band_h * 0.52)), QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(x, y + 1, tw, band_h), Qt.AlignmentFlag.AlignCenter, tile_kind_label(tile)[:4])

    draw_city_art(painter, tile, art_rect)

    if owned and owner_color is not None:
        tint = QColor(owner_color)
        tint.setAlpha(72)
        painter.fillRect(art_rect, tint)

    if tile.kind == TileKind.PROPERTY:
        painter.setFont(QFont("Microsoft YaHei UI", int(price_sz), QFont.Weight.Bold))
        painter.setPen(QColor(210, 75, 55))
        painter.drawText(QRectF(x, y + th - price_sz - 5 - ribbon_h, tw, price_sz + 2), Qt.AlignmentFlag.AlignCenter, f"¥{tile.price}")
    elif tile.name not in tile_kind_label(tile):
        painter.setFont(QFont("Microsoft YaHei UI", name_sz, QFont.Weight.Bold))
        painter.setPen(QColor(35, 35, 45))
        painter.drawText(QRectF(x, y + th - name_sz - 5 - ribbon_h, tw, name_sz + 2), Qt.AlignmentFlag.AlignCenter, tile.name[:4])

    if owned and owner_color is not None:
        ry = y + th - ribbon_h
        ribbon = QLinearGradient(x, ry, x + tw, ry)
        ribbon.setColorAt(0.0, owner_color.darker(115))
        ribbon.setColorAt(1.0, owner_color)
        painter.setBrush(ribbon)
        painter.setPen(QPen(QColor(255, 255, 255, 160), 1))
        painter.drawRoundedRect(QRectF(x + 2, ry + 1, tw - 4, ribbon_h - 2), 3, 3)

        badge = owner_name[:3] if owner_name else "?"
        painter.setFont(QFont("Microsoft YaHei UI", max(7, int(ribbon_h * 0.62)), QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(x + 2, ry + 1, tw - 4, ribbon_h - 2), Qt.AlignmentFlag.AlignCenter, f"◆ {badge}")

        dot = max(10.0, tw * 0.2)
        painter.setBrush(owner_color)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(QRectF(x - dot * 0.25, y - dot * 0.25, dot, dot))
        painter.setFont(QFont("Microsoft YaHei UI", max(6, int(dot * 0.45)), QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(x - dot * 0.25, y - dot * 0.25, dot, dot), Qt.AlignmentFlag.AlignCenter, badge[:1])

    if level > 0 and tile.kind == TileKind.PROPERTY:
        _draw_buildings(painter, cx, art_rect.bottom() - 4, level, accent, tw)


def _draw_buildings(painter: QPainter, cx: float, cy: float, level: int, color: QColor, tw: float) -> None:
    count = min(level, 4)
    bw = max(7.0, tw * 0.13)
    bh = max(9.0, tw * 0.18)
    start_x = cx - (count * (bw + 2)) / 2
    for i in range(count):
        bx = start_x + i * (bw + 2)
        h = bh + i * 2
        painter.setPen(QPen(color.darker(130), 1))
        painter.setBrush(color.lighter(110))
        painter.drawRoundedRect(QRectF(bx, cy - h, bw, h), 1, 1)


def draw_h5_token(
    painter: QPainter,
    cx: float,
    cy: float,
    color: QColor,
    label: str,
    *,
    is_current: bool = False,
    size: float = 22.0,
    avatar: Optional[QPixmap] = None,
) -> None:
    r = size / 2
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 45))
    painter.drawEllipse(QRectF(cx - r, cy + r * 0.55, size, size * 0.35))

    if avatar is not None and not avatar.isNull():
        painter.save()
        clip = QPainterPath()
        clip.addEllipse(QRectF(cx - r, cy - r, size, size))
        painter.setClipPath(clip)
        painter.drawPixmap(int(cx - r), int(cy - r), int(size), int(size), avatar)
        painter.restore()
        painter.setPen(QPen(color.lighter(120), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QRectF(cx - r, cy - r, size, size))
    else:
        grad = QRadialGradient(cx - r * 0.2, cy - r * 0.2, r * 1.2)
        grad.setColorAt(0.0, color.lighter(130))
        grad.setColorAt(1.0, color)
        painter.setBrush(grad)
        painter.setPen(QPen(QColor(255, 255, 255, 210), 2))
        painter.drawEllipse(QRectF(cx - r, cy - r, size, size))

        painter.setFont(QFont("Microsoft YaHei UI", max(7, int(size * 0.38)), QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(cx - r, cy - r, size, size), Qt.AlignmentFlag.AlignCenter, label[:2])

    if is_current:
        aw = size * 0.55
        arrow = QPolygonF(
            [
                QPointF(cx, cy - r - 6),
                QPointF(cx - aw / 2, cy - r - 20),
                QPointF(cx + aw / 2, cy - r - 20),
            ]
        )
        painter.setBrush(QColor(255, 255, 255, 240))
        painter.setPen(QPen(QColor(255, 90, 120), 2))
        painter.drawPolygon(arrow)
