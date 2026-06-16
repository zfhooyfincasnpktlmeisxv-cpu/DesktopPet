"""玩家头像 — 预设 + 本地自定义图片"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils.constants import GAME_THEME

AvatarKey = Tuple[str, Optional[str]]  # (avatar_id, custom_path)


@dataclass(frozen=True)
class AvatarPreset:
    id: str
    emoji: str
    color: Tuple[int, int, int]
    label: str


PRESET_AVATARS: List[AvatarPreset] = [
    AvatarPreset("preset_0", "😺", (255, 120, 150), "萌猫"),
    AvatarPreset("preset_1", "🐶", (100, 180, 255), "小狗"),
    AvatarPreset("preset_2", "🦊", (255, 160, 90), "狐狸"),
    AvatarPreset("preset_3", "🐼", (120, 220, 160), "熊猫"),
    AvatarPreset("preset_4", "🐯", (255, 200, 80), "小虎"),
    AvatarPreset("preset_5", "🐰", (200, 150, 255), "兔子"),
    AvatarPreset("preset_6", "🐸", (80, 210, 180), "青蛙"),
    AvatarPreset("preset_7", "🐻", (180, 140, 110), "小熊"),
]

_PRESET_MAP: Dict[str, AvatarPreset] = {p.id: p for p in PRESET_AVATARS}
_pixmap_cache: Dict[str, QPixmap] = {}


def default_avatar_id(index: int) -> str:
    return PRESET_AVATARS[index % len(PRESET_AVATARS)].id


def render_preset_pixmap(avatar_id: str, size: int = 64) -> QPixmap:
    cache_key = f"{avatar_id}:{size}"
    if cache_key in _pixmap_cache:
        return _pixmap_cache[cache_key]

    preset = _PRESET_MAP.get(avatar_id, PRESET_AVATARS[0])
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    r, g, b = preset.color
    p.setPen(QPen(QColor(255, 255, 255, 180), 2))
    p.setBrush(QColor(r, g, b))
    p.drawEllipse(1, 1, size - 2, size - 2)
    p.setFont(QFont("Segoe UI Emoji", max(12, int(size * 0.46))))
    p.setPen(QColor(255, 255, 255))
    p.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, preset.emoji)
    p.end()
    _pixmap_cache[cache_key] = pm
    return pm


def load_avatar_pixmap(avatar_id: str, custom_path: Optional[str] = None, size: int = 64) -> QPixmap:
    if custom_path:
        path = Path(custom_path)
        if path.is_file():
            cache_key = f"file:{path}:{size}:{path.stat().st_mtime_ns}"
            if cache_key in _pixmap_cache:
                return _pixmap_cache[cache_key]
            raw = QPixmap(str(path))
            if not raw.isNull():
                pm = raw.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
                _pixmap_cache[cache_key] = pm
                return pm
    return render_preset_pixmap(avatar_id, size)


class AvatarPickerButton(QPushButton):
    """可点击选择预设或本地图片的头像按钮。"""

    avatar_changed = pyqtSignal(str, object)  # avatar_id, custom_path Optional[str]

    def __init__(self, avatar_id: str = "preset_0", custom_path: Optional[str] = None, parent=None):
        super().__init__(parent)
        self._avatar_id = avatar_id
        self._custom_path: Optional[str] = custom_path
        self.setFixedSize(44, 44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("点击更换头像")
        self.clicked.connect(self._open_picker)
        self._refresh_style()

    def avatar_id(self) -> str:
        return self._avatar_id

    def custom_path(self) -> Optional[str]:
        return self._custom_path

    def set_avatar(self, avatar_id: str, custom_path: Optional[str] = None) -> None:
        self._avatar_id = avatar_id
        self._custom_path = custom_path
        self._refresh_style()
        self.update()

    def _refresh_style(self) -> None:
        self.setStyleSheet(
            "QPushButton { border: 2px solid rgb(0,200,255); border-radius: 22px; padding: 0; background: rgb(20,28,42); }"
            "QPushButton:hover { border-color: rgb(120,230,255); }"
        )

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pm = load_avatar_pixmap(self._avatar_id, self._custom_path, 40)
        path = QPainterPath()
        path.addEllipse(2, 2, 40, 40)
        p.setClipPath(path)
        p.drawPixmap(2, 2, pm)
        p.end()

    def _open_picker(self) -> None:
        dlg = _AvatarPickDialog(self._avatar_id, self._custom_path, parent=self.window())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            aid, path = dlg.selection()
            self._avatar_id = aid
            self._custom_path = path
            self.update()
            self.avatar_changed.emit(aid, path)


class _AvatarPickDialog(QDialog):
    def __init__(self, current_id: str, current_path: Optional[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择头像")
        self.setMinimumWidth(320)
        self._selected_id = current_id
        self._selected_path = current_path
        t = GAME_THEME

        self.setStyleSheet(
            f"QDialog {{ background: rgb({t['background'][0]},{t['background'][1]},{t['background'][2]}); }}"
            "QPushButton { padding: 6px 10px; }"
        )

        root = QVBoxLayout(self)
        root.addWidget(QLabel("选一个预设头像，或从电脑上传图片"))

        grid = QGridLayout()
        grid.setSpacing(8)
        self._buttons: List[QPushButton] = []
        for i, preset in enumerate(PRESET_AVATARS):
            btn = QPushButton()
            btn.setFixedSize(52, 52)
            btn.setToolTip(preset.label)
            btn.setProperty("avatar_id", preset.id)
            btn.clicked.connect(lambda _=False, pid=preset.id: self._pick_preset(pid))
            grid.addWidget(btn, i // 4, i % 4)
            self._buttons.append(btn)
        root.addLayout(grid)

        custom_row = QHBoxLayout()
        self._custom_btn = QPushButton("从电脑选择图片…")
        self._custom_btn.clicked.connect(self._pick_file)
        custom_row.addWidget(self._custom_btn)
        if current_path:
            clear_btn = QPushButton("清除自定义")
            clear_btn.clicked.connect(self._clear_custom)
            custom_row.addWidget(clear_btn)
        root.addLayout(custom_row)

        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        root.addWidget(box)
        self._repaint_buttons()

    def _pick_preset(self, avatar_id: str) -> None:
        self._selected_id = avatar_id
        self._selected_path = None
        self._repaint_buttons()

    def _pick_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择头像图片",
            "",
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp);;全部 (*.*)",
        )
        if path:
            self._selected_path = path
            self._selected_id = default_avatar_id(0)
            self._repaint_buttons()

    def _clear_custom(self) -> None:
        self._selected_path = None
        self._repaint_buttons()

    def _repaint_buttons(self) -> None:
        for i, btn in enumerate(self._buttons):
            preset = PRESET_AVATARS[i]
            selected = preset.id == self._selected_id and not self._selected_path
            border = "rgb(0,220,255)" if selected else "rgb(60,70,90)"
            btn.setStyleSheet(
                f"QPushButton {{ border: 2px solid {border}; border-radius: 26px; background: rgb(18,24,36); }}"
            )
            pm = render_preset_pixmap(preset.id, 48)
            icon = pm
            from PyQt6.QtGui import QIcon

            btn.setIcon(QIcon(icon))
            btn.setIconSize(QSize(44, 44))

    def selection(self) -> AvatarKey:
        return self._selected_id, self._selected_path


class AvatarThumb(QWidget):
    """只读圆形头像缩略图（骰子面板等）。"""

    def __init__(
        self,
        avatar_id: str = "preset_0",
        custom_path: Optional[str] = None,
        size: int = 32,
        parent=None,
    ):
        super().__init__(parent)
        self._avatar_id = avatar_id
        self._custom_path = custom_path
        self._size = size
        self.setFixedSize(size, size)

    def set_avatar(self, avatar_id: str, custom_path: Optional[str] = None) -> None:
        self._avatar_id = avatar_id
        self._custom_path = custom_path
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pm = load_avatar_pixmap(self._avatar_id, self._custom_path, self._size)
        path = QPainterPath()
        path.addEllipse(0, 0, self._size, self._size)
        p.setClipPath(path)
        p.drawPixmap(0, 0, pm)
        p.end()
