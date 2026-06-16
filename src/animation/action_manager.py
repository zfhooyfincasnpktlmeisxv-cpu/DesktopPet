"""动作管理器：统一状态机驱动动画"""
from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ..utils.blink_overlay import BLINK_FRAME_COUNT
from .action_config import ActionConfig
from .action_scheduler import ActionScheduler
from .action_state import ActionPriority, ActionState
from .animation_controller import AnimationController

logger = logging.getLogger(__name__)


class ActionManager(QObject):
    state_changed = pyqtSignal(str, str)
    action_started = pyqtSignal(str)
    action_finished = pyqtSignal(str)
    blink_frame_changed = pyqtSignal(int)

    def __init__(
        self,
        animation_controller: AnimationController,
        config_path: str | None = None,
        auto_walk_enabled: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._anim = animation_controller
        self._config = ActionConfig(config_path)
        self._auto_walk = auto_walk_enabled
        self._scheduler: Optional[ActionScheduler] = None

        self._current = ActionState.IDLE
        self._previous = ActionState.IDLE
        self._safety_timer = QTimer(self)
        self._safety_timer.setSingleShot(True)
        self._safety_timer.timeout.connect(self._on_safety_timeout)

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._on_blink_tick)
        self._blink_frame = 0
        self._blink_playing = False

        self._anim.on_animation_finished(self._on_animation_finished)

    @property
    def current_state(self) -> str:
        return self._current

    @property
    def is_sleeping(self) -> bool:
        return self._current == ActionState.SLEEP

    @property
    def is_blinking(self) -> bool:
        return self._blink_playing

    @property
    def blink_frame(self) -> int:
        return self._blink_frame

    def start(self) -> None:
        self._scheduler = ActionScheduler(
            self._config.get_schedule_config(),
            self._auto_walk,
            self,
        )
        self._scheduler.blink_requested.connect(self._trigger_blink)
        self._scheduler.walk_requested.connect(self._trigger_walk)
        self._scheduler.sleep_requested.connect(self._trigger_sleep)
        self._scheduler.start()
        self._transition_to(ActionState.IDLE)

    def stop(self) -> None:
        self._clear_safety()
        self._stop_blink()
        if self._scheduler:
            self._scheduler.stop()

    def set_auto_walk_enabled(self, enabled: bool) -> None:
        self._auto_walk = bool(enabled)
        if self._scheduler:
            self._scheduler.set_auto_walk_enabled(enabled)

    def request_action(self, state: str) -> bool:
        if state == self._current:
            return True
        if not ActionPriority.can_interrupt(self._current, state):
            logger.debug("拒绝切换 %s -> %s", self._current, state)
            return False
        if not self._config.can_transition(self._current, state) and state != ActionState.IDLE:
            logger.debug("转换不允许 %s -> %s", self._current, state)
            return False
        self._transition_to(state)
        return True

    def force_idle(self) -> None:
        self._stop_blink()
        self._clear_safety()
        self._transition_to(ActionState.IDLE)

    def trigger_eat(self) -> None:
        if self._current == ActionState.SLEEP:
            return
        self.request_action(ActionState.EAT)

    def trigger_happy(self) -> None:
        if self._current == ActionState.SLEEP:
            return
        self.request_action(ActionState.HAPPY)

    def trigger_walk(self) -> None:
        self._trigger_walk()

    def wake_from_sleep(self) -> None:
        if self._current == ActionState.SLEEP:
            self.force_idle()

    def on_user_interaction(self) -> None:
        if self._current == ActionState.SLEEP:
            self.force_idle()
        if self._scheduler:
            self._scheduler.record_interaction()

    def pause_scheduler(self) -> None:
        """小游戏期间暂停随机走动/睡觉调度。"""
        if self._scheduler:
            self._scheduler.stop()

    def resume_scheduler(self) -> None:
        if self._scheduler:
            self._scheduler.start()
            # 退出小游戏后立刻恢复眨眼/溜达节奏，避免长时间“呆住”
            self._scheduler.record_interaction()

    def notify_walk_finished(self) -> None:
        if self._scheduler:
            self._scheduler.notify_walk_finished()

    def _transition_to(self, new_state: str) -> None:
        cfg = self._config.get_anim_config(new_state)
        old = self._current
        self._previous = old
        self._current = new_state

        self._clear_safety()
        self._stop_blink()

        if new_state == ActionState.BLINK:
            self._start_blink_overlay(cfg)
        else:
            self._play_body_anim(new_state, cfg)

        self._arm_safety(new_state, cfg)

        logger.info("动作: %s -> %s", old, new_state)
        self.state_changed.emit(old, new_state)
        self.action_started.emit(new_state)
        if old != ActionState.IDLE and new_state == ActionState.IDLE:
            self.action_finished.emit(old)

    def _play_body_anim(self, state: str, cfg: dict) -> None:
        anim = cfg.get("anim_name", state)
        if not self._anim.has_animation(anim):
            logger.warning("缺少动画 '%s'，降级 idle", anim)
            anim = "idle"
            if not self._anim.has_animation(anim):
                return

        fps = int(cfg.get("fps", 10))

        # 待机只用第一帧，避免 idle 目录多帧乱切
        if state == ActionState.IDLE:
            self._anim.show_static_frame(anim, 0)
            return

        loop = bool(cfg.get("loop", False))
        ping_pong = bool(cfg.get("ping_pong", False))
        self._anim.play(anim, loop=loop, fps=fps, ping_pong=ping_pong)

    def _start_blink_overlay(self, cfg: dict) -> None:
        fps = int(cfg.get("fps", 10))
        # 保持待机静帧，仅叠加眼睑动画
        self._anim.show_static_frame("idle", 0)
        self._blink_frame = 0
        self._blink_playing = True
        interval = max(8, int(1000 / fps))
        self._blink_timer.start(interval)
        self.blink_frame_changed.emit(0)

    def _on_blink_tick(self) -> None:
        self._blink_frame += 1
        self.blink_frame_changed.emit(self._blink_frame)
        if self._blink_frame >= BLINK_FRAME_COUNT - 1:
            self._stop_blink()
            if self._current == ActionState.BLINK:
                resume = self._previous
                if resume in (ActionState.BLINK, ActionState.WALK, ActionState.GRABBED):
                    resume = ActionState.IDLE
                self._transition_to(resume)

    def _stop_blink(self) -> None:
        self._blink_timer.stop()
        self._blink_playing = False
        self._blink_frame = 0

    def _arm_safety(self, state: str, cfg: dict) -> None:
        if state in (ActionState.IDLE, ActionState.WALK):
            return
        duration = int(cfg.get("duration_ms", -1))
        if duration <= 0:
            return
        self._safety_timer.start(duration + 500)

    def _clear_safety(self) -> None:
        self._safety_timer.stop()

    def _on_safety_timeout(self) -> None:
        if self._current != ActionState.IDLE:
            logger.warning("保险超时，强制 idle (was %s)", self._current)
            self._transition_to(ActionState.IDLE)

    def _on_animation_finished(self, anim_name: str) -> None:
        if self._current in (ActionState.CLICK, ActionState.HAPPY):
            self._transition_to(ActionState.IDLE)
        elif self._current == ActionState.EAT:
            self._transition_to(ActionState.IDLE)

    def _trigger_blink(self) -> None:
        if self._current in (ActionState.IDLE, ActionState.SAD):
            self.request_action(ActionState.BLINK)

    def _trigger_walk(self) -> None:
        if not self._auto_walk:
            return
        if self._current == ActionState.BLINK:
            if self._scheduler:
                self._scheduler.schedule_walk_retry(delay_ms=800)
            return
        if self._current not in (ActionState.IDLE, ActionState.SAD):
            if self._scheduler:
                self._scheduler.schedule_walk_retry()
            return
        self.request_action(ActionState.WALK)

    def _trigger_sleep(self) -> None:
        if self._current in (ActionState.IDLE,):
            self.request_action(ActionState.SLEEP)
