"""小游戏基类"""
from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget


class BaseGameWidget(QWidget):
    """可嵌入对话框的小游戏控件基类。"""

    game_finished = pyqtSignal(int)  # score（贪吃蛇为吃到食物数）
    game_event = pyqtSignal(str, int)  # 事件名, 附带数值（如得分）

    def start_game(self) -> None:
        """开始或重新开始一局。"""

    def stop_game(self) -> None:
        """停止计时器并释放输入。"""

    def set_render_fps(self, fps: int) -> None:
        """设置渲染帧率（30 或 60）。"""

    def set_vsync(self, enabled: bool) -> None:
        """开启垂直同步（与显示器刷新对齐）。"""
