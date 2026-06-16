"""国际象棋开局设置 — 人机 / 双人同屏"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
)

from ...utils.constants import GAME_THEME


@dataclass
class ChessSetup:
    white_name: str
    black_name: str
    white_is_human: bool
    black_is_human: bool
    difficulty: str = "normal"

    @staticmethod
    def vs_ai(
        human_name: str = "主人",
        human_plays_white: bool = True,
        difficulty: str = "normal",
    ) -> ChessSetup:
        name = human_name.strip() or "主人"
        if human_plays_white:
            return ChessSetup(name, "电脑", True, False, difficulty)
        return ChessSetup("电脑", name, False, True, difficulty)

    @staticmethod
    def local(white_name: str = "白方", black_name: str = "黑方") -> ChessSetup:
        return ChessSetup(
            white_name.strip() or "白方",
            black_name.strip() or "黑方",
            True,
            True,
            "normal",
        )


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


class ChessSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = GAME_THEME
        self._setup: Optional[ChessSetup] = None
        self.setWindowTitle("国际象棋 · 选择对局")
        self.setMinimumWidth(400)
        self.setModal(True)

        t = self._theme
        self.setStyleSheet(
            f"""
            QDialog {{ background: {_rgb(t['background'])}; color: {_rgb(t['text'])}; }}
            QLabel {{ color: {_rgb(t['text'])}; }}
            QLineEdit {{
                background: rgb(14,20,32);
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: 6px; padding: 6px 10px; color: {_rgb(t['text'])};
            }}
            QComboBox {{
                background: rgb(14,20,32);
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: 6px; padding: 4px 8px; color: {_rgb(t['text'])};
            }}
            QRadioButton {{ color: {_rgb(t['text'])}; spacing: 6px; }}
            """
        )

        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel("选择对战模式")
        title.setFont(QFont(t["font_family"], 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_rgb(t['text_accent'])};")
        root.addWidget(title)

        self._mode_ai = QRadioButton("人机对战（你 vs 电脑）")
        self._mode_local = QRadioButton("双人同屏（本地轮流）")
        self._mode_ai.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self._mode_ai)
        grp.addButton(self._mode_local)
        root.addWidget(self._mode_ai)
        root.addWidget(self._mode_local)

        self._human_name = QLineEdit()
        self._human_name.setPlaceholderText("你的昵称")
        self._human_name.setText("主人")
        root.addWidget(QLabel("本地玩家昵称"))
        root.addWidget(self._human_name)

        self._color = QComboBox()
        self._color.addItems(["执白（先手）", "执黑（后手）"])
        root.addWidget(QLabel("人机模式 · 你的棋子颜色"))
        root.addWidget(self._color)

        self._difficulty = QComboBox()
        self._difficulty.addItems(["简单", "普通", "困难"])
        self._difficulty.setCurrentIndex(1)
        root.addWidget(QLabel("电脑难度"))
        root.addWidget(self._difficulty)

        self._white_name = QLineEdit()
        self._white_name.setPlaceholderText("白方昵称")
        self._white_name.setText("白方")
        self._black_name = QLineEdit()
        self._black_name.setPlaceholderText("黑方昵称")
        self._black_name.setText("黑方")
        root.addWidget(QLabel("双人模式 · 白方昵称"))
        root.addWidget(self._white_name)
        root.addWidget(QLabel("双人模式 · 黑方昵称"))
        root.addWidget(self._black_name)

        self._mode_ai.toggled.connect(self._sync_mode_ui)
        self._sync_mode_ui()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _sync_mode_ui(self) -> None:
        ai = self._mode_ai.isChecked()
        self._human_name.setEnabled(ai)
        self._color.setEnabled(ai)
        self._difficulty.setEnabled(ai)
        self._white_name.setEnabled(not ai)
        self._black_name.setEnabled(not ai)

    def _accept(self) -> None:
        if self._mode_ai.isChecked():
            diff_map = {"简单": "easy", "普通": "normal", "困难": "hard"}
            diff = diff_map.get(self._difficulty.currentText(), "normal")
            self._setup = ChessSetup.vs_ai(
                self._human_name.text(),
                self._color.currentIndex() == 0,
                diff,
            )
        else:
            self._setup = ChessSetup.local(self._white_name.text(), self._black_name.text())
        self.accept()

    def setup(self) -> Optional[ChessSetup]:
        return self._setup


def pick_chess_setup(parent=None) -> Optional[ChessSetup]:
    dlg = ChessSetupDialog(parent)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None
    return dlg.setup()
