"""自动行为调度：眨眼、自主行走、睡眠"""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

logger = logging.getLogger(__name__)


class ActionScheduler(QObject):
    blink_requested = pyqtSignal()
    walk_requested = pyqtSignal()
    sleep_requested = pyqtSignal()

    def __init__(self, config: Dict[str, Any], auto_walk_enabled: bool = True, parent=None):
        super().__init__(parent)
        self._config = config
        self._auto_walk = auto_walk_enabled
        self._last_interaction = time.monotonic()

        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._on_blink)

        self._walk_timer = QTimer(self)
        self._walk_timer.setSingleShot(True)
        self._walk_timer.timeout.connect(self._on_walk)

        self._sleep_timer = QTimer(self)
        self._sleep_timer.timeout.connect(self._check_sleep)

    def start(self) -> None:
        self._schedule_blink(first=True)
        if self._auto_walk:
            self._schedule_walk(first=True)
        self._sleep_timer.start(1000)
        logger.info("动作调度器已启动 (walk=%s)", self._auto_walk)

    def stop(self) -> None:
        self._blink_timer.stop()
        self._walk_timer.stop()
        self._sleep_timer.stop()

    def record_interaction(self) -> None:
        now = time.monotonic()
        self._last_interaction = now
        self._schedule_blink()
        if self._auto_walk:
            self._walk_timer.stop()
            # 互动后稍等再走，别把走路排得太远
            cfg = self._config.get("walk", {})
            lo = int(cfg.get("rest_min_ms", 8000))
            hi = int(cfg.get("rest_max_ms", 15000))
            self._walk_timer.start(random.randint(lo, hi))

    def notify_walk_finished(self) -> None:
        """走完一段路后，随机待机再计划下一次走。"""
        if self._auto_walk:
            self._schedule_walk(after_trip=True)

    def set_auto_walk_enabled(self, enabled: bool) -> None:
        self._auto_walk = bool(enabled)
        if self._auto_walk:
            self._schedule_walk()
        else:
            self._walk_timer.stop()

    def _schedule_blink(self, *, first: bool = False) -> None:
        self._blink_timer.stop()
        cfg = self._config.get("blink", {})
        lo = int(cfg.get("min_interval_ms", 2000))
        hi = int(cfg.get("max_interval_ms", 5000))
        delay = random.randint(lo, hi)
        if first:
            delay = random.randint(lo // 2, hi // 2)
        self._blink_timer.start(delay)

    def _schedule_walk(self, *, first: bool = False, after_trip: bool = False) -> None:
        if not self._auto_walk:
            return
        self._walk_timer.stop()
        cfg = self._config.get("walk", {})
        if first:
            lo = int(cfg.get("first_delay_min_ms", 8000))
            hi = int(cfg.get("first_delay_max_ms", 22000))
        elif after_trip:
            lo = int(cfg.get("rest_min_ms", 8000))
            hi = int(cfg.get("rest_max_ms", max(lo + 1, 15000)))
        else:
            lo = int(cfg.get("min_interval_ms", 18000))
            hi = int(cfg.get("max_interval_ms", 55000))
        delay = random.randint(lo, hi)
        self._walk_timer.start(delay)
        logger.debug("下次走路约 %ds 后", delay // 1000)

    def _on_blink(self) -> None:
        self.blink_requested.emit()
        self._schedule_blink()

    def _on_walk(self) -> None:
        logger.info("调度器: 触发自主走路")
        self.walk_requested.emit()

    def schedule_walk_retry(self, *, delay_ms: int | None = None) -> None:
        """当前无法走路时，稍后再试。"""
        if not self._auto_walk:
            return
        self._walk_timer.stop()
        delay = delay_ms if delay_ms is not None else random.randint(4000, 12000)
        self._walk_timer.start(delay)
        logger.debug("走路推迟，约 %ds 后再试", delay // 1000)

    def _check_sleep(self) -> None:
        cfg = self._config.get("sleep", {})
        need = int(cfg.get("idle_duration_ms", 300000)) / 1000.0
        if time.monotonic() - self._last_interaction >= need:
            self.sleep_requested.emit()
