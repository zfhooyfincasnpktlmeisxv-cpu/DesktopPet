"""贪吃蛇小游戏（方向键 / WASD）— 深色科技风"""
from __future__ import annotations

import random
import time
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy

from ..utils.constants import GAME_THEME
from .base_game import BaseGameWidget

Cell = Tuple[int, int]


class SnakeGameWidget(BaseGameWidget):
    GRID_COLS = 16
    GRID_ROWS = 14
    CELL_SIZE = 22
    HUD_HEIGHT = 28
    LOGIC_TICK_MS = 140
    DANGER_COOLDOWN_S = 1.4
    LONG_SNAKE_LEN = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._logic_timer = QTimer(self)
        self._logic_timer.timeout.connect(self._tick)
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self._on_render)
        self._snake: List[Cell] = []
        self._direction: Cell = (1, 0)
        self._pending_dir: Cell | None = None
        self._food: Cell = (0, 0)
        self._score = 0
        self._running = False
        self._finished = False
        self._target_fps = 60
        self._vsync = True
        self._last_danger_at = 0.0
        self._was_in_danger = False
        self._long_feedback_done = False

        w = self.GRID_COLS * self.CELL_SIZE
        h = self.HUD_HEIGHT + self.GRID_ROWS * self.CELL_SIZE
        self.setMinimumSize(w, h)
        self.setMaximumSize(w, h)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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
        if self._running and not self._finished:
            if not self._render_timer.isActive():
                self._render_timer.start()

    def start_game(self) -> None:
        mid_y = self.GRID_ROWS // 2
        mid_x = self.GRID_COLS // 2
        self._snake = [(mid_x - 1, mid_y), (mid_x, mid_y), (mid_x + 1, mid_y)]
        self._direction = (1, 0)
        self._pending_dir = None
        self._score = 0
        self._running = True
        self._finished = False
        self._last_danger_at = 0.0
        self._was_in_danger = False
        self._long_feedback_done = False
        self._spawn_food()
        self._logic_timer.start(self.LOGIC_TICK_MS)
        self._render_timer.start()
        self.setFocus()
        self.game_event.emit("start", 0)
        self.update()

    def stop_game(self) -> None:
        self._logic_timer.stop()
        self._render_timer.stop()
        self._running = False

    def score(self) -> int:
        return self._score

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if not self._running:
            super().keyPressEvent(event)
            return

        key = event.key()
        mapping = {
            Qt.Key.Key_Up: (0, -1),
            Qt.Key.Key_Down: (0, 1),
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_W: (0, -1),
            Qt.Key.Key_S: (0, 1),
            Qt.Key.Key_A: (-1, 0),
            Qt.Key.Key_D: (1, 0),
        }
        new_dir = mapping.get(key)
        if new_dir and not self._is_opposite(new_dir, self._direction):
            self._pending_dir = new_dir
        super().keyPressEvent(event)

    def _on_render(self) -> None:
        if self._running and not self._finished:
            self._check_danger_feedback()
        self.update()

    def _is_opposite(self, a: Cell, b: Cell) -> bool:
        return a[0] == -b[0] and a[1] == -b[1]

    def _active_direction(self) -> Cell:
        if self._pending_dir is not None:
            return self._pending_dir
        return self._direction

    def _spawn_food(self) -> None:
        occupied = set(self._snake)
        free = [
            (x, y)
            for x in range(self.GRID_COLS)
            for y in range(self.GRID_ROWS)
            if (x, y) not in occupied
        ]
        self._food = random.choice(free) if free else (0, 0)

    def _predict_collision(self) -> bool:
        head_x, head_y = self._snake[-1]
        dx, dy = self._active_direction()
        new_head = (head_x + dx, head_y + dy)

        if (
            new_head[0] < 0
            or new_head[0] >= self.GRID_COLS
            or new_head[1] < 0
            or new_head[1] >= self.GRID_ROWS
        ):
            return True

        body = set(self._snake)
        will_eat = new_head == self._food
        if not will_eat and self._snake:
            body.discard(self._snake[0])
        return new_head in body

    def _check_danger_feedback(self) -> None:
        in_danger = self._predict_collision()
        now = time.monotonic()
        if in_danger and (now - self._last_danger_at) >= self.DANGER_COOLDOWN_S:
            self._last_danger_at = now
            self.game_event.emit("danger", self._score)
        self._was_in_danger = in_danger

    def _tick(self) -> None:
        if not self._running:
            return

        if self._pending_dir is not None:
            self._direction = self._pending_dir
            self._pending_dir = None

        head_x, head_y = self._snake[-1]
        dx, dy = self._direction
        new_head = (head_x + dx, head_y + dy)

        if (
            new_head[0] < 0
            or new_head[0] >= self.GRID_COLS
            or new_head[1] < 0
            or new_head[1] >= self.GRID_ROWS
            or new_head in self._snake
        ):
            self._end_game()
            return

        self._snake.append(new_head)
        if new_head == self._food:
            self._score += 1
            self._spawn_food()
            self.game_event.emit("food", self._score)
            if self._score == 3:
                self.game_event.emit("milestone_3", self._score)
            elif self._score == 5:
                self.game_event.emit("milestone_5", self._score)
            elif self._score == 10:
                self.game_event.emit("milestone_10", self._score)
            if len(self._snake) >= self.LONG_SNAKE_LEN and not self._long_feedback_done:
                self._long_feedback_done = True
                self.game_event.emit("long", self._score)
        else:
            self._snake.pop(0)

    def _end_game(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._running = False
        self._logic_timer.stop()
        self._render_timer.stop()
        self.game_event.emit("death", self._score)
        self.update()
        self.game_finished.emit(self._score)

    def paintEvent(self, _event) -> None:
        t = self._theme
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        hud_h = self.HUD_HEIGHT
        grid_w = self.GRID_COLS * self.CELL_SIZE
        grid_h = self.GRID_ROWS * self.CELL_SIZE

        painter.fillRect(self.rect(), QColor(*t["background"]))

        # 顶部 HUD（得分 / 帧率信息，不占用地图格子）
        painter.fillRect(0, 0, self.width(), hud_h, QColor(*t["surface"]))
        hud_pen = QPen(QColor(*t["surface_border"]))
        hud_pen.setWidth(1)
        painter.setPen(hud_pen)
        painter.drawLine(0, hud_h, self.width(), hud_h)

        score_color = QColor(*t["text_accent"])
        painter.setPen(score_color)
        painter.setFont(QFont(t["font_family"], 10, QFont.Weight.Bold))
        painter.drawText(10, 0, grid_w - 20, hud_h, Qt.AlignmentFlag.AlignVCenter, f"得分 {self._score}")

        fps_label = "60" if self._vsync else str(self._target_fps)
        painter.setPen(QColor(*t["text_muted"]))
        painter.setFont(QFont(t["font_family"], 9))
        vsync_txt = "VSync" if self._vsync else f"{fps_label} FPS"
        painter.drawText(
            0, 0, grid_w - 10, hud_h,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            vsync_txt,
        )

        # 游戏区背景
        painter.fillRect(0, hud_h, grid_w, grid_h, QColor(*t["grid_bg"]))

        glow_pen = QPen(QColor(*t["panel_glow"]))
        glow_pen.setWidth(2)
        painter.setPen(glow_pen)
        painter.drawRoundedRect(1, hud_h + 1, grid_w - 2, grid_h - 2, 6, 6)

        grid_pen = QPen(QColor(*t["grid_line"]))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for x in range(self.GRID_COLS + 1):
            painter.drawLine(
                x * self.CELL_SIZE,
                hud_h,
                x * self.CELL_SIZE,
                hud_h + grid_h,
            )
        for y in range(self.GRID_ROWS + 1):
            painter.drawLine(
                0,
                hud_h + y * self.CELL_SIZE,
                grid_w,
                hud_h + y * self.CELL_SIZE,
            )

        food_x = self._food[0] * self.CELL_SIZE
        food_y = hud_h + self._food[1] * self.CELL_SIZE
        pad = 4
        food_grad = QLinearGradient(food_x, food_y, food_x + self.CELL_SIZE, food_y + self.CELL_SIZE)
        food_grad.setColorAt(0, QColor(*t["food"]))
        food_grad.setColorAt(1, QColor(255, 100, 50))
        painter.setBrush(food_grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(
            food_x + pad,
            food_y + pad,
            self.CELL_SIZE - pad * 2,
            self.CELL_SIZE - pad * 2,
            6,
            6,
        )

        for i, (x, y) in enumerate(self._snake):
            cx = x * self.CELL_SIZE
            cy = hud_h + y * self.CELL_SIZE
            pad = 3
            is_head = i == len(self._snake) - 1
            grad = QLinearGradient(cx, cy, cx + self.CELL_SIZE, cy + self.CELL_SIZE)
            if is_head:
                grad.setColorAt(0, QColor(*t["snake_head"]))
                grad.setColorAt(1, QColor(0, 255, 220))
            else:
                grad.setColorAt(0, QColor(*t["snake_body"]))
                grad.setColorAt(1, QColor(0, 100, 160))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(
                cx + pad,
                cy + pad,
                self.CELL_SIZE - pad * 2,
                self.CELL_SIZE - pad * 2,
                5,
                5,
            )

        if self._finished:
            overlay = QColor(14, 18, 28, 210)
            painter.fillRect(0, hud_h, grid_w, grid_h, overlay)
            painter.setPen(QColor(*t["text_accent"]))
            painter.setFont(QFont(t["font_family"], 14, QFont.Weight.Bold))
            painter.drawText(
                0, hud_h, grid_w, grid_h,
                Qt.AlignmentFlag.AlignCenter,
                "游戏结束",
            )
