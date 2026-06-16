"""动画控制器：封装 AnimationManager"""
from __future__ import annotations

import logging
from typing import Callable, Optional

from PyQt6.QtGui import QPixmap

logger = logging.getLogger(__name__)


class AnimationController:
    def __init__(self, animation_manager):
        self._anim_mgr = animation_manager
        self._finished_callback: Optional[Callable[[str], None]] = None
        self._anim_mgr.animation_finished.connect(self._on_finished)

    def show_static_frame(self, anim_name: str, frame_index: int = 0) -> bool:
        return self._anim_mgr.show_static_frame(anim_name, frame_index)

    def play(
        self,
        anim_name: str,
        *,
        loop: bool = True,
        fps: Optional[int] = None,
        ping_pong: bool = False,
    ) -> bool:
        if fps is not None:
            self._anim_mgr.set_fps(fps)
        return self._anim_mgr.play(anim_name, loop=loop, ping_pong=ping_pong)

    def stop(self) -> None:
        self._anim_mgr.stop()

    def on_animation_finished(self, callback: Callable[[str], None]) -> None:
        self._finished_callback = callback

    def get_current_frame(self) -> Optional[QPixmap]:
        return self._anim_mgr.get_current_frame()

    def has_animation(self, anim_name: str) -> bool:
        return self._anim_mgr.has_animation(anim_name)

    def _on_finished(self, anim_name: str) -> None:
        if self._finished_callback:
            self._finished_callback(anim_name)

    @property
    def animation_manager(self):
        return self._anim_mgr
