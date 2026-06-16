"""棋盘格子视觉规范 — 每格可辨认、不抄版美术，自研科技风"""
from __future__ import annotations

from typing import Tuple

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF

from .board_data import TileDef, TileKind

# 玩家棋子色（与视口一致）
PLAYER_COLORS = [
    QColor(72, 220, 160),
    QColor(100, 180, 255),
    QColor(255, 150, 180),
    QColor(255, 200, 100),
]


def tile_icon(tile: TileDef) -> str:
    icons = {
        TileKind.START: "🏁",
        TileKind.CHANCE: "❓",
        TileKind.FATE: "🎴",
        TileKind.TAX: "💰",
        TileKind.JAIL: "🔒",
        TileKind.GO_TO_JAIL: "👮",
        TileKind.PARKING: "🅿",
        TileKind.PROPERTY: "🏙",
    }
    return icons.get(tile.kind, "▣")


def tile_subtitle(tile: TileDef) -> str:
    if tile.kind == TileKind.PROPERTY:
        return f"¥{tile.price}"
    if tile.kind == TileKind.TAX:
        return "税款"
    if tile.kind == TileKind.CHANCE:
        return "机会"
    if tile.kind == TileKind.FATE:
        return "命运"
    if tile.kind == TileKind.JAIL:
        return "监狱"
    if tile.kind == TileKind.GO_TO_JAIL:
        return "入狱"
    if tile.kind == TileKind.PARKING:
        return "停车"
    if tile.kind == TileKind.START:
        return "起点"
    return ""


def base_body_color(tile: TileDef) -> QColor:
    """地块主体（侧面/底座）。"""
    r, g, b = tile.color
    if tile.kind == TileKind.PROPERTY:
        return QColor(max(0, r - 40), max(0, g - 40), max(0, b - 40))
    return QColor(min(255, r + 20), min(255, g + 20), min(255, b + 20), 200)


def top_face_color(tile: TileDef, owned: bool) -> QColor:
    r, g, b = tile.color
    if tile.kind == TileKind.PROPERTY:
        c = QColor(r, g, b)
        return c.lighter(130) if owned else c.lighter(110)
    return QColor(r, g, b)


def group_band_color(tile: TileDef) -> QColor | None:
    if tile.kind != TileKind.PROPERTY or not tile.group:
        return None
    r, g, b = tile.color
    return QColor(min(255, r + 30), min(255, g + 30), min(255, b + 30))


def gl_top_rgb(tile: TileDef, owned: bool) -> Tuple[float, float, float]:
    c = top_face_color(tile, owned)
    scale = 1.15 if owned else 1.0
    return (c.red() / 255.0 * scale, c.green() / 255.0 * scale, c.blue() / 255.0 * scale)


def gl_body_rgb(tile: TileDef) -> Tuple[float, float, float]:
    c = base_body_color(tile)
    return (c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)


def gl_band_rgb(tile: TileDef) -> Tuple[float, float, float] | None:
    c = group_band_color(tile)
    if not c:
        return None
    return (c.red() / 255.0, c.green() / 255.0, c.blue() / 255.0)


def draw_tile_badge(
    painter: QPainter,
    cx: float,
    cy: float,
    tile: TileDef,
    *,
    owned: bool = False,
    level: int = 0,
    owner_color: QColor | None = None,
    highlight: bool = False,
    scale: float = 1.0,
) -> QRectF:
    """在屏幕坐标绘制一块可读的格子顶面，返回顶面区域。"""
    w = 64 * scale
    h = 46 * scale
    x = cx - w / 2
    y = cy - h / 2 - 6 * scale
    top_rect = QRectF(x, y, w, h)

    if highlight:
        painter.setPen(QPen(QColor(0, 220, 255, 230), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(x - 4, y - 4, w + 8, h + 8), 12, 12)

    body = base_body_color(tile)
    top = top_face_color(tile, owned)
    painter.setPen(QPen(QColor(20, 28, 42, 220), 1.5))
    painter.setBrush(body)
    painter.drawRoundedRect(top_rect, 9, 9)

    band = group_band_color(tile)
    if band:
        painter.setBrush(band)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(x + 3, y + 3, w - 6, 9 * scale), 5, 5)

    painter.setBrush(top)
    painter.setPen(QPen(QColor(255, 255, 255, 55), 1))
    painter.drawRoundedRect(QRectF(x + 4, y + 12 * scale, w - 8, h - 16 * scale), 7, 7)

    painter.setFont(QFont("Segoe UI Emoji", int(14 * scale)))
    painter.setPen(QColor(255, 255, 255))
    painter.drawText(QRectF(x, y + 10 * scale, w, 18 * scale), Qt.AlignmentFlag.AlignCenter, tile_icon(tile))

    painter.setFont(QFont("Microsoft YaHei UI", int(10 * scale), QFont.Weight.Bold))
    painter.setPen(QColor(248, 252, 255))
    name = tile.name if len(tile.name) <= 4 else tile.name[:3] + "…"
    painter.drawText(QRectF(x, y + 26 * scale, w, 14 * scale), Qt.AlignmentFlag.AlignCenter, name)

    painter.setFont(QFont("Microsoft YaHei UI", int(8 * scale), QFont.Weight.DemiBold))
    painter.setPen(QColor(200, 215, 240))
    sub = tile_subtitle(tile)
    if sub:
        painter.drawText(QRectF(x, y + h - 13 * scale, w, 12 * scale), Qt.AlignmentFlag.AlignCenter, sub)

    if owner_color is not None:
        painter.setBrush(owner_color)
        painter.setPen(QPen(QColor(255, 255, 255, 160), 1))
        painter.drawEllipse(QRectF(x + w - 13 * scale, y + 4, 9 * scale, 9 * scale))

    if level > 0:
        painter.setFont(QFont("Microsoft YaHei UI", int(8 * scale), QFont.Weight.Bold))
        painter.setPen(QColor(255, 230, 120))
        lbl = "店" if level >= 4 else "▪" * min(level, 3)
        painter.drawText(QRectF(x + 5, y + 4, 24, 12), Qt.AlignmentFlag.AlignLeft, lbl)

    return top_rect


def draw_tile_iso(
    painter: QPainter,
    cx: float,
    cy: float,
    tile: TileDef,
    *,
    owned: bool = False,
    level: int = 0,
    owner_color: QColor | None = None,
    highlight: bool = False,
    scale: float = 1.0,
) -> None:
    """2.5D 等距地块：阴影 + 立体侧壁 + 可读顶面。"""
    w = 64 * scale
    h = 46 * scale
    depth = 11 * scale
    skew = 6 * scale
    x = cx - w / 2
    y = cy - h / 2 - 6 * scale - depth

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 42))
    painter.drawEllipse(QRectF(cx - w * 0.44, cy + 5 * scale, w * 0.88, 15 * scale))

    body = base_body_color(tile)
    left_c = body.darker(155)
    right_c = body.darker(125)

    left_face = QPolygonF(
        [
            QPointF(x, y + h),
            QPointF(x - skew, y + h + depth),
            QPointF(x - skew, y + depth),
            QPointF(x, y),
        ]
    )
    painter.setBrush(left_c)
    painter.drawPolygon(left_face)

    right_face = QPolygonF(
        [
            QPointF(x + w, y + h),
            QPointF(x + w + skew, y + h + depth),
            QPointF(x + w + skew, y + depth),
            QPointF(x + w, y),
        ]
    )
    painter.setBrush(right_c)
    painter.drawPolygon(right_face)

    front_lip = QPolygonF(
        [
            QPointF(x, y + h),
            QPointF(x + w, y + h),
            QPointF(x + w + skew, y + h + depth),
            QPointF(x - skew, y + h + depth),
        ]
    )
    painter.setBrush(body.darker(135))
    painter.drawPolygon(front_lip)

    draw_tile_badge(
        painter,
        cx,
        cy - depth,
        tile,
        owned=owned,
        level=level,
        owner_color=owner_color,
        highlight=highlight,
        scale=scale,
    )


def draw_token_iso(painter: QPainter, cx: float, cy: float, color: QColor, label: str) -> None:
    """2.5D 棋子：底座阴影 + 立体圆棋。"""
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 50))
    painter.drawEllipse(QRectF(cx - 13, cy + 3, 26, 9))

    painter.setBrush(color.darker(140))
    painter.drawEllipse(QRectF(cx - 10, cy - 6, 20, 10))

    painter.setBrush(color)
    painter.setPen(QPen(QColor(255, 255, 255, 150), 1.5))
    painter.drawEllipse(QRectF(cx - 11, cy - 22, 22, 22))

    painter.setBrush(QColor(255, 255, 255, 90))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QRectF(cx - 5, cy - 18, 9, 7))

    painter.setFont(QFont("Microsoft YaHei UI", 9, QFont.Weight.Bold))
    painter.setPen(color.lighter(135))
    painter.drawText(QRectF(cx - 24, cy - 38, 48, 14), Qt.AlignmentFlag.AlignCenter, label)


def draw_board_platform(painter: QPainter, cx: float, cy: float, zoom: float = 1.0) -> None:
    """中央 2.5D 展台底座。"""
    pw, ph = 210 * zoom, 150 * zoom
    depth = 14 * zoom
    x, y = cx - pw / 2, cy - ph / 2 - depth

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 35))
    painter.drawEllipse(QRectF(cx - pw * 0.42, cy + ph * 0.22, pw * 0.84, 28 * zoom))

    side = QPolygonF(
        [
            QPointF(x, y + ph),
            QPointF(x + pw, y + ph),
            QPointF(x + pw, y + ph + depth),
            QPointF(x, y + ph + depth),
        ]
    )
    painter.setBrush(QColor(6, 10, 20, 240))
    painter.drawPolygon(side)

    painter.setPen(QPen(QColor(0, 170, 220, 70), 2))
    painter.setBrush(QColor(10, 18, 32, 235))
    painter.drawRoundedRect(QRectF(x, y, pw, ph), 18, 18)

    painter.setPen(QPen(QColor(0, 200, 255, 45), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(x + 8, y + 8, pw - 16, ph - 16), 14, 14)


def draw_center_logo(painter: QPainter, cx: float, cy: float) -> None:
    painter.setFont(QFont("Microsoft YaHei UI", 20, QFont.Weight.Bold))
    painter.setPen(QColor(0, 210, 255))
    painter.drawText(QRectF(cx - 80, cy - 30, 160, 36), Qt.AlignmentFlag.AlignCenter, "大富翁")
    painter.setFont(QFont("Microsoft YaHei UI", 10))
    painter.setPen(QColor(130, 155, 190))
    painter.drawText(QRectF(cx - 80, cy + 6, 160, 22), Qt.AlignmentFlag.AlignCenter, "中国城市巡回赛")
