"""美食记忆 — 限时翻牌配对"""
from __future__ import annotations

import random
from typing import List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy

from ..utils.constants import GAME_THEME
from .base_game import BaseGameWidget
from .game_runtime import GameRenderMixin, paint_game_hud, paint_play_border

CellIdx = int


class MemoryGameWidget(BaseGameWidget, GameRenderMixin):
    COLS = 4
    ROWS = 4
    CELL = 68
    GAP = 6
    HUD_HEIGHT = 28
    PAIRS = ("🍔", "🍕", "🍩", "🍰", "🍗", "🌮", "🍜", "🍦")
    TIME_LIMIT = 90.0
    FLIP_BACK_MS = 700

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._init_render_loop(self._on_render)
        self._logic_timer = QTimer(self)
        self._logic_timer.timeout.connect(self._tick_time)
        self._flip_timer = QTimer(self)
        self._flip_timer.setSingleShot(True)
        self._flip_timer.timeout.connect(self._flip_back)

        grid_w = self.COLS * self.CELL + (self.COLS - 1) * self.GAP
        grid_h = self.ROWS * self.CELL + (self.ROWS - 1) * self.GAP
        self._play_w = grid_w
        self._play_h = grid_h

        self._symbols: List[str] = []
        self._matched: List[bool] = []
        self._flipped: List[bool] = []
        self._first_pick: Optional[CellIdx] = None
        self._score = 0
        self._time_left = self.TIME_LIMIT
        self._input_locked = False
        self._running = False
        self._finished = False

        h = self.HUD_HEIGHT + self._play_h + 8
        self.setMinimumSize(self._play_w, h)
        self.setMaximumSize(self._play_w, h)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def start_game(self) -> None:
        symbols = list(self.PAIRS) * 2
        random.shuffle(symbols)
        self._symbols = symbols
        n = len(symbols)
        self._matched = [False] * n
        self._flipped = [False] * n
        self._first_pick = None
        self._score = 0
        self._time_left = self.TIME_LIMIT
        self._input_locked = False
        self._running = True
        self._finished = False
        self._logic_timer.start(200)
        self._start_render()
        self.setFocus()
        self.game_event.emit("start", 0)

    def stop_game(self) -> None:
        self._logic_timer.stop()
        self._flip_timer.stop()
        self._stop_render()
        self._running = False

    def score(self) -> int:
        return self._score

    def _on_render(self) -> None:
        self.update()

    def _tick_time(self) -> None:
        if not self._running or self._finished:
            return
        self._time_left -= 0.2
        if self._time_left <= 0:
            self._end_game(timeout=True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if not self._running or self._finished or self._input_locked:
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        idx = self._cell_at(event.position().x(), event.position().y())
        if idx is None or self._matched[idx] or self._flipped[idx]:
            return

        self._flipped[idx] = True
        if self._first_pick is None:
            self._first_pick = idx
            self.update()
            return

        if self._first_pick == idx:
            self._flipped[idx] = False
            self._first_pick = None
            self.update()
            return

        a, b = self._first_pick, idx
        if self._symbols[a] == self._symbols[b]:
            self._matched[a] = True
            self._matched[b] = True
            self._score += 1
            self._first_pick = None
            self.game_event.emit("match", self._score)
            if self._score in (4, 6, 8):
                self.game_event.emit(f"milestone_{self._score}", self._score)
            if self._score >= len(self.PAIRS):
                self._end_game(timeout=False, win=True)
        else:
            self._input_locked = True
            self.game_event.emit("mismatch", self._score)
            self._flip_timer.start(self.FLIP_BACK_MS)
        self.update()

    def _flip_back(self) -> None:
        if self._first_pick is not None:
            for i in range(len(self._symbols)):
                if not self._matched[i]:
                    self._flipped[i] = False
            self._first_pick = None
        self._input_locked = False
        self.update()

    def _cell_at(self, mx: float, my: float) -> Optional[CellIdx]:
        hud = self.HUD_HEIGHT + 4
        for row in range(self.ROWS):
            for col in range(self.COLS):
                x = col * (self.CELL + self.GAP)
                y = hud + row * (self.CELL + self.GAP)
                if x <= mx <= x + self.CELL and y <= my <= y + self.CELL:
                    return row * self.COLS + col
        return None

    def _cell_rect(self, idx: CellIdx) -> Tuple[int, int]:
        row, col = divmod(idx, self.COLS)
        x = col * (self.CELL + self.GAP)
        y = self.HUD_HEIGHT + 4 + row * (self.CELL + self.GAP)
        return x, y

    def _end_game(self, timeout: bool = False, win: bool = False) -> None:
        if self._finished:
            return
        self._finished = True
        self._running = False
        self._logic_timer.stop()
        self._flip_timer.stop()
        self._stop_render()
        if win:
            self.game_event.emit("complete", self._score)
        elif timeout:
            self.game_event.emit("death", self._score)
        self.update()
        self.game_finished.emit(self._score)

    def paintEvent(self, _event) -> None:
        t = self._theme
        hud = self.HUD_HEIGHT
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(*t["background"]))

        left = f"配对 {self._score}/{len(self.PAIRS)}  ⏱ {max(0, int(self._time_left))}s"
        paint_game_hud(painter, t, self._play_w, hud, left, self._fps_hud_text())

        py = hud + 4
        paint_play_border(painter, t, 0, py, self._play_w, self._play_h)

        for i in range(len(self._symbols)):
            cx, cy = self._cell_rect(i)
            show_face = self._flipped[i] or self._matched[i]
            if self._matched[i]:
                bg = QColor(30, 50, 70)
                border = QColor(*t["success"])
            elif show_face:
                bg = QColor(35, 48, 68)
                border = QColor(*t["accent"])
            else:
                bg = QColor(22, 30, 46)
                border = QColor(*t["surface_border"])

            painter.setBrush(bg)
            painter.setPen(QPen(border, 2))
            painter.drawRoundedRect(cx, cy, self.CELL, self.CELL, 10, 10)

            if show_face:
                painter.setFont(QFont(t["font_family"], 22))
                painter.setPen(QColor(*t["text"]))
                painter.drawText(cx, cy, self.CELL, self.CELL, Qt.AlignmentFlag.AlignCenter, self._symbols[i])
            else:
                painter.setPen(QColor(*t["text_muted"]))
                painter.setFont(QFont(t["font_family"], 11))
                painter.drawText(cx, cy, self.CELL, self.CELL, Qt.AlignmentFlag.AlignCenter, "?")

        if self._finished:
            overlay = QColor(14, 18, 28, 210)
            painter.fillRect(0, py, self._play_w, self._play_h, overlay)
            painter.setPen(QColor(*t["text_accent"]))
            painter.setFont(QFont(t["font_family"], 14, QFont.Weight.Bold))
            if self._score >= len(self.PAIRS):
                msg = "全部配对！太棒了！"
            elif self._time_left <= 0:
                msg = "时间到！"
            else:
                msg = "游戏结束"
            painter.drawText(0, py, self._play_w, self._play_h, Qt.AlignmentFlag.AlignCenter, msg)
