"""大富翁开局选人 — 人机 / 自定义本地混合"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.constants import GAME_THEME
from .player_avatars import AvatarPickerButton, default_avatar_id

DEFAULT_BOT_NAMES = ("小蓝", "小粉", "小橙", "小绿")
DEFAULT_HUMAN_NAMES = ("主人", "玩家2", "玩家3", "玩家4")


@dataclass
class PlayerSlot:
    name: str
    is_human: bool
    avatar_id: str = "preset_0"
    avatar_path: Optional[str] = None


@dataclass
class RichmanSetup:
    players: List[PlayerSlot]

    @staticmethod
    def vs_ai(human_name: str = "主人", avatar_id: str = "preset_0", avatar_path: Optional[str] = None) -> RichmanSetup:
        name = human_name.strip() or "主人"
        return RichmanSetup(
            [
                PlayerSlot(name, True, avatar_id, avatar_path),
                PlayerSlot("小蓝", False, default_avatar_id(1)),
                PlayerSlot("小粉", False, default_avatar_id(2)),
                PlayerSlot("小橙", False, default_avatar_id(3)),
            ]
        )


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


class _SlotRow(QFrame):
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._index = index
        t = GAME_THEME
        self.setStyleSheet(
            f"QFrame {{ background: rgb(22,30,46); border: 1px solid {_rgb(t['surface_border'])};"
            f" border-radius: 8px; padding: 4px; }}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)

        self._avatar = AvatarPickerButton(default_avatar_id(index))
        row.addWidget(self._avatar)

        self._role = QComboBox()
        self._role.addItems(["本地玩家 👤", "电脑 🤖"])
        self._role.setMinimumWidth(118)
        row.addWidget(self._role)

        self._name = QLineEdit()
        self._name.setPlaceholderText("昵称")
        self._name.setMaxLength(8)
        row.addWidget(self._name, stretch=1)

    def set_defaults(self, name: str, is_human: bool, avatar_id: Optional[str] = None) -> None:
        self._name.setText(name)
        self._role.setCurrentIndex(0 if is_human else 1)
        if avatar_id:
            self._avatar.set_avatar(avatar_id, None)

    def to_slot(self) -> PlayerSlot:
        return PlayerSlot(
            self._name.text().strip() or f"玩家{self._index + 1}",
            self._role.currentIndex() == 0,
            self._avatar.avatar_id(),
            self._avatar.custom_path(),
        )

    def set_enabled_row(self, on: bool) -> None:
        self.setVisible(on)


class RichmanSetupDialog(QDialog):
    """选择 2～4 人：人机对战或自定义人/电脑混合（本地同屏，非联网）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._setup: Optional[RichmanSetup] = None
        self.setWindowTitle("大富翁 · 选择对局")
        self.setMinimumWidth(460)
        self.setModal(True)

        t = self._theme
        self.setStyleSheet(
            f"""
            QDialog {{ background: {_rgb(t['background'])}; color: {_rgb(t['text'])}; }}
            QLabel {{ color: {_rgb(t['text'])}; }}
            QLineEdit {{
                background: rgb(14,20,32);
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: 6px;
                padding: 6px 8px;
                color: {_rgb(t['text'])};
            }}
            QComboBox {{
                background: rgb(14,20,32);
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: 6px;
                padding: 4px 8px;
                color: {_rgb(t['text'])};
            }}
            QRadioButton {{ spacing: 8px; }}
            """
        )

        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("选择对局模式")
        title.setFont(QFont(t["font_family"], 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_rgb(t['text_accent'])};")
        root.addWidget(title)

        hint = QLabel("本地同屏：轮到本地玩家时用鼠标操作；电脑自动行动。无需联网。")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {_rgb(t['text_muted'])}; font-size: 11px;")
        root.addWidget(hint)

        self._mode_vs = QRadioButton("人机对战 — 1 名本地玩家 + 3 名电脑（4 人）")
        self._mode_vs.setChecked(True)
        self._mode_custom = QRadioButton("自定义 — 2～4 人，自由搭配本地玩家与电脑")
        mode_group = QButtonGroup(self)
        mode_group.addButton(self._mode_vs)
        mode_group.addButton(self._mode_custom)
        root.addWidget(self._mode_vs)
        root.addWidget(self._mode_custom)

        self._vs_box = QFrame()
        vs_l = QHBoxLayout(self._vs_box)
        vs_l.addWidget(QLabel("头像"))
        self._vs_avatar = AvatarPickerButton("preset_0")
        vs_l.addWidget(self._vs_avatar)
        vs_l.addWidget(QLabel("昵称"))
        self._human_name = QLineEdit("主人")
        self._human_name.setMaxLength(8)
        vs_l.addWidget(self._human_name, stretch=1)
        root.addWidget(self._vs_box)

        self._custom_box = QFrame()
        custom_outer = QVBoxLayout(self._custom_box)
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("人数"))
        self._count = QComboBox()
        self._count.addItems(["2 人", "3 人", "4 人"])
        self._count.setCurrentIndex(2)
        self._count.currentIndexChanged.connect(self._on_count_changed)
        count_row.addWidget(self._count)
        count_row.addStretch(1)
        custom_outer.addLayout(count_row)

        self._slot_rows: List[_SlotRow] = []
        slots_host = QWidget()
        slots_l = QVBoxLayout(slots_host)
        slots_l.setSpacing(6)
        for i in range(4):
            row = _SlotRow(i)
            is_human = i < 2
            row.set_defaults(
                DEFAULT_HUMAN_NAMES[i] if is_human else DEFAULT_BOT_NAMES[i - 1],
                is_human,
                default_avatar_id(i),
            )
            self._slot_rows.append(row)
            slots_l.addWidget(row)
        custom_outer.addWidget(slots_host)
        self._custom_box.setVisible(False)
        root.addWidget(self._custom_box)

        self._error = QLabel("")
        self._error.setStyleSheet("color: rgb(255, 120, 100); font-size: 11px;")
        root.addWidget(self._error)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("开始对局")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self._mode_vs.toggled.connect(self._on_mode_changed)
        self._mode_custom.toggled.connect(self._on_mode_changed)
        self._on_count_changed()

    def _on_mode_changed(self) -> None:
        vs = self._mode_vs.isChecked()
        self._vs_box.setVisible(vs)
        self._custom_box.setVisible(not vs)
        self._error.setText("")

    def _on_count_changed(self, _idx: int = 0) -> None:
        n = self._count.currentIndex() + 2
        for i, row in enumerate(self._slot_rows):
            row.set_enabled_row(i < n)

    def _on_accept(self) -> None:
        self._error.setText("")
        if self._mode_vs.isChecked():
            self._setup = RichmanSetup.vs_ai(
                self._human_name.text(),
                self._vs_avatar.avatar_id(),
                self._vs_avatar.custom_path(),
            )
            self.accept()
            return

        n = self._count.currentIndex() + 2
        slots = [self._slot_rows[i].to_slot() for i in range(n)]
        names = [s.name for s in slots]
        if len(set(names)) < len(names):
            self._error.setText("玩家昵称不能重复")
            return
        if not any(s.is_human for s in slots):
            self._error.setText("至少需要 1 名本地玩家")
            return
        self._setup = RichmanSetup(slots)
        self.accept()

    def setup(self) -> Optional[RichmanSetup]:
        return self._setup


def pick_richman_setup(parent=None) -> Optional[RichmanSetup]:
    dlg = RichmanSetupDialog(parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        return dlg.setup()
    return None
