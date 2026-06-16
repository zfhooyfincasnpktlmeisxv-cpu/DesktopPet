"""
对话气泡组件
自绘圆角气泡 + 尾巴，任意桌面背景下文字可读
"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QBrush,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPen,
    QColor,
    QTransform,
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QWidget

from ..utils.constants import (
    BUBBLE_ACCENT,
    BUBBLE_DURATION_MS,
    BUBBLE_THEME,
)

logger = logging.getLogger(__name__)


class SpeechBubble(QWidget):
    """宠物头顶对话气泡：实心底、描边、小尾巴、淡入/淡出。"""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.duration_ms: int = BUBBLE_DURATION_MS
        self.is_showing: bool = False
        self._text: str = ""
        self._style: str = "normal"
        self._pop_offset: float = 0.0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        theme = BUBBLE_THEME
        self._font = QFont(theme["font_family"], theme["font_size"])
        self._font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self._fade_step)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide)

        self._pop_timer = QTimer(self)
        self._pop_timer.timeout.connect(self._pop_step)
        self._pop_progress = 0.0

        self.hide()
        logger.info("对话气泡初始化完成")

    def dismiss(self) -> None:
        """立即关闭气泡（退出/隐藏宠物前必须调用）"""
        self.fade_timer.stop()
        self.hide_timer.stop()
        self._pop_timer.stop()
        self.opacity_effect.setOpacity(1.0)
        self._pop_offset = 0.0
        self._text = ""
        self.is_showing = False
        super().hide()

    def show_text(
        self,
        text: Optional[str],
        duration_ms: Optional[int] = None,
        *,
        style: str = "normal",
    ) -> None:
        if not text:
            return

        self.dismiss()

        self._text = text
        self._style = style if style in BUBBLE_ACCENT else "normal"
        self._layout_for_text(text)

        self.opacity_effect.setOpacity(0.0)
        self._pop_offset = 4.0
        self._pop_progress = 0.0
        self.is_showing = True

        self.show()
        self.raise_()
        self._pop_timer.start(16)

        duration = duration_ms or self.duration_ms
        fade_start = max(100, duration - 500)
        QTimer.singleShot(fade_start, self._start_fade)
        self.hide_timer.start(duration)

        logger.debug("显示气泡: %s (style=%s, %sms)", text, self._style, duration)

    def _layout_for_text(self, text: str) -> None:
        theme = BUBBLE_THEME
        max_w = int(theme["max_text_width"])
        pad_h = int(theme["padding_h"])
        pad_v = int(theme["padding_v"])
        tail_h = int(theme["tail_height"])
        shadow = int(theme["shadow_pad"])

        fm = QFontMetrics(self._font)
        bounds = fm.boundingRect(
            0,
            0,
            max_w,
            10000,
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            text,
        )
        text_w = max(24, bounds.width())
        text_h = max(fm.height(), bounds.height())

        body_w = text_w + pad_h * 2
        body_h = text_h + pad_v * 2
        total_w = body_w + shadow * 2
        total_h = body_h + tail_h + shadow * 2

        self.resize(total_w, total_h)
        self._shadow = shadow
        self._body_rect = QRectF(shadow, shadow, body_w, body_h)
        self._text_rect = QRectF(
            shadow + pad_h,
            shadow + pad_v,
            text_w,
            text_h,
        )
        self._tail_cx = shadow + body_w / 2.0

    def _bubble_path(self) -> QPainterPath:
        theme = BUBBLE_THEME
        radius = float(theme["radius"])
        tail_w = float(theme["tail_width"])
        tail_h = float(theme["tail_height"])
        body = self._body_rect
        cx = self._tail_cx
        half = tail_w / 2.0
        tip_y = body.bottom() + tail_h

        body_path = QPainterPath()
        body_path.addRoundedRect(body, radius, radius)

        tail_path = QPainterPath()
        tail_path.moveTo(cx - half, body.bottom() - 0.5)
        tail_path.lineTo(cx, tip_y)
        tail_path.lineTo(cx + half, body.bottom() - 0.5)
        tail_path.closeSubpath()
        return body_path.united(tail_path)

    def _border_color(self) -> QColor:
        accent = BUBBLE_ACCENT.get(self._style, BUBBLE_ACCENT["normal"])
        return QColor(*accent)

    def paintEvent(self, event) -> None:
        if not self._text:
            return

        theme = BUBBLE_THEME
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.translate(0, self._pop_offset)

        shadow_color = QColor(*theme["shadow"])
        path = self._bubble_path()

        shadow_path = QTransform.fromTranslate(1.5, 2.0).map(path)
        painter.fillPath(shadow_path, shadow_color)

        bg = QColor(*theme["background"], int(theme["background_alpha"]))
        painter.fillPath(path, QBrush(bg))

        border = self._border_color()
        painter.setPen(QPen(border, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.setPen(QColor(*theme["text"]))
        painter.setFont(self._font)
        painter.drawText(
            self._text_rect,
            int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
            self._text,
        )
        painter.end()

    def _start_pop_in(self) -> None:
        self._pop_progress = 0.0
        self._pop_timer.start(16)

    def _pop_step(self) -> None:
        self._pop_progress = min(1.0, self._pop_progress + 16 / 180.0)
        t = self._pop_progress
        # ease-out
        eased = 1.0 - (1.0 - t) ** 2
        self.opacity_effect.setOpacity(eased)
        self._pop_offset = 4.0 * (1.0 - eased)
        self.update()
        if self._pop_progress >= 1.0:
            self._pop_timer.stop()
            self._pop_offset = 0.0
            self.opacity_effect.setOpacity(1.0)

    def _start_fade(self) -> None:
        if not self.is_showing:
            return
        self._pop_timer.stop()
        self.fade_step = 0.05
        self.fade_timer.start(30)

    def _fade_step(self) -> None:
        opacity = self.opacity_effect.opacity() - self.fade_step
        if opacity <= 0:
            self.fade_timer.stop()
            opacity = 0.0
        self.opacity_effect.setOpacity(opacity)

    def hide(self) -> None:
        self.fade_timer.stop()
        self.hide_timer.stop()
        self._pop_timer.stop()
        self.opacity_effect.setOpacity(1.0)
        self._pop_offset = 0.0
        self._text = ""
        self.is_showing = False
        super().hide()
        logger.debug("气泡已隐藏")

    def set_duration(self, duration_ms: int) -> None:
        self.duration_ms = max(500, duration_ms)

    def move_above(self, parent_x: int, parent_y: int, parent_width: int) -> None:
        gap = int(BUBBLE_THEME["gap_above_pet"])
        bubble_x = parent_x + (parent_width - self.width()) // 2
        bubble_y = parent_y - self.height() - gap
        self.move(bubble_x, bubble_y)
