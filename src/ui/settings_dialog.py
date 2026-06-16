"""Application settings dialog."""
from __future__ import annotations

import logging
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..i18n import SUPPORTED_LANGUAGES, t
from ..system.data_persistence import Settings

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Language and basic display options."""

    def __init__(
        self,
        settings: Settings,
        on_save: Callable[[Settings], None],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._initial = settings
        self._on_save = on_save
        self._build_ui(settings)
        self._retranslate()

    def _build_ui(self, settings: Settings) -> None:
        self.setMinimumWidth(380)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(18, 18, 18, 14)

        self._hint = QLabel()
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color: rgb(100, 110, 125); font-size: 12px;")
        root.addWidget(self._hint)

        form = QFormLayout()
        form.setSpacing(10)

        self._lang_combo = QComboBox()
        for code, label in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(label, code)
        idx = self._lang_combo.findData(settings.language)
        if idx >= 0:
            self._lang_combo.setCurrentIndex(idx)
        self._lang_label = QLabel()
        form.addRow(self._lang_label, self._lang_combo)

        self._auto_walk = QCheckBox()
        self._auto_walk.setChecked(settings.auto_walk_enabled)
        self._auto_walk_label = QLabel()
        form.addRow(self._auto_walk_label, self._auto_walk)

        self._stat_hud = QCheckBox()
        self._stat_hud.setChecked(settings.show_stat_hud)
        self._stat_hud_label = QLabel()
        form.addRow(self._stat_hud_label, self._stat_hud)

        self._opacity = QDoubleSpinBox()
        self._opacity.setRange(0.3, 1.0)
        self._opacity.setSingleStep(0.05)
        self._opacity.setDecimals(2)
        self._opacity.setValue(settings.opacity)
        self._opacity_label = QLabel()
        form.addRow(self._opacity_label, self._opacity)

        root.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._save_btn = buttons.button(QDialogButtonBox.StandardButton.Save)
        self._cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _retranslate(self) -> None:
        self.setWindowTitle(t("settings.title"))
        self._hint.setText(t("settings.language_hint"))
        self._lang_label.setText(t("settings.language"))
        self._auto_walk_label.setText(t("settings.auto_walk"))
        self._auto_walk.setText(t("settings.auto_walk"))
        self._stat_hud_label.setText(t("settings.show_stat_hud"))
        self._stat_hud.setText(t("settings.show_stat_hud"))
        self._opacity_label.setText(t("settings.opacity"))
        if self._save_btn:
            self._save_btn.setText(t("settings.save"))
        if self._cancel_btn:
            self._cancel_btn.setText(t("settings.cancel"))

    def _accept(self) -> None:
        updated = Settings(
            scale=self._initial.scale,
            fps=self._initial.fps,
            opacity=float(self._opacity.value()),
            hunger_decay_rate=self._initial.hunger_decay_rate,
            mood_decay_rate=self._initial.mood_decay_rate,
            intimacy_threshold=self._initial.intimacy_threshold,
            max_pets=self._initial.max_pets,
            auto_run_enabled=self._initial.auto_run_enabled,
            auto_walk_enabled=self._auto_walk.isChecked(),
            show_stat_hud=self._stat_hud.isChecked(),
            gold=self._initial.gold,
            inventory=dict(self._initial.inventory),
            daily_gold_earned=self._initial.daily_gold_earned,
            daily_reset_date=self._initial.daily_reset_date,
            game_stats=dict(self._initial.game_stats),
            default_skin=self._initial.default_skin,
            text_pools=dict(self._initial.text_pools),
            language=str(self._lang_combo.currentData()),
        )
        self._on_save(updated)
        self.accept()
