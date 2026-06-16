"""小游戏共享：渲染循环与 HUD 绘制"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter


class GameRenderMixin:
    """30/60 FPS 与垂直同步渲染定时器。"""

    def _init_render_loop(self, on_render) -> None:
        self._target_fps = 60
        self._vsync = True
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(on_render)
        self._apply_render_timer()

    def set_render_fps(self, fps: int) -> None:
        self._target_fps = 60 if fps >= 60 else 30
        self._apply_render_timer()

    def set_vsync(self, enabled: bool) -> None:
        self._vsync = enabled
        self._apply_render_timer()

    def _apply_render_timer(self) -> None:
        if self._vsync:
            fps = 60
            timer_type = Qt.TimerType.PreciseTimer
        else:
            fps = self._target_fps
            timer_type = Qt.TimerType.CoarseTimer
        interval = max(1, round(1000 / fps))
        self._render_timer.setTimerType(timer_type)
        self._render_timer.setInterval(interval)
        running = getattr(self, "_running", False)
        finished = getattr(self, "_finished", False)
        if running and not finished and not self._render_timer.isActive():
            self._render_timer.start()

    def _start_render(self) -> None:
        self._apply_render_timer()
        if not self._render_timer.isActive():
            self._render_timer.start()

    def _stop_render(self) -> None:
        self._render_timer.stop()

    def _fps_hud_text(self) -> str:
        if self._vsync:
            return "VSync"
        return f"{self._target_fps} FPS"


def paint_game_hud(
    painter: QPainter,
    theme: dict,
    width: int,
    hud_h: int,
    left_text: str,
    right_text: str,
) -> None:
    painter.fillRect(0, 0, width, hud_h, QColor(*theme["surface"]))
    painter.setPen(QColor(*theme["surface_border"]))
    painter.drawLine(0, hud_h, width, hud_h)
    painter.setPen(QColor(*theme["text_accent"]))
    painter.setFont(QFont(theme["font_family"], 10, QFont.Weight.Bold))
    painter.drawText(10, 0, width - 20, hud_h, Qt.AlignmentFlag.AlignVCenter, left_text)
    painter.setPen(QColor(*theme["text_muted"]))
    painter.setFont(QFont(theme["font_family"], 9))
    painter.drawText(
        0, 0, width - 10, hud_h,
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        right_text,
    )


def paint_play_border(painter: QPainter, theme: dict, x: int, y: int, w: int, h: int) -> None:
    from PyQt6.QtGui import QPen

    painter.fillRect(x, y, w, h, QColor(*theme["grid_bg"]))
    glow_pen = QPen(QColor(*theme["panel_glow"]))
    glow_pen.setWidth(2)
    painter.setPen(glow_pen)
    painter.drawRoundedRect(x + 1, y + 1, w - 2, h - 2, 6, 6)
