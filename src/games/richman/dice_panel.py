"""大富翁右侧动态骰子面板"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...utils.constants import GAME_THEME
from .game_engine import GamePhase, PlayerState, RichmanEngine
from .player_avatars import AvatarThumb

PLAYER_ACCENTS = [
    (72, 220, 160),
    (100, 180, 255),
    (255, 150, 180),
    (255, 200, 100),
]

_DICE_DOTS = {
    1: [(0.5, 0.5)],
    2: [(0.28, 0.28), (0.72, 0.72)],
    3: [(0.28, 0.28), (0.5, 0.5), (0.72, 0.72)],
    4: [(0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)],
    5: [(0.28, 0.28), (0.72, 0.28), (0.5, 0.5), (0.28, 0.72), (0.72, 0.72)],
    6: [
        (0.28, 0.28),
        (0.72, 0.28),
        (0.28, 0.5),
        (0.72, 0.5),
        (0.28, 0.72),
        (0.72, 0.72),
    ],
}


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


class DieWidget(QWidget):
    """单颗骰子：可滚动、可展示点数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value: Optional[int] = None
        self._rolling = False
        self._idle = False
        self._roll_ticks = 0
        self._roll_target = 1
        self._shake = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._on_tick)
        self.setFixedSize(54, 54)

    def value(self) -> Optional[int]:
        return self._value

    def set_value(self, value: Optional[int]) -> None:
        self._rolling = False
        self._timer.stop()
        self._value = value if value is None else max(1, min(6, value))
        self._shake = 0.0
        self.update()

    def start_roll(self, final_value: int, duration_ms: int = 950) -> None:
        self._roll_target = max(1, min(6, final_value))
        self._rolling = True
        self._roll_ticks = max(8, duration_ms // 50)
        self._shake = 1.0
        self._timer.setInterval(50)
        self._timer.start()
        self.update()

    def set_idle_bounce(self, enabled: bool) -> None:
        self._idle = enabled
        if self._rolling:
            return
        if enabled:
            if not self._timer.isActive():
                self._timer.setInterval(320)
                self._timer.start()
        else:
            self._timer.stop()
            self._shake = 0.0
            self.update()

    def _on_tick(self) -> None:
        if self._rolling:
            self._roll_ticks -= 1
            self._value = random.randint(1, 6)
            self._shake = 1.0 if self._roll_ticks > 2 else max(0.0, self._roll_ticks * 0.35)
            if self._roll_ticks <= 0:
                self._rolling = False
                self._value = self._roll_target
                self._shake = 0.0
                if self._idle:
                    self._timer.setInterval(320)
                else:
                    self._timer.stop()
            self.update()
            return

        if self._idle:
            self._shake = 0.16 if self._shake < 0.1 else 0.0
            self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pad = 4
        shake_y = math_sin(self._shake) * 3.0 if self._shake else 0.0
        rect = QRectF(pad, pad + shake_y, w - pad * 2, h - pad * 2)

        p.setPen(QPen(QColor(0, 200, 255, 120 if self._rolling else 70), 1.5))
        p.setBrush(QColor(248, 252, 255))
        p.drawRoundedRect(rect, 10, 10)

        if self._value is None:
            p.setPen(QColor(140, 155, 175))
            p.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "?")
            return

        dot_r = max(3.5, rect.width() * 0.09)
        p.setBrush(QColor(28, 36, 52))
        p.setPen(Qt.PenStyle.NoPen)
        for dx, dy in _DICE_DOTS.get(self._value, []):
            cx = rect.left() + rect.width() * dx
            cy = rect.top() + rect.height() * dy
            p.drawEllipse(QRectF(cx - dot_r, cy - dot_r, dot_r * 2, dot_r * 2))


def math_sin(x: float) -> float:
    import math

    return math.sin(x * math.pi * 2)


class _PlayerDiceSlot(QFrame):
    def __init__(self, player_id: int, name: str, parent=None):
        super().__init__(parent)
        self.player_id = player_id
        self._accent = PLAYER_ACCENTS[player_id % len(PLAYER_ACCENTS)]
        self.setObjectName("diceSlot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        head = QHBoxLayout()
        head.setSpacing(6)
        self._avatar = AvatarThumb(size=30)
        head.addWidget(self._avatar, alignment=Qt.AlignmentFlag.AlignCenter)
        self._name = QLabel(name)
        self._name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        head.addWidget(self._name, stretch=1)
        layout.addLayout(head)

        dice_row = QHBoxLayout()
        dice_row.setSpacing(6)
        self._die1 = DieWidget()
        self._die2 = DieWidget()
        dice_row.addWidget(self._die1)
        dice_row.addWidget(self._die2)
        layout.addLayout(dice_row)

        self._sum = QLabel("—")
        self._sum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._sum)
        self.set_active(False)

    def set_name(self, name: str) -> None:
        self._name.setText(name)

    def set_avatar(self, avatar_id: str, avatar_path: Optional[str] = None) -> None:
        self._avatar.set_avatar(avatar_id, avatar_path)

    def set_active(self, active: bool) -> None:
        accent = _rgb(self._accent)
        if active:
            self.setStyleSheet(
                f"QFrame#diceSlot {{ background: rgb(18,28,44); border: 2px solid {accent};"
                f" border-radius: 12px; }}"
                f"QLabel {{ color: {accent}; font-weight: 700; font-size: 11px; }}"
            )
        else:
            self.setStyleSheet(
                "QFrame#diceSlot { background: rgb(14,18,28); border: 1px solid rgb(42,52,70);"
                " border-radius: 12px; }"
                "QLabel { color: rgb(120,132,150); font-size: 11px; }"
            )

    def set_idle(self, bounce: bool) -> None:
        self._die1.set_idle_bounce(bounce)
        self._die2.set_idle_bounce(bounce)

    def show_roll(self, d1: int, d2: int) -> None:
        self._die1.start_roll(d1)
        self._die2.start_roll(d2, duration_ms=1050)
        self._sum.setText("…")
        QTimer.singleShot(1100, lambda: self._sum.setText(f"= {d1 + d2} 点"))

    def clear_roll(self) -> None:
        self._die1.set_value(None)
        self._die2.set_value(None)
        self._sum.setText("—")


class RichmanDicePanel(QWidget):
    """四名玩家骰子区：轮到谁，骰子就在谁那里动。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._slots: List[_PlayerDiceSlot] = []
        self._last_rolls: Dict[int, Tuple[int, int]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        title = QLabel("🎲  行动骰子")
        title.setStyleSheet(
            f"color: {_rgb(self._theme['text_accent'])}; font-size: 13px; font-weight: 700;"
        )
        root.addWidget(title)

        row_host = QWidget()
        row = QHBoxLayout(row_host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        root.addWidget(row_host)

        self._hint = QLabel("轮到谁谁掷骰，骰子会跟随高亮")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        root.addWidget(self._hint)

    def bind_players(self, players: List[PlayerState]) -> None:
        layout = self.layout()
        row_host = layout.itemAt(1).widget()
        row = row_host.layout()
        while row.count():
            item = row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._slots.clear()
        for i, pl in enumerate(players):
            slot = _PlayerDiceSlot(i, pl.name)
            slot.set_avatar(pl.avatar_id, pl.avatar_path)
            row.addWidget(slot)
            self._slots.append(slot)

    def sync_from_engine(self, engine: RichmanEngine) -> None:
        players = engine.players()
        if len(self._slots) != len(players):
            self.bind_players(players)

        cp = engine.current_player
        phase = engine.phase
        for i, slot in enumerate(self._slots):
            pl = players[i]
            slot.set_name(pl.name)
            slot.set_avatar(pl.avatar_id, pl.avatar_path)
            is_active = pl.id == cp.id and not pl.bankrupt and phase != GamePhase.GAME_OVER
            slot.set_active(is_active)
            bounce = is_active and phase == GamePhase.WAIT_ROLL
            slot.set_idle(bounce)
            if not is_active and pl.id in self._last_rolls:
                d1, d2 = self._last_rolls[pl.id]
                if slot._die1.value() is None:
                    slot._die1.set_value(d1)
                    slot._die2.set_value(d2)
                    slot._sum.setText(f"= {d1 + d2} 点")

        if phase == GamePhase.MOVING:
            self._hint.setText(f"{cp.name} 掷骰移动中…")
        elif is_active := (
            cp.id == engine.current_player.id
            and not cp.bankrupt
            and phase == GamePhase.WAIT_ROLL
        ):
            self._hint.setText(f"▶ 轮到 {cp.name}，请掷骰子")
        elif phase == GamePhase.GAME_OVER:
            self._hint.setText("对局结束")
        else:
            self._hint.setText(f"等待 {cp.name} 行动…")

    def on_dice_rolled(self, player_id: int, d1: int, d2: int) -> None:
        self._last_rolls[player_id] = (d1, d2)
        if 0 <= player_id < len(self._slots):
            for i, slot in enumerate(self._slots):
                slot.set_active(i == player_id)
                slot.set_idle(False)
            self._slots[player_id].show_roll(d1, d2)
            name = self._slots[player_id]._name.text()
            self._hint.setText(f"{name} 掷出了 {d1} + {d2}")
