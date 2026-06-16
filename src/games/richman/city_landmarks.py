"""各城市地标插画 — 程序绘制，等比适配格子"""
from __future__ import annotations

from typing import Callable, Dict, Tuple

from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPolygonF, QRadialGradient

from .board_data import TileDef, TileKind

DrawFn = Callable[[QPainter, QRectF], None]

Sky = Tuple[int, int, int]
Ground = Tuple[int, int, int]


def _fit_rect(box: QRectF, aspect: float) -> QRectF:
    """在 box 内等比居中。"""
    bw, bh = box.width(), box.height()
    if bw / max(bh, 1) > aspect:
        h = bh
        w = h * aspect
    else:
        w = bw
        h = w / aspect
    return QRectF(box.x() + (bw - w) / 2, box.y() + (bh - h) / 2, w, h)


def _sky_ground(p: QPainter, r: QRectF, sky: Sky, ground: Ground) -> None:
    mid = r.y() + r.height() * 0.62
    grad = QLinearGradient(r.x(), r.y(), r.x(), r.bottom())
    grad.setColorAt(0.0, QColor(*sky))
    grad.setColorAt(0.55, QColor(*sky))
    grad.setColorAt(1.0, QColor(*ground))
    p.fillRect(r, grad)


def _draw_shanghai(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.35)
    _sky_ground(p, r, (120, 185, 230), (195, 210, 225))
    bx = r.x() + r.width() * 0.5
    base = r.y() + r.height() * 0.82
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(90, 100, 120))
    p.drawRect(QRectF(r.x() + r.width() * 0.08, base - r.height() * 0.18, r.width() * 0.84, r.height() * 0.18))
    # 东方明珠
    p.setBrush(QColor(220, 80, 100))
    p.drawEllipse(QRectF(bx - r.width() * 0.04, base - r.height() * 0.55, r.width() * 0.08, r.height() * 0.08))
    p.drawRect(QRectF(bx - r.width() * 0.015, base - r.height() * 0.52, r.width() * 0.03, r.height() * 0.36))
    p.drawEllipse(QRectF(bx - r.width() * 0.035, base - r.height() * 0.38, r.width() * 0.07, r.height() * 0.07))
    # 陆家嘴楼群
    for i, (ox, h, c) in enumerate([(-0.22, 0.32, (70, 130, 200)), (-0.1, 0.26, (100, 150, 210)), (0.12, 0.35, (60, 110, 180)), (0.24, 0.28, (85, 140, 200))]):
        p.setBrush(QColor(*c))
        p.drawRect(QRectF(bx + r.width() * ox, base - r.height() * h, r.width() * 0.09, r.height() * h))


def _draw_beijing(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.4)
    _sky_ground(p, r, (140, 200, 240), (180, 60, 50))
    base = r.y() + r.height() * 0.78
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(180, 50, 45))
    p.drawRect(QRectF(r.x() + r.width() * 0.12, base - r.height() * 0.22, r.width() * 0.76, r.height() * 0.22))
    # 天坛穹顶
    cx = r.x() + r.width() * 0.5
    p.setBrush(QColor(40, 140, 200))
    p.drawEllipse(QRectF(cx - r.width() * 0.18, base - r.height() * 0.48, r.width() * 0.36, r.height() * 0.22))
    p.setBrush(QColor(200, 60, 50))
    p.drawRect(QRectF(cx - r.width() * 0.06, base - r.height() * 0.3, r.width() * 0.12, r.height() * 0.12))


def _draw_guangzhou(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.3)
    _sky_ground(p, r, (100, 175, 230), (90, 150, 90))
    base = r.y() + r.height() * 0.8
    cx = r.x() + r.width() * 0.52
    p.setPen(Qt.PenStyle.NoPen)
    # 广州塔
    p.setBrush(QColor(255, 140, 60))
    path = QPolygonF(
        [
            QPointF(cx, base - r.height() * 0.62),
            QPointF(cx - r.width() * 0.04, base - r.height() * 0.08),
            QPointF(cx + r.width() * 0.04, base - r.height() * 0.08),
        ]
    )
    p.drawPolygon(path)
    p.setBrush(QColor(70, 120, 180))
    p.drawRect(QRectF(r.x() + r.width() * 0.15, base - r.height() * 0.25, r.width() * 0.2, r.height() * 0.25))
    p.drawRect(QRectF(r.x() + r.width() * 0.62, base - r.height() * 0.2, r.width() * 0.18, r.height() * 0.2))


def _draw_shenzhen(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.35)
    _sky_ground(p, r, (90, 165, 225), (210, 220, 230))
    base = r.y() + r.height() * 0.82
    p.setPen(Qt.PenStyle.NoPen)
    towers = [(0.12, 0.42, (50, 90, 160)), (0.28, 0.55, (70, 120, 190)), (0.45, 0.38, (40, 80, 150)), (0.62, 0.48, (60, 110, 175)), (0.76, 0.35, (80, 130, 200))]
    for ox, h, c in towers:
        p.setBrush(QColor(*c))
        p.drawRect(QRectF(r.x() + r.width() * ox, base - r.height() * h, r.width() * 0.1, r.height() * h))


def _draw_hangzhou(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.5)
    _sky_ground(p, r, (150, 205, 240), (100, 175, 130))
    water = r.y() + r.height() * 0.58
    p.fillRect(QRectF(r.x(), water, r.width(), r.height() * 0.42), QColor(80, 160, 200, 180))
    cx = r.x() + r.width() * 0.55
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(200, 80, 70))
    p.drawPolygon(
        QPolygonF(
            [
                QPointF(cx, water - r.height() * 0.28),
                QPointF(cx - r.width() * 0.12, water),
                QPointF(cx + r.width() * 0.12, water),
            ]
        )
    )
    p.setBrush(QColor(60, 130, 80))
    p.drawEllipse(QRectF(r.x() + r.width() * 0.1, water + r.height() * 0.08, r.width() * 0.22, r.height() * 0.1))


def _draw_nanjing(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.35)
    _sky_ground(p, r, (130, 190, 235), (140, 130, 120))
    base = r.y() + r.height() * 0.8
    cx = r.x() + r.width() * 0.5
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(70, 70, 85))
    p.drawRect(QRectF(cx - r.width() * 0.2, base - r.height() * 0.35, r.width() * 0.4, r.height() * 0.35))
    p.setBrush(QColor(180, 60, 50))
    p.drawPolygon(
        QPolygonF(
            [
                QPointF(cx, base - r.height() * 0.48),
                QPointF(cx - r.width() * 0.14, base - r.height() * 0.35),
                QPointF(cx + r.width() * 0.14, base - r.height() * 0.35),
            ]
        )
    )


def _draw_chengdu(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.4)
    _sky_ground(p, r, (160, 210, 245), (120, 180, 100))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(50, 120, 60))
    for ox in (0.1, 0.35, 0.7):
        p.drawRect(QRectF(r.x() + r.width() * ox, r.y() + r.height() * 0.35, r.width() * 0.04, r.height() * 0.45))
    p.setBrush(QColor(240, 240, 245))
    p.drawEllipse(QRectF(r.x() + r.width() * 0.28, r.y() + r.height() * 0.52, r.width() * 0.18, r.height() * 0.16))
    p.setBrush(QColor(30, 30, 35))
    p.drawEllipse(QRectF(r.x() + r.width() * 0.33, r.y() + r.height() * 0.55, r.width() * 0.04, r.height() * 0.04))
    p.drawEllipse(QRectF(r.x() + r.width() * 0.39, r.y() + r.height() * 0.55, r.width() * 0.04, r.height() * 0.04))


def _draw_xian(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.35)
    _sky_ground(p, r, (200, 170, 140), (160, 120, 90))
    base = r.y() + r.height() * 0.78
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(150, 110, 80))
    p.drawRect(QRectF(r.x() + r.width() * 0.2, base - r.height() * 0.3, r.width() * 0.6, r.height() * 0.3))
    p.setBrush(QColor(180, 140, 100))
    for i in range(3):
        p.drawEllipse(QRectF(r.x() + r.width() * (0.28 + i * 0.14), base - r.height() * 0.42, r.width() * 0.1, r.height() * 0.12))


def _draw_wuhan(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.3)
    _sky_ground(p, r, (120, 185, 230), (100, 150, 200))
    base = r.y() + r.height() * 0.8
    cx = r.x() + r.width() * 0.5
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(200, 170, 80))
    p.drawPolygon(
        QPolygonF(
            [
                QPointF(cx, base - r.height() * 0.5),
                QPointF(cx - r.width() * 0.16, base - r.height() * 0.12),
                QPointF(cx + r.width() * 0.16, base - r.height() * 0.12),
            ]
        )
    )
    p.setBrush(QColor(80, 140, 200, 150))
    p.drawRect(QRectF(r.x(), base - r.height() * 0.12, r.width(), r.height() * 0.12))


def _draw_suzhou(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.45)
    _sky_ground(p, r, (165, 210, 240), (110, 165, 110))
    water = r.y() + r.height() * 0.62
    p.fillRect(QRectF(r.x(), water, r.width(), r.height() * 0.38), QColor(90, 150, 190, 160))
    cx = r.x() + r.width() * 0.45
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(180, 70, 65))
    p.drawPolygon(
        QPolygonF(
            [
                QPointF(cx, water - r.height() * 0.22),
                QPointF(cx - r.width() * 0.1, water - r.height() * 0.05),
                QPointF(cx + r.width() * 0.1, water - r.height() * 0.05),
            ]
        )
    )
    p.setBrush(QColor(70, 120, 70))
    p.drawEllipse(QRectF(r.x() + r.width() * 0.62, water - r.height() * 0.08, r.width() * 0.15, r.height() * 0.08))


def _draw_tianjin(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.35)
    _sky_ground(p, r, (130, 195, 235), (170, 190, 210))
    base = r.y() + r.height() * 0.78
    cx = r.x() + r.width() * 0.5
    p.setPen(QPen(QColor(200, 80, 90), 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QRectF(cx - r.width() * 0.2, base - r.height() * 0.42, r.width() * 0.4, r.height() * 0.4))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(90, 130, 180))
    p.drawRect(QRectF(cx - r.width() * 0.03, base - r.height() * 0.35, r.width() * 0.06, r.height() * 0.35))


def _draw_chongqing(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.4)
    grad = QLinearGradient(r.x(), r.y(), r.x(), r.bottom())
    grad.setColorAt(0.0, QColor(100, 160, 210))
    grad.setColorAt(1.0, QColor(60, 90, 70))
    p.fillRect(r, grad)
    p.setPen(Qt.PenStyle.NoPen)
    for i, h in enumerate([0.35, 0.5, 0.65]):
        p.setBrush(QColor(50 + i * 15, 80 + i * 10, 60 + i * 8))
        p.drawPolygon(
            QPolygonF(
                [
                    QPointF(r.x(), r.y() + r.height() * h),
                    QPointF(r.x() + r.width() * 0.7, r.y() + r.height() * (h - 0.12)),
                    QPointF(r.right(), r.y() + r.height() * (h + 0.05)),
                    QPointF(r.x() + r.width() * 0.3, r.y() + r.height() * (h + 0.1)),
                ]
            )
        )
    p.setBrush(QColor(220, 180, 80))
    p.drawRect(QRectF(r.x() + r.width() * 0.35, r.y() + r.height() * 0.55, r.width() * 0.3, r.height() * 0.04))


def _draw_hongkong(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.35)
    _sky_ground(p, r, (90, 150, 220), (40, 80, 140))
    base = r.y() + r.height() * 0.75
    p.setPen(Qt.PenStyle.NoPen)
    p.fillRect(QRectF(r.x(), base, r.width(), r.height() * 0.25), QColor(30, 70, 130, 200))
    for ox, h in [(0.1, 0.35), (0.25, 0.5), (0.42, 0.42), (0.58, 0.55), (0.72, 0.38)]:
        p.setBrush(QColor(220, 200, 120))
        p.drawRect(QRectF(r.x() + r.width() * ox, base - r.height() * h, r.width() * 0.1, r.height() * h))


def _draw_taipei(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.3)
    _sky_ground(p, r, (120, 185, 235), (100, 160, 110))
    base = r.y() + r.height() * 0.8
    cx = r.x() + r.width() * 0.5
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(90, 150, 210))
    p.drawRect(QRectF(cx - r.width() * 0.06, base - r.height() * 0.55, r.width() * 0.12, r.height() * 0.55))
    for i, y in enumerate([0.45, 0.58, 0.7]):
        p.setBrush(QColor(220, 180, 60))
        p.drawEllipse(QRectF(cx - r.width() * 0.1, base - r.height() * y, r.width() * 0.2, r.height() * 0.06))


def _draw_start(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.4)
    grad = QLinearGradient(r.x(), r.y(), r.right(), r.bottom())
    grad.setColorAt(0.0, QColor(90, 220, 160))
    grad.setColorAt(1.0, QColor(50, 180, 130))
    p.fillRect(r, grad)
    p.setPen(QPen(QColor(255, 255, 255, 180), 2))
    for i in range(4):
        y = r.y() + r.height() * (0.25 + i * 0.15)
        p.drawLine(QPointF(r.x() + r.width() * 0.1, y), QPointF(r.x() + r.width() * 0.9, y))


def _draw_chance(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.2)
    p.fillRect(r, QColor(255, 210, 120))
    card = QRectF(r.x() + r.width() * 0.18, r.y() + r.height() * 0.12, r.width() * 0.64, r.height() * 0.76)
    p.setBrush(QColor(255, 245, 220))
    p.setPen(QPen(QColor(220, 160, 60), 2))
    p.drawRoundedRect(card, 6, 6)
    p.setPen(QColor(255, 220, 40))
    p.setFont(QFont("Microsoft YaHei UI", max(14, int(r.height() * 0.35)), QFont.Weight.Bold))
    p.drawText(card, Qt.AlignmentFlag.AlignCenter, "?")


def _draw_fate(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.0)
    p.fillRect(r, QColor(255, 150, 190))
    cx, cy = r.center().x(), r.center().y()
    rad = min(r.width(), r.height()) * 0.38
    p.setBrush(QColor(255, 230, 245))
    p.setPen(QPen(QColor(220, 80, 140), 2))
    p.drawEllipse(QRectF(cx - rad, cy - rad, rad * 2, rad * 2))
    p.setPen(QColor(200, 60, 120))
    p.drawLine(QPointF(cx, cy - rad * 0.6), QPointF(cx, cy + rad * 0.6))
    p.drawLine(QPointF(cx - rad * 0.6, cy), QPointF(cx + rad * 0.6, cy))


def _draw_tax(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.3)
    p.fillRect(r, QColor(255, 170, 140))
    cx = r.center().x()
    p.setBrush(QColor(255, 220, 80))
    p.setPen(QPen(QColor(200, 150, 40), 2))
    p.drawEllipse(QRectF(cx - r.width() * 0.22, r.y() + r.height() * 0.28, r.width() * 0.44, r.height() * 0.44))
    p.setBrush(QColor(255, 200, 60))
    p.drawEllipse(QRectF(cx - r.width() * 0.14, r.y() + r.height() * 0.36, r.width() * 0.28, r.height() * 0.28))


def _draw_jail(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.3)
    p.fillRect(r, QColor(120, 130, 155))
    p.setPen(QPen(QColor(60, 70, 90), 3))
    for i in range(5):
        x = r.x() + r.width() * (0.15 + i * 0.17)
        p.drawLine(QPointF(x, r.y() + r.height() * 0.15), QPointF(x, r.y() + r.height() * 0.85))


def _draw_parking(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.4)
    _sky_ground(p, r, (150, 200, 240), (130, 175, 120))
    p.setBrush(QColor(100, 160, 220))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(r.x() + r.width() * 0.2, r.y() + r.height() * 0.45, r.width() * 0.6, r.height() * 0.28), 4, 4)
    p.setBrush(QColor(220, 80, 70))
    p.drawRoundedRect(QRectF(r.x() + r.width() * 0.28, r.y() + r.height() * 0.52, r.width() * 0.44, r.height() * 0.14), 3, 3)


def _draw_go_jail(p: QPainter, box: QRectF) -> None:
    r = _fit_rect(box, 1.3)
    p.fillRect(r, QColor(180, 70, 90))
    p.setPen(QPen(QColor(40, 40, 50), 2))
    p.setBrush(QColor(80, 90, 110))
    p.drawRect(QRectF(r.x() + r.width() * 0.25, r.y() + r.height() * 0.2, r.width() * 0.5, r.height() * 0.6))
    p.setPen(QPen(QColor(200, 200, 210), 2))
    for i in range(3):
        x = r.x() + r.width() * (0.35 + i * 0.1)
        p.drawLine(QPointF(x, r.y() + r.height() * 0.25), QPointF(x, r.y() + r.height() * 0.75))


_CITY_DRAW: Dict[str, DrawFn] = {
    "天津": _draw_tianjin,
    "重庆": _draw_chongqing,
    "上海": _draw_shanghai,
    "南京": _draw_nanjing,
    "杭州": _draw_hangzhou,
    "苏州": _draw_suzhou,
    "武汉": _draw_wuhan,
    "成都": _draw_chengdu,
    "西安": _draw_xian,
    "广州": _draw_guangzhou,
    "深圳": _draw_shenzhen,
    "北京": _draw_beijing,
    "香港": _draw_hongkong,
    "台北": _draw_taipei,
}

_KIND_DRAW: Dict[TileKind, DrawFn] = {
    TileKind.START: _draw_start,
    TileKind.CHANCE: _draw_chance,
    TileKind.FATE: _draw_fate,
    TileKind.TAX: _draw_tax,
    TileKind.JAIL: _draw_jail,
    TileKind.PARKING: _draw_parking,
    TileKind.GO_TO_JAIL: _draw_go_jail,
}


def draw_city_landmark(painter: QPainter, tile: TileDef, art_rect: QRectF) -> None:
    painter.save()
    painter.setClipRect(art_rect.adjusted(1, 1, -1, -1))
    fn = _CITY_DRAW.get(tile.name)
    if fn is None and tile.kind in _KIND_DRAW:
        fn = _KIND_DRAW[tile.kind]
    if fn is None:
        painter.fillRect(art_rect, QColor(220, 225, 235))
    else:
        fn(painter, art_rect)
    painter.restore()
