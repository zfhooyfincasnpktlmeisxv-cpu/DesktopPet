"""脚边状态条：饱食度、心情、亲密度等级（玻璃质感 + 渐变进度）"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)

from ..core.intimacy_levels import intimacy_level_progress
from ..utils.constants import STAT_HUD_THEME


def _clamp(value: int) -> float:
    return max(0.0, min(100.0, float(value)))


def _layout_metrics(scale: float) -> dict[str, float]:
    s = max(0.5, min(2.0, scale))
    return {
        "icon_w": max(13.0, 14.0 * s),
        "bar_w": max(38.0, 44.0 * s),
        "badge_w": max(46.0, 52.0 * s),
        "gap": max(7.0, 9.0 * s),
        "pad_x": max(6.0, 8.0 * s),
        "pad_y": max(3.0, 5.0 * s),
    }


def hud_height(scale: float) -> int:
    s = max(0.5, min(2.0, scale))
    return max(26, int(34 * s))


def hud_required_width(scale: float) -> int:
    """状态条所需最小宽度（通常宽于人物画布）。"""
    m = _layout_metrics(scale)
    inner = (
        m["icon_w"] * 2
        + m["bar_w"] * 2
        + m["badge_w"]
        + m["gap"] * 3
    )
    return int(inner + m["pad_x"] * 2 + 12)


def _pick_gradient(stops: dict[str, tuple], value: int) -> tuple[tuple, tuple]:
    if value <= 30:
        return stops["low"]
    if value <= 60:
        return stops["mid"]
    return stops["high"]


def _linear_brush(
    x: float,
    y: float,
    w: float,
    h: float,
    c0: tuple[int, int, int],
    c1: tuple[int, int, int],
    *,
    vertical: bool = False,
) -> QBrush:
    if vertical:
        grad = QLinearGradient(x, y, x, y + h)
    else:
        grad = QLinearGradient(x, y, x + w, y)
    grad.setColorAt(0.0, QColor(*c0))
    grad.setColorAt(1.0, QColor(*c1))
    return QBrush(grad)


def _rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    return path


def _draw_glass_panel(
    painter: QPainter,
    rect: QRectF,
    *,
    radius: float,
    theme: dict,
) -> None:
    shadow_off = theme["shadow_offset"]
    shadow_path = _rounded_path(
        rect.translated(shadow_off[0], shadow_off[1]),
        radius,
    )
    painter.fillPath(shadow_path, QColor(*theme["shadow"]))

    body_path = _rounded_path(rect, radius)
    bg = QColor(*theme["background"], int(theme["background_alpha"]))
    painter.fillPath(body_path, bg)

    gloss = QLinearGradient(rect.left(), rect.top(), rect.left(), rect.bottom())
    gloss.setColorAt(0.0, QColor(*theme["highlight_top"]))
    gloss.setColorAt(0.55, QColor(*theme["highlight_bottom"]))
    painter.fillPath(body_path, gloss)

    border = QColor(*theme["border"])
    painter.setPen(QPen(border, float(theme["border_width"])))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(body_path)


def _draw_premium_bar(
    painter: QPainter,
    x: float,
    y: float,
    width: float,
    height: float,
    value: int,
    *,
    grad_stops: dict[str, tuple[tuple, tuple]],
    theme: dict,
) -> None:
    radius = height / 2.0
    rect = QRectF(x, y, width, height)
    track_path = _rounded_path(rect, radius)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(*theme["track_inset"]))
    painter.drawPath(track_path)
    painter.setBrush(QColor(*theme["track"]))
    painter.drawPath(track_path)

    pct = _clamp(value) / 100.0
    fill_w = max(radius * 2.0, width * pct)
    if fill_w <= 0.5:
        return

    fill_rect = QRectF(x, y, fill_w, height)
    fill_path = _rounded_path(fill_rect, radius)

    c0, c1 = _pick_gradient(grad_stops, value)
    painter.setBrush(_linear_brush(x, y, fill_w, height, c0, c1))
    painter.drawPath(fill_path)

    gloss = QLinearGradient(x, y, x, y + height)
    gloss.setColorAt(0.0, QColor(255, 255, 255, 95))
    gloss.setColorAt(0.45, QColor(255, 255, 255, 28))
    gloss.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(gloss)
    painter.drawPath(fill_path)

    painter.setPen(QPen(QColor(255, 255, 255, 55), 0.8))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    inner = fill_rect.adjusted(0.6, 0.6, -0.6, -height * 0.52)
    if inner.width() > 2 and inner.height() > 1:
        painter.drawRoundedRect(inner, radius * 0.6, radius * 0.6)


def _draw_intimacy_badge(
    painter: QPainter,
    rect: QRectF,
    level: int,
    *,
    level_have: int = 0,
    level_need: int = 1,
    theme: dict,
    font: QFont,
    scale: float,
) -> None:
    radius = rect.height() / 2.0
    path = _rounded_path(rect, radius)

    bg0, bg1 = theme["badge_bg"]
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_linear_brush(rect.left(), rect.top(), rect.width(), rect.height(), bg0, bg1, vertical=True))
    painter.drawPath(path)

    accent = QColor(*theme["badge_accent"])
    border_grad = QLinearGradient(rect.left(), rect.top(), rect.right(), rect.bottom())
    border_grad.setColorAt(0.0, accent)
    border_grad.setColorAt(0.45, QColor(*theme["badge_border"]))
    border_grad.setColorAt(1.0, QColor(*theme["border"]))
    painter.setPen(QPen(QBrush(border_grad), 1.2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)

    star_size = max(7, int(8 * scale))
    star_font = QFont(font)
    star_font.setPointSize(star_size)
    star_font.setBold(True)
    lv_font = QFont(font)
    lv_font.setPointSize(max(7, int(7.5 * scale)))
    lv_font.setWeight(QFont.Weight.DemiBold)

    star_w = max(10.0, 11.0 * scale)
    star_rect = QRectF(rect.left() + 4 * scale, rect.top(), star_w, rect.height())
    lv_rect = QRectF(star_rect.right(), rect.top(), rect.width() - star_w - 5 * scale, rect.height())

    painter.setFont(star_font)
    painter.setPen(accent)
    painter.drawText(
        star_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        "✦",
    )

    painter.setFont(lv_font)
    painter.setPen(QColor(*theme["badge_text"]))
    painter.drawText(
        lv_rect,
        int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
        f"Lv.{level}",
    )

    if level_need > 0:
        prog_h = max(2.0, 2.5 * scale)
        prog_y = rect.bottom() - prog_h - 2 * scale
        prog_x = rect.left() + 5 * scale
        prog_w = rect.width() - 10 * scale
        track = QColor(*theme["track_inset"])
        fill_c = QColor(*theme["badge_accent"])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(QRectF(prog_x, prog_y, prog_w, prog_h), prog_h / 2, prog_h / 2)
        ratio = max(0.0, min(1.0, level_have / level_need))
        if ratio > 0:
            painter.setBrush(fill_c)
            painter.drawRoundedRect(
                QRectF(prog_x, prog_y, max(prog_h, prog_w * ratio), prog_h),
                prog_h / 2,
                prog_h / 2,
            )


def paint_stat_hud(
    painter: QPainter,
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    hunger: int,
    mood: int,
    intimacy: int,
    scale: float,
) -> None:
    """在人物画布下方绘制状态条。"""
    theme = STAT_HUD_THEME
    m = _layout_metrics(scale)
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    pad_x = max(4, int(m["pad_x"]))
    pad_y = max(3, int(m["pad_y"]))
    panel_rect = QRectF(x + 2, y + 1, width - 4, height - 3)
    radius = float(theme["radius"]) * max(0.85, min(1.15, scale * 0.95))

    _draw_glass_panel(painter, panel_rect, radius=radius, theme=theme)

    inner = panel_rect.adjusted(pad_x, pad_y, -pad_x, -pad_y)
    bar_h = max(5.0, 7.0 * scale)
    icon_w = m["icon_w"]
    bar_w = m["bar_w"]
    badge_w = m["badge_w"]
    gap = m["gap"]
    bar_y = inner.top() + (inner.height() - bar_h) / 2.0

    icon_font = QFont(theme["font_family"], max(8, int(9 * scale)))
    painter.setFont(icon_font)

    def draw_stat(col_x: float, emoji: str, value: int, grad_key: str) -> float:
        icon_rect = QRectF(col_x, inner.top(), icon_w, inner.height())
        painter.setPen(QColor(*theme["text_muted"]))
        painter.drawText(
            icon_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter),
            emoji,
        )
        _draw_premium_bar(
            painter,
            col_x + icon_w,
            bar_y,
            bar_w,
            bar_h,
            value,
            grad_stops=theme[grad_key],
            theme=theme,
        )
        return col_x + icon_w + bar_w

    x0 = inner.left()
    mood_x = draw_stat(x0, "🍖", hunger, "hunger_grad") + gap
    badge_x = draw_stat(mood_x, "♥", mood, "mood_grad") + gap

    badge_rect = QRectF(badge_x, inner.top(), badge_w, inner.height())
    lv, lv_have, lv_need = intimacy_level_progress(intimacy)
    _draw_intimacy_badge(
        painter,
        badge_rect,
        lv,
        level_have=lv_have,
        level_need=lv_need,
        theme=theme,
        font=QFont(theme["font_family"]),
        scale=scale,
    )

    painter.restore()
