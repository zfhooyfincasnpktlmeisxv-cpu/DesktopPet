"""接汉堡 — 左右移动接盘，接住美食躲开炸弹"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy

from ..utils.constants import GAME_THEME
from .base_game import BaseGameWidget
from .game_runtime import GameRenderMixin, paint_game_hud, paint_play_border


@dataclass
class FallingItem:
    x: float
    y: float
    vy: float
    kind: str  # "good" | "bad"
    size: int = 18
    alive: bool = True


class CatchGameWidget(BaseGameWidget, GameRenderMixin):
    PLAY_W = 352
    PLAY_H = 300
    HUD_HEIGHT = 28
    BASKET_W = 64
    BASKET_H = 22
    BASKET_SPEED = 7.5
    LOGIC_MS = 33
    MAX_LIVES = 3
    ROUND_SEC = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._init_render_loop(self._on_render)
        self._logic_timer = QTimer(self)
        self._logic_timer.timeout.connect(self._tick)
        self._items: List[FallingItem] = []
        self._basket_x = self.PLAY_W / 2 - self.BASKET_W / 2
        self._keys_left = False
        self._keys_right = False
        self._score = 0
        self._lives = self.MAX_LIVES
        self._time_left = self.ROUND_SEC
        self._spawn_cd = 0
        self._fall_speed = 2.2
        self._running = False
        self._finished = False

        h = self.HUD_HEIGHT + self.PLAY_H
        self.setMinimumSize(self.PLAY_W, h)
        self.setMaximumSize(self.PLAY_W, h)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def start_game(self) -> None:
        self._items.clear()
        self._basket_x = self.PLAY_W / 2 - self.BASKET_W / 2
        self._score = 0
        self._lives = self.MAX_LIVES
        self._time_left = self.ROUND_SEC
        self._spawn_cd = 0
        self._fall_speed = 2.2
        self._running = True
        self._finished = False
        self._logic_timer.start(self.LOGIC_MS)
        self._start_render()
        self.setFocus()
        self.game_event.emit("start", 0)

    def stop_game(self) -> None:
        self._logic_timer.stop()
        self._stop_render()
        self._running = False

    def score(self) -> int:
        return self._score

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self._keys_left = True
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self._keys_right = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self._keys_left = False
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self._keys_right = False
        super().keyReleaseEvent(event)

    def _on_render(self) -> None:
        self.update()

    def _tick(self) -> None:
        if not self._running:
            return

        dt = self.LOGIC_MS / 1000.0
        self._time_left -= dt
        if self._time_left <= 0:
            self._end_game(win=True)
            return

        if self._keys_left:
            self._basket_x -= self.BASKET_SPEED
        if self._keys_right:
            self._basket_x += self.BASKET_SPEED
        self._basket_x = max(0, min(self.PLAY_W - self.BASKET_W, self._basket_x))

        self._spawn_cd -= dt
        if self._spawn_cd <= 0:
            self._spawn_item()
            self._spawn_cd = random.uniform(0.35, 0.75) - min(self._score * 0.02, 0.25)

        basket_bottom = self.PLAY_H - 8
        basket_top = basket_bottom - self.BASKET_H
        basket_cx = self._basket_x + self.BASKET_W / 2
        catch_half_w = self.BASKET_W / 2 + 4

        for item in self._items:
            if not item.alive:
                continue
            item.y += item.vy
            if item.y > self.PLAY_H + 20:
                continue

            item_cx = item.x + item.size / 2
            item_cy = item.y + item.size / 2
            in_horizontal = abs(item_cx - basket_cx) <= catch_half_w
            # 物品中心进入接盘条区域才判定接住（避免在半空提前触发）
            in_vertical = basket_top + 4 <= item_cy <= basket_bottom - 2

            if in_horizontal and in_vertical:
                item.alive = False
                if item.kind == "good":
                    self._score += 1
                    self.game_event.emit("catch", self._score)
                    if self._score in (5, 10, 15):
                        self.game_event.emit(f"milestone_{self._score}", self._score)
                else:
                    self._lives -= 1
                    self.game_event.emit("danger", self._score)
                    if self._lives <= 0:
                        self._end_game(win=False)
                        return

        self._items = [it for it in self._items if it.alive and it.y < self.PLAY_H + 30]
        self._fall_speed = min(4.5, 2.2 + self._score * 0.08)

    def _spawn_item(self) -> None:
        kind = "bad" if random.random() < 0.22 else "good"
        x = random.uniform(20, self.PLAY_W - 40)
        vy = self._fall_speed + random.uniform(-0.3, 0.5)
        self._items.append(FallingItem(x=x, y=-20, vy=vy, kind=kind))

    def _end_game(self, win: bool) -> None:
        if self._finished:
            return
        self._finished = True
        self._running = False
        self._logic_timer.stop()
        self._stop_render()
        if win:
            self.game_event.emit("complete", self._score)
        else:
            self.game_event.emit("death", self._score)
        self.update()
        self.game_finished.emit(self._score)

    def paintEvent(self, _event) -> None:
        t = self._theme
        hud = self.HUD_HEIGHT
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(*t["background"]))

        left = f"得分 {self._score}  ❤ {self._lives}  ⏱ {max(0, int(self._time_left))}s"
        paint_game_hud(painter, t, self.PLAY_W, hud, left, self._fps_hud_text())
        paint_play_border(painter, t, 0, hud, self.PLAY_W, self.PLAY_H)

        for item in self._items:
            if not item.alive:
                continue
            cx, cy = int(item.x), int(item.y)
            if item.kind == "good":
                grad = QLinearGradient(cx, cy, cx + item.size, cy + item.size)
                grad.setColorAt(0, QColor(*t["food"]))
                grad.setColorAt(1, QColor(255, 100, 50))
            else:
                grad = QLinearGradient(cx, cy, cx + item.size, cy + item.size)
                grad.setColorAt(0, QColor(*t["danger"]))
                grad.setColorAt(1, QColor(180, 40, 60))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx, cy, item.size, item.size)
            painter.setFont(QFont(t["font_family"], 9))
            painter.setPen(QColor(255, 255, 255))
            sym = "🍔" if item.kind == "good" else "💣"
            painter.drawText(cx - 2, cy, item.size + 4, item.size + 4, Qt.AlignmentFlag.AlignCenter, sym)

        by = hud + self.PLAY_H - self.BASKET_H - 8
        bx = int(self._basket_x)
        basket_grad = QLinearGradient(bx, by, bx + self.BASKET_W, by + self.BASKET_H)
        basket_grad.setColorAt(0, QColor(*t["snake_head"]))
        basket_grad.setColorAt(1, QColor(*t["snake_body"]))
        painter.setBrush(basket_grad)
        painter.setPen(QPen(QColor(*t["panel_glow"]), 1.5))
        painter.drawRoundedRect(bx, by, self.BASKET_W, self.BASKET_H, 8, 8)

        if self._finished:
            overlay = QColor(14, 18, 28, 210)
            painter.fillRect(0, hud, self.PLAY_W, self.PLAY_H, overlay)
            painter.setPen(QColor(*t["text_accent"]))
            painter.setFont(QFont(t["font_family"], 14, QFont.Weight.Bold))
            msg = "时间到！大获全胜" if self._time_left <= 0 and self._lives > 0 else "游戏结束"
            painter.drawText(0, hud, self.PLAY_W, self.PLAY_H, Qt.AlignmentFlag.AlignCenter, msg)
