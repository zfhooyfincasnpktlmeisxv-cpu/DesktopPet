"""棋盘视觉特效 — 粒子、闪光、轻震屏"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPainter, QRadialGradient
from PyQt6.QtWidgets import QWidget


@dataclass
class _Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: QColor


class RichmanBoardFxOverlay(QWidget):
    """叠在棋盘视口上的透明特效层。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self._particles: List[_Particle] = []
        self._flash = 0.0
        self._flash_color = QColor(255, 220, 120, 0)
        self._shake_t = 0.0
        self._shake_amp = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._tile_flash: Optional[Tuple[float, float, float]] = None
        self.hide()

    def _set_active(self, active: bool) -> None:
        if active:
            self.show()
        else:
            self.hide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())

    def _tick(self) -> None:
        dt = 0.016
        alive: List[_Particle] = []
        for p in self._particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.x += p.vx * dt * 60
            p.y += p.vy * dt * 60
            p.vy += 0.35
            alive.append(p)
        self._particles = alive
        if self._flash > 0:
            self._flash = max(0.0, self._flash - dt * 2.2)
        if self._shake_t > 0:
            self._shake_t = max(0.0, self._shake_t - dt * 3.5)
        if self._tile_flash:
            x, y, t = self._tile_flash
            t -= dt * 2.0
            self._tile_flash = (x, y, t) if t > 0 else None
        if self._particles or self._flash > 0 or self._shake_t > 0 or self._tile_flash:
            self._set_active(True)
            self.update()
        else:
            self._timer.stop()
            self._set_active(False)

    def _ensure_timer(self) -> None:
        self._set_active(True)
        if not self._timer.isActive():
            self._timer.start()

    def burst(self, x: float, y: float, color: QColor, count: int = 18, spread: float = 4.5) -> None:
        self._ensure_timer()
        for _ in range(count):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(1.5, spread)
            self._particles.append(
                _Particle(
                    x,
                    y,
                    math.cos(ang) * spd,
                    math.sin(ang) * spd - 1.2,
                    random.uniform(0.35, 0.85),
                    0.85,
                    random.uniform(3.0, 7.0),
                    QColor(color),
                )
            )

    def flash(self, color: QColor, strength: float = 0.35) -> None:
        self._ensure_timer()
        self._flash = strength
        self._flash_color = color

    def shake(self, amp: float = 6.0, duration: float = 0.35) -> None:
        self._ensure_timer()
        self._shake_amp = amp
        self._shake_t = duration

    def tile_glow(self, x: float, y: float) -> None:
        self._ensure_timer()
        self._tile_flash = (x, y, 1.0)

    def confetti(self) -> None:
        self._ensure_timer()
        w, h = max(1, self.width()), max(1, self.height())
        colors = [
            QColor(255, 120, 150),
            QColor(100, 200, 255),
            QColor(255, 210, 80),
            QColor(120, 255, 180),
            QColor(200, 150, 255),
        ]
        for _ in range(120):
            self._particles.append(
                _Particle(
                    random.uniform(0, w),
                    random.uniform(-40, h * 0.3),
                    random.uniform(-2, 2),
                    random.uniform(2, 6),
                    random.uniform(1.2, 2.8),
                    2.8,
                    random.uniform(4, 9),
                    random.choice(colors),
                )
            )
        self.flash(QColor(255, 240, 200, 80), 0.5)

    def shake_offset(self) -> Tuple[float, float]:
        if self._shake_t <= 0:
            return 0.0, 0.0
        t = self._shake_t
        return (
            math.sin(t * 48) * self._shake_amp * (t / 0.35),
            math.cos(t * 40) * self._shake_amp * 0.6 * (t / 0.35),
        )

    def paintEvent(self, _event) -> None:
        if not (self._particles or self._flash > 0 or self._tile_flash):
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._flash > 0:
            c = QColor(self._flash_color)
            c.setAlpha(int(180 * self._flash))
            p.fillRect(self.rect(), c)
        if self._tile_flash:
            x, y, t = self._tile_flash
            r = 28 + (1.0 - t) * 18
            g = QRadialGradient(x, y, r)
            g.setColorAt(0.0, QColor(255, 230, 120, int(160 * t)))
            g.setColorAt(1.0, QColor(255, 230, 120, 0))
            p.setBrush(g)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(x - r), int(y - r), int(r * 2), int(r * 2))
        for pt in self._particles:
            alpha = int(255 * max(0, pt.life / pt.max_life))
            c = QColor(pt.color)
            c.setAlpha(alpha)
            p.setBrush(c)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(pt.x - pt.size / 2), int(pt.y - pt.size / 2), int(pt.size), int(pt.size))
