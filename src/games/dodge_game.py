"""流星躲避 — 在星雨中存活，越久得分越高"""
from __future__ import annotations

import math
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
class Star:
    x: float
    y: float
    speed: float
    size: float
    layer: int


@dataclass
class Asteroid:
    x: float
    y: float
    vx: float
    vy: float
    radius: float


class DodgeGameWidget(BaseGameWidget, GameRenderMixin):
    PLAY_W = 352
    PLAY_H = 308
    HUD_HEIGHT = 28
    PLAYER_R = 9
    LOGIC_MS = 33
    MOVE_SPEED = 4.2

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._init_render_loop(self._on_render)
        self._logic_timer = QTimer(self)
        self._logic_timer.timeout.connect(self._tick)
        self._stars: List[Star] = []
        self._asteroids: List[Asteroid] = []
        self._px = self.PLAY_W / 2
        self._py = self.PLAY_H / 2
        self._keys = {"up": False, "down": False, "left": False, "right": False}
        self._score = 0
        self._elapsed = 0.0
        self._spawn_cd = 0.0
        self._near_miss_cd = 0.0
        self._milestone_30 = False
        self._milestone_60 = False
        self._running = False
        self._finished = False

        h = self.HUD_HEIGHT + self.PLAY_H
        self.setMinimumSize(self.PLAY_W, h)
        self.setMaximumSize(self.PLAY_W, h)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._init_stars()

    def _init_stars(self) -> None:
        self._stars = [
            Star(
                random.uniform(0, self.PLAY_W),
                random.uniform(0, self.PLAY_H),
                random.uniform(0.3, 1.2) * (layer + 1),
                random.uniform(1, 2.5),
                layer,
            )
            for layer in range(3)
            for _ in range(40)
        ]

    def start_game(self) -> None:
        self._asteroids.clear()
        self._px = self.PLAY_W / 2
        self._py = self.PLAY_H / 2
        self._score = 0
        self._elapsed = 0.0
        self._spawn_cd = 0.5
        self._near_miss_cd = 0.0
        self._milestone_30 = False
        self._milestone_60 = False
        self._running = True
        self._finished = False
        self._init_stars()
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
        m = {
            Qt.Key.Key_Up: "up", Qt.Key.Key_W: "up",
            Qt.Key.Key_Down: "down", Qt.Key.Key_S: "down",
            Qt.Key.Key_Left: "left", Qt.Key.Key_A: "left",
            Qt.Key.Key_Right: "right", Qt.Key.Key_D: "right",
        }
        k = m.get(event.key())
        if k:
            self._keys[k] = True
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        m = {
            Qt.Key.Key_Up: "up", Qt.Key.Key_W: "up",
            Qt.Key.Key_Down: "down", Qt.Key.Key_S: "down",
            Qt.Key.Key_Left: "left", Qt.Key.Key_A: "left",
            Qt.Key.Key_Right: "right", Qt.Key.Key_D: "right",
        }
        k = m.get(event.key())
        if k:
            self._keys[k] = False
        super().keyReleaseEvent(event)

    def _on_render(self) -> None:
        self.update()

    def _tick(self) -> None:
        if not self._running:
            return
        dt = self.LOGIC_MS / 1000.0
        self._elapsed += dt
        self._score = int(self._elapsed)
        if self._score >= 30 and not self._milestone_30:
            self._milestone_30 = True
            self.game_event.emit("milestone_30", self._score)
        if self._score >= 60 and not self._milestone_60:
            self._milestone_60 = True
            self.game_event.emit("milestone_60", self._score)

        vx = (self._keys["right"] - self._keys["left"]) * self.MOVE_SPEED
        vy = (self._keys["down"] - self._keys["up"]) * self.MOVE_SPEED
        self._px = max(self.PLAYER_R, min(self.PLAY_W - self.PLAYER_R, self._px + vx))
        self._py = max(self.PLAYER_R, min(self.PLAY_H - self.PLAYER_R, self._py + vy))

        for star in self._stars:
            star.y += star.speed
            if star.y > self.PLAY_H:
                star.y = 0
                star.x = random.uniform(0, self.PLAY_W)

        self._spawn_cd -= dt
        if self._spawn_cd <= 0:
            self._spawn_asteroid()
            self._spawn_cd = max(0.35, 1.1 - self._elapsed * 0.012)

        self._near_miss_cd = max(0, self._near_miss_cd - dt)
        for ast in self._asteroids:
            ast.x += ast.vx
            ast.y += ast.vy
            dist = math.hypot(ast.x - self._px, ast.y - self._py)
            if dist < ast.radius + self.PLAYER_R - 2:
                self._end_game()
                return
            if dist < ast.radius + self.PLAYER_R + 14 and self._near_miss_cd <= 0:
                self._near_miss_cd = 2.0
                self.game_event.emit("near_miss", self._score)

        margin = 40
        self._asteroids = [
            a for a in self._asteroids
            if -margin < a.x < self.PLAY_W + margin and -margin < a.y < self.PLAY_H + margin
        ]

    def _spawn_asteroid(self) -> None:
        side = random.randint(0, 3)
        speed = random.uniform(2.5, 4.5) + min(self._elapsed * 0.05, 2.5)
        if side == 0:
            x, y = random.uniform(0, self.PLAY_W), -20
            tx, ty = random.uniform(0, self.PLAY_W), self.PLAY_H + 20
        elif side == 1:
            x, y = self.PLAY_W + 20, random.uniform(0, self.PLAY_H)
            tx, ty = -20, random.uniform(0, self.PLAY_H)
        elif side == 2:
            x, y = random.uniform(0, self.PLAY_W), self.PLAY_H + 20
            tx, ty = random.uniform(0, self.PLAY_W), -20
        else:
            x, y = -20, random.uniform(0, self.PLAY_H)
            tx, ty = self.PLAY_W + 20, random.uniform(0, self.PLAY_H)
        dx, dy = tx - x, ty - y
        length = math.hypot(dx, dy) or 1
        vx, vy = dx / length * speed, dy / length * speed
        radius = random.uniform(10, 18)
        self._asteroids.append(Asteroid(x, y, vx, vy, radius))

    def _end_game(self) -> None:
        if self._finished:
            return
        self._finished = True
        self._running = False
        self._logic_timer.stop()
        self._stop_render()
        self.game_event.emit("death", self._score)
        self.update()
        self.game_finished.emit(self._score)

    def paintEvent(self, _event) -> None:
        t = self._theme
        hud = self.HUD_HEIGHT
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(*t["background"]))

        left = f"存活 {self._score} 秒"
        paint_game_hud(painter, t, self.PLAY_W, hud, left, self._fps_hud_text())

        # 星空层（在 HUD 下方游戏区内）
        painter.save()
        painter.setClipRect(0, hud, self.PLAY_W, self.PLAY_H)
        paint_play_border(painter, t, 0, hud, self.PLAY_W, self.PLAY_H)

        for star in self._stars:
            sy = hud + star.y
            alpha = 80 + star.layer * 50
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(200, 220, 255, alpha))
            painter.drawEllipse(int(star.x), int(sy), int(star.size), int(star.size))

        for ast in self._asteroids:
            ax, ay = int(ast.x), hud + int(ast.y)
            grad = QLinearGradient(ax - ast.radius, ay - ast.radius, ax + ast.radius, ay + ast.radius)
            grad.setColorAt(0, QColor(120, 90, 70))
            grad.setColorAt(1, QColor(60, 45, 35))
            painter.setBrush(grad)
            painter.setPen(QPen(QColor(180, 140, 100), 1))
            painter.drawEllipse(int(ax - ast.radius), int(ay - ast.radius), int(ast.radius * 2), int(ast.radius * 2))

        px, py = int(self._px), hud + int(self._py)
        ship_grad = QLinearGradient(px - 10, py - 10, px + 10, py + 10)
        ship_grad.setColorAt(0, QColor(*t["snake_head"]))
        ship_grad.setColorAt(1, QColor(0, 120, 200))
        painter.setBrush(ship_grad)
        painter.setPen(QPen(QColor(*t["panel_glow"]), 2))
        painter.drawEllipse(px - self.PLAYER_R, py - self.PLAYER_R, self.PLAYER_R * 2, self.PLAYER_R * 2)
        painter.restore()

        if self._finished:
            overlay = QColor(14, 18, 28, 210)
            painter.fillRect(0, hud, self.PLAY_W, self.PLAY_H, overlay)
            painter.setPen(QColor(*t["text_accent"]))
            painter.setFont(QFont(t["font_family"], 14, QFont.Weight.Bold))
            painter.drawText(0, hud, self.PLAY_W, self.PLAY_H, Qt.AlignmentFlag.AlignCenter, "被流星击中！")
