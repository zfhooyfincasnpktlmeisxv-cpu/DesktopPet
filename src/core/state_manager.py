"""
宠物状态管理器
管理饥饿度、心情值、亲密度，按分钟衰减 + 互动限速
"""
import logging
import time
from collections import deque
from typing import Deque, Optional, Dict, Any

from PyQt6.QtCore import QTimer, pyqtSignal, QObject

from ..utils.constants import (
    HUNGER_DECAY_PER_MINUTE,
    MOOD_DECAY_PER_MINUTE,
    INTIMACY_INCREMENT,
    FEED_HUNGER_BOOST,
    FEED_MOOD_BOOST,
    PET_MOOD_BOOST,
    HUNGER_LOW_THRESHOLD,
    MOOD_LOW_THRESHOLD,
    HUNGER_CRITICAL,
    INTERACTION_WINDOW_SEC,
    FEED_MAX_PER_MINUTE,
    PET_MAX_PER_MINUTE,
    INTIMACY_MAX_GAIN_PER_MINUTE,
    INTERACTION_DIMINISH_RATIO,
)

logger = logging.getLogger(__name__)

_TICKS_PER_MINUTE = 60


class _RollingEventCounter:
    """滚动时间窗口内的事件次数统计。"""

    def __init__(self, window_sec: float) -> None:
        self.window_sec = window_sec
        self._times: Deque[float] = deque()

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_sec
        while self._times and self._times[0] <= cutoff:
            self._times.popleft()

    def count(self, now: float) -> int:
        self._prune(now)
        return len(self._times)

    def record(self, now: float) -> None:
        self._prune(now)
        self._times.append(now)

    def has_capacity(self, now: float, limit: int) -> bool:
        return self.count(now) < limit


class _IntimacyGainTracker:
    """滚动窗口内好感度累计获取上限。"""

    def __init__(self, window_sec: float, max_gain: int) -> None:
        self.window_sec = window_sec
        self.max_gain = max_gain
        self._entries: Deque[tuple[float, int]] = deque()

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_sec
        while self._entries and self._entries[0][0] <= cutoff:
            self._entries.popleft()

    def gained(self, now: float) -> int:
        self._prune(now)
        return sum(amount for _, amount in self._entries)

    def try_gain(self, now: float, amount: int) -> int:
        if amount <= 0:
            return 0
        self._prune(now)
        allowed = max(0, self.max_gain - self.gained(now))
        actual = min(amount, allowed)
        if actual > 0:
            self._entries.append((now, actual))
        return actual


class StateManager(QObject):
    """
    宠物状态管理器
    管理饥饿度、心情值、亲密度，控制状态衰减
    """

    hunger_changed = pyqtSignal(int)
    mood_changed = pyqtSignal(int)
    intimacy_changed = pyqtSignal(int)
    state_critical = pyqtSignal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        self._hunger: int = 100
        self._mood: int = 100
        self._intimacy: int = 0

        self.hunger_decay_per_minute: float = float(HUNGER_DECAY_PER_MINUTE)
        self.mood_decay_per_minute: float = float(MOOD_DECAY_PER_MINUTE)

        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._tick)

        self._hunger_counter: float = 0.0
        self._mood_counter: float = 0.0

        self._hunger_was_critical: bool = False
        self._mood_was_low: bool = False

        window = float(INTERACTION_WINDOW_SEC)
        self._feed_events = _RollingEventCounter(window)
        self._pet_events = _RollingEventCounter(window)
        self._intimacy_gains = _IntimacyGainTracker(window, INTIMACY_MAX_GAIN_PER_MINUTE)

        self.tick_interval: int = 1000
        self.decay_timer.start(self.tick_interval)

        logger.info("状态管理器初始化完成")

    @property
    def hunger(self) -> int:
        return self._hunger

    @property
    def mood(self) -> int:
        return self._mood

    @property
    def intimacy(self) -> int:
        return self._intimacy

    @property
    def hunger_decay_rate(self) -> float:
        """兼容旧接口：返回每分钟衰减量。"""
        return self.hunger_decay_per_minute

    @property
    def mood_decay_rate(self) -> float:
        return self.mood_decay_per_minute

    def set_state(self, hunger: int, mood: int, intimacy: int) -> None:
        self._hunger = max(0, min(100, hunger))
        self._mood = max(0, min(100, mood))
        self._intimacy = max(0, intimacy)
        self._hunger_was_critical = self._hunger <= HUNGER_CRITICAL
        self._mood_was_low = self._mood <= MOOD_LOW_THRESHOLD

        self.hunger_changed.emit(self._hunger)
        self.mood_changed.emit(self._mood)
        self.intimacy_changed.emit(self._intimacy)

        logger.debug(
            "状态已设置: 饥饿=%s, 心情=%s, 亲密=%s",
            self._hunger,
            self._mood,
            self._intimacy,
        )

    def _apply_intimacy(self, now: float, amount: int) -> int:
        gained = self._intimacy_gains.try_gain(now, amount)
        if gained <= 0:
            return 0
        self._intimacy += gained
        self.intimacy_changed.emit(self._intimacy)
        return gained

    def feed(self) -> bool:
        """
        喂食：增加饥饿度和心情值；每分钟次数与好感获取均有限制。
        返回是否计为「完整喂食」。
        """
        now = time.monotonic()
        full_effect = self._feed_events.has_capacity(now, FEED_MAX_PER_MINUTE)

        ratio = 1.0 if full_effect else INTERACTION_DIMINISH_RATIO
        hunger_boost = int(FEED_HUNGER_BOOST * ratio)
        mood_boost = int(FEED_MOOD_BOOST * ratio)

        old_hunger = self._hunger
        old_mood = self._mood

        self._hunger = min(100, self._hunger + hunger_boost)
        self._mood = min(100, self._mood + mood_boost)

        if full_effect:
            self._feed_events.record(now)
            intimacy_gain = self._apply_intimacy(now, INTIMACY_INCREMENT)
        else:
            intimacy_gain = 0
            logger.debug("喂食过于频繁，仅少量恢复、无好感")

        if self._hunger != old_hunger:
            self.hunger_changed.emit(self._hunger)
        if self._mood != old_mood:
            self.mood_changed.emit(self._mood)

        logger.info(
            "喂食: 饥饿=%s 心情=%s 亲密=%s (完整=%s 好感+%s)",
            self._hunger,
            self._mood,
            self._intimacy,
            full_effect,
            intimacy_gain,
        )
        return full_effect

    def pet(self) -> bool:
        """
        抚摸：增加心情值；每分钟次数与好感获取均有限制。
        返回是否计为「完整抚摸」。
        """
        now = time.monotonic()
        full_effect = self._pet_events.has_capacity(now, PET_MAX_PER_MINUTE)

        ratio = 1.0 if full_effect else INTERACTION_DIMINISH_RATIO
        mood_boost = int(PET_MOOD_BOOST * ratio)

        old_mood = self._mood
        self._mood = min(100, self._mood + mood_boost)

        if full_effect:
            self._pet_events.record(now)
            intimacy_gain = self._apply_intimacy(now, INTIMACY_INCREMENT)
        else:
            intimacy_gain = 0
            logger.debug("抚摸过于频繁，仅少量恢复、无好感")

        if self._mood != old_mood:
            self.mood_changed.emit(self._mood)

        logger.info(
            "抚摸: 心情=%s 亲密=%s (完整=%s 好感+%s)",
            self._mood,
            self._intimacy,
            full_effect,
            intimacy_gain,
        )
        return full_effect

    def _tick(self) -> None:
        """每秒 tick，按「每分钟衰减量 / 60」累加。"""
        changed = False

        self._hunger_counter += self.hunger_decay_per_minute / _TICKS_PER_MINUTE
        if self._hunger_counter >= 1.0:
            decay = int(self._hunger_counter)
            self._hunger = max(0, self._hunger - decay)
            self._hunger_counter -= decay
            changed = True

            if self._hunger <= HUNGER_CRITICAL:
                if not self._hunger_was_critical:
                    self.state_critical.emit("hunger")
                    logger.warning("饥饿度处于临界值!")
                self._hunger_was_critical = True
            else:
                self._hunger_was_critical = False

        self._mood_counter += self.mood_decay_per_minute / _TICKS_PER_MINUTE
        if self._mood_counter >= 1.0:
            decay = int(self._mood_counter)
            self._mood = max(0, self._mood - decay)
            self._mood_counter -= decay
            changed = True

            if self._mood <= MOOD_LOW_THRESHOLD:
                if not self._mood_was_low:
                    self.state_critical.emit("mood")
                    logger.info("心情值较低")
                self._mood_was_low = True
            else:
                self._mood_was_low = False

        if changed:
            self.hunger_changed.emit(self._hunger)
            self.mood_changed.emit(self._mood)

    def get_mood_text(self) -> str:
        if self._hunger <= HUNGER_CRITICAL:
            return "hungry"
        if self._hunger < HUNGER_LOW_THRESHOLD or self._mood < MOOD_LOW_THRESHOLD:
            return "sad"
        if self._mood >= 80 and self._hunger >= 80:
            return "happy"
        return "normal"

    def should_play_sad_animation(self) -> bool:
        return self._hunger < HUNGER_LOW_THRESHOLD or self._mood < MOOD_LOW_THRESHOLD

    def should_show_hungry_bubble(self) -> bool:
        return self._hunger <= HUNGER_CRITICAL

    def reset_state(self) -> None:
        self._hunger = 100
        self._mood = 100
        self._intimacy = 0
        self._hunger_counter = 0.0
        self._mood_counter = 0.0
        self._feed_events = _RollingEventCounter(float(INTERACTION_WINDOW_SEC))
        self._pet_events = _RollingEventCounter(float(INTERACTION_WINDOW_SEC))
        self._intimacy_gains = _IntimacyGainTracker(
            float(INTERACTION_WINDOW_SEC),
            INTIMACY_MAX_GAIN_PER_MINUTE,
        )

        self.hunger_changed.emit(self._hunger)
        self.mood_changed.emit(self._mood)
        self.intimacy_changed.emit(self._intimacy)

        logger.info("状态已重置")

    def stop(self) -> None:
        self.decay_timer.stop()
        logger.info("状态管理器已停止")

    def get_state_dict(self) -> Dict[str, Any]:
        return {
            "hunger": self._hunger,
            "mood": self._mood,
            "intimacy": self._intimacy,
        }

    def set_decay_rates(self, hunger_rate: float, mood_rate: float) -> None:
        """设置每分钟衰减量。"""
        self.hunger_decay_per_minute = max(0.0, hunger_rate)
        self.mood_decay_per_minute = max(0.0, mood_rate)
        logger.debug(
            "衰减速度已设置: 饥饿=%s/分, 心情=%s/分",
            self.hunger_decay_per_minute,
            self.mood_decay_per_minute,
        )
