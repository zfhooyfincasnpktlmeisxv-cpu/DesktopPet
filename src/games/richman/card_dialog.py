"""机会 / 命运卡弹窗"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from ...utils.constants import GAME_THEME


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


class CardDialog(QDialog):
    def __init__(self, deck_label: str, text: str, parent=None):
        super().__init__(parent)
        t = GAME_THEME
        self.setWindowTitle(deck_label)
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setStyleSheet(
            f"""
            QDialog {{ background: {_rgb(t['surface'])}; color: {_rgb(t['text'])}; }}
            QLabel#title {{ color: {_rgb(t['text_accent'])}; font-size: 16px; font-weight: 700; }}
            QLabel#body {{ color: {_rgb(t['text'])}; font-size: 13px; line-height: 1.5; }}
            QPushButton {{
                background: {_rgb(t['accent'])};
                color: rgb(14,18,28);
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 700;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 18, 20, 18)

        title = QLabel(deck_label)
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        body = QLabel(text)
        body.setObjectName("body")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(body)

        ok = QPushButton("知道了")
        ok.clicked.connect(self.accept)
        layout.addWidget(ok)
        self.setFont(QFont(t["font_family"], 10))


def show_card(parent, deck_name: str, text: str) -> None:
    label = "机会卡" if deck_name == "chance" else "命运卡"
    dlg = CardDialog(label, text, parent)
    dlg.exec()
