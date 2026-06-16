"""棋子逐格跳跃动画（3D / 2D 视口共用）"""
from __future__ import annotations

import math
from typing import Callable, Optional, Tuple

from PyQt6.QtCore import QObject, QTimer

Vec3 = Tuple[float, float, float]


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def hop_arc(t: float, peak: float) -> float:
    return math.sin(max(0.0, min(1.0, t)) * math.pi) * peak


class StepHopAnimator(QObject):
    """从一格平滑跳到下一格，带抛物线高度。"""

    def __init__(
        self,
        parent=None,
        frame_ms: int = 16,
        duration_ms: int = 480,
        hop_peak: float = 0.55,
    ):
        super().__init__(parent)
        self._duration_ms = max(120, duration_ms)
        self._hop_peak = hop_peak
        self._timer = QTimer(self)
        self._timer.setInterval(frame_ms)
        self._timer.timeout.connect(self._tick)
        self._t = 1.0
        self._start: Vec3 = (0.0, 0.0, 0.0)
        self._end: Vec3 = (0.0, 0.0, 0.0)
        self._on_update: Optional[Callable[[Vec3], None]] = None
        self._on_done: Optional[Callable[[], None]] = None

    def is_running(self) -> bool:
        return self._timer.isActive()

    def cancel(self) -> None:
        """停止当前跳跃，不触发 on_done。"""
        self._timer.stop()
        self._t = 1.0
        self._on_update = None
        self._on_done = None

    def start(
        self,
        start: Vec3,
        end: Vec3,
        on_update: Callable[[Vec3], None],
        on_done: Optional[Callable[[], None]] = None,
    ) -> None:
        self._start = start
        self._end = end
        self._on_update = on_update
        self._on_done = on_done
        self._t = 0.0
        self._timer.start()
        self._tick()

    def _pos_at(self, t: float) -> Vec3:
        e = smoothstep(t)
        base_y = self._start[1] + (self._end[1] - self._start[1]) * e
        return (
            self._start[0] + (self._end[0] - self._start[0]) * e,
            base_y + hop_arc(t, self._hop_peak),
            self._start[2] + (self._end[2] - self._start[2]) * e,
        )

    def _tick(self) -> None:
        self._t += self._timer.interval() / self._duration_ms
        if self._t >= 1.0:
            self._t = 1.0
            self._timer.stop()
            if self._on_update:
                self._on_update(self._pos_at(1.0))
            if self._on_done:
                self._on_done()
            return
        if self._on_update:
            self._on_update(self._pos_at(self._t))
