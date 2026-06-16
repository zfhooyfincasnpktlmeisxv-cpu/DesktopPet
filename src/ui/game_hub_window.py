"""陪玩打工 — 小游戏中心（深色科技风）"""
from __future__ import annotations

import logging
import random
from typing import Callable, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..games.game_registry import create_game_widget, list_games
from ..i18n import game_meta, shop_item, t
from ..utils.constants import (
    DAILY_GOLD_CAP,
    GAME_SNAKE_ID,
    GAME_THEME,
    RICHMAN_FEATURE,
    CHESS_FEATURE,
)

if TYPE_CHECKING:
    from ..core.economy_manager import EconomyManager

logger = logging.getLogger(__name__)


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


def _game_stylesheet(theme: dict) -> str:
    bg = _rgb(theme["background"])
    surface = _rgb(theme["surface"])
    border = _rgb(theme["surface_border"])
    accent = _rgb(theme["accent"])
    accent_hover = _rgb(theme["accent_hover"])
    text = _rgb(theme["text"])
    muted = _rgb(theme["text_muted"])
    return f"""
QDialog {{
    background-color: {bg};
}}
QLabel {{
    color: {text};
    background: transparent;
}}
QFrame#panel {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: {theme["radius"]}px;
}}
QFrame#feedback {{
    background-color: rgb(18, 26, 40);
    border: 1px solid {_rgb(theme["panel_glow"])};
    border-radius: {theme["radius"]}px;
}}
QPushButton#primary {{
    background-color: {accent};
    color: rgb(14, 18, 28);
    border: none;
    border-radius: 9px;
    padding: 9px 18px;
    font-weight: 700;
    min-width: 88px;
}}
QPushButton#primary:hover {{
    background-color: {accent_hover};
}}
QPushButton#ghost {{
    background-color: transparent;
    color: {muted};
    border: 1px solid {border};
    border-radius: 9px;
    padding: 8px 16px;
}}
QPushButton#ghost:hover {{
    background-color: rgb(30, 38, 54);
    color: {text};
}}
QComboBox {{
    background-color: rgb(18, 24, 36);
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 5px 10px;
    min-height: 28px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: rgb(22, 28, 42);
    color: {text};
    selection-background-color: {accent};
    selection-color: rgb(14, 18, 28);
    border: 1px solid {border};
}}
QCheckBox {{
    color: {muted};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border};
    border-radius: 4px;
    background: rgb(18, 24, 36);
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}
"""


_POSITIVE_EVENTS = frozenset({
    "food", "catch", "match", "near_miss", "complete",
    "milestone_3", "milestone_4", "milestone_5", "milestone_6",
    "milestone_8", "milestone_10", "milestone_15", "milestone_30",
    "milestone_60", "long",
})


def _pick_feedback(game_id: str, event: str) -> str:
    from ..i18n import game_feedback_line
    return game_feedback_line(game_id, event)


def _gold_daily_text(economy: "EconomyManager") -> str:
    return t(
        "game_hub.gold_today",
        left=economy.daily_remaining(),
        cap=DAILY_GOLD_CAP,
    )


class GamePlayDialog(QDialog):
    """单局游戏对话框（内含游戏控件与结算）。"""

    def __init__(
        self,
        game_id: str,
        economy_mgr: "EconomyManager",
        on_reward: Optional[Callable[[int, int, bool], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._game_id = game_id
        self._economy = economy_mgr
        self._on_reward = on_reward
        self._theme = GAME_THEME
        self._award = 0
        self._hit_cap = False
        self._game_session_active = False

        meta = list_games().get(game_id, {})
        i18n = game_meta(game_id)
        title = i18n.get("name") or meta.get("name", "Mini-game")
        self.setWindowTitle(t("game_hub.session_title", name=title))
        self.setModal(True)
        self.setMinimumWidth(440)
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(_game_stylesheet(self._theme))

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 14)
        root.setSpacing(10)

        # 桌宠反馈区
        feedback_frame = QFrame()
        feedback_frame.setObjectName("feedback")
        feedback_layout = QVBoxLayout(feedback_frame)
        feedback_layout.setContentsMargins(14, 12, 14, 12)
        feedback_layout.setSpacing(4)

        feedback_title = QLabel(t("game_hub.pet_live"))
        feedback_title.setStyleSheet(
            f"color: {_rgb(self._theme['text_accent'])}; font-size: 11px; font-weight: 600;"
        )
        feedback_layout.addWidget(feedback_title)

        self._feedback_label = QLabel(t("game_hub.waiting"))
        self._feedback_label.setWordWrap(True)
        self._feedback_label.setMinimumHeight(40)
        self._feedback_label.setStyleSheet(
            f"color: {_rgb(self._theme['text'])}; font-size: 13px; line-height: 1.4;"
        )
        feedback_layout.addWidget(self._feedback_label)
        root.addWidget(feedback_frame)

        daily_left = self._economy.daily_remaining()
        self._daily_label = QLabel(_gold_daily_text(self._economy))
        self._daily_label.setStyleSheet(
            f"font-size: 12px; color: {_rgb(self._theme['gold_text'])};"
        )
        root.addWidget(self._daily_label)

        # 画面设置行
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)

        fps_label = QLabel(t("game_hub.fps"))
        fps_label.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])};")
        settings_row.addWidget(fps_label)

        self._fps_combo = QComboBox()
        self._fps_combo.addItem("60 FPS", 60)
        self._fps_combo.addItem("30 FPS", 30)
        self._fps_combo.setCurrentIndex(0)
        self._fps_combo.currentIndexChanged.connect(self._on_fps_changed)
        settings_row.addWidget(self._fps_combo)

        self._vsync_check = QCheckBox(t("game_hub.vsync"))
        self._vsync_check.setChecked(True)
        self._vsync_check.setToolTip("与显示器刷新对齐，画面更顺滑；开启时固定 60Hz 渲染")
        self._vsync_check.toggled.connect(self._on_vsync_changed)
        settings_row.addWidget(self._vsync_check)

        settings_row.addStretch(1)
        hint = QLabel(meta.get("description", ""))
        hint.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        settings_row.addWidget(hint)
        root.addLayout(settings_row)

        self._game = create_game_widget(game_id, self)
        if self._game is None:
            root.addWidget(QLabel("游戏加载失败"))
            self._game = None
        else:
            self._game.game_finished.connect(self._on_game_finished)
            self._game.game_event.connect(self._on_game_event)
            self._apply_display_settings()
            root.addWidget(self._game, alignment=Qt.AlignmentFlag.AlignCenter)

        self._result_label = QLabel("")
        self._result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._result_label.setWordWrap(True)
        self._result_label.setMinimumHeight(32)
        root.addWidget(self._result_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self._again_btn = QPushButton("再来一局")
        self._again_btn.setObjectName("primary")
        self._again_btn.clicked.connect(self._restart)
        self._again_btn.setVisible(False)
        btn_row.addWidget(self._again_btn)

        close_btn = QPushButton(t("game_hub.close"))
        close_btn.setObjectName("ghost")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

        if self._game is not None:
            self._begin_pet_spectator()
            self._game.start_game()

    def _refresh_daily_label(self) -> None:
        self._daily_label.setText(_gold_daily_text(self._economy))

    def _get_pet_app(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        return app.property("desktop_pet_app") if app else None

    def _begin_pet_spectator(self) -> None:
        pet_app = self._get_pet_app()
        if pet_app and hasattr(pet_app, "begin_game_session"):
            pet_app.begin_game_session()
            self._game_session_active = True
            self.raise_()
            self.activateWindow()

    def _end_pet_spectator(self) -> None:
        if not self._game_session_active:
            return
        pet_app = self._get_pet_app()
        if pet_app and hasattr(pet_app, "end_game_session"):
            pet_app.end_game_session()
        self._game_session_active = False

    def _apply_display_settings(self) -> None:
        if self._game is None:
            return
        fps = self._fps_combo.currentData()
        vsync = self._vsync_check.isChecked()
        self._fps_combo.setEnabled(not vsync)
        if vsync:
            self._fps_combo.setToolTip("垂直同步开启时固定 60Hz 渲染")
        else:
            self._fps_combo.setToolTip("")
        self._game.set_vsync(vsync)
        self._game.set_render_fps(int(fps))

    def _on_fps_changed(self, _index: int) -> None:
        self._apply_display_settings()

    def _on_vsync_changed(self, _checked: bool) -> None:
        self._apply_display_settings()

    def _on_game_event(self, event: str, score: int) -> None:
        text = _pick_feedback(self._game_id, event)
        if event in ("danger", "mismatch"):
            self._feedback_label.setStyleSheet(
                f"color: {_rgb(self._theme['danger'])}; font-size: 13px; font-weight: 600;"
            )
        elif event in _POSITIVE_EVENTS:
            self._feedback_label.setStyleSheet(
                f"color: {_rgb(self._theme['success'])}; font-size: 13px;"
            )
        elif event == "death":
            self._feedback_label.setStyleSheet(
                f"color: {_rgb(self._theme['text_muted'])}; font-size: 13px;"
            )
        else:
            self._feedback_label.setStyleSheet(
                f"color: {_rgb(self._theme['text'])}; font-size: 13px;"
            )
        self._feedback_label.setText(text)
        logger.debug("桌宠反馈 [%s] score=%s: %s", event, score, text)

    def _restart(self) -> None:
        self._award = 0
        self._hit_cap = False
        self._result_label.setText("")
        self._again_btn.setVisible(False)
        self._feedback_label.setText("新的一局，冲！")
        self._feedback_label.setStyleSheet(
            f"color: {_rgb(self._theme['text_accent'])}; font-size: 13px;"
        )
        daily_left = self._economy.daily_remaining()
        self._daily_label.setText(_gold_daily_text(self._economy))
        self._apply_display_settings()
        if self._game is not None:
            self._begin_pet_spectator()
            self._game.start_game()

    def _on_game_finished(self, score: int) -> None:
        award, hit_cap = self._economy.award_game_reward(self._game_id, score)
        self._award = award
        self._hit_cap = hit_cap

        if award > 0:
            self._result_label.setText(f"本局得分 {score}，获得 {award} 金币！")
            self._result_label.setStyleSheet(
                f"color: {_rgb(self._theme['success'])}; font-weight: 600;"
            )
        elif hit_cap:
            self._result_label.setText(
                f"本局得分 {score}。今日打工金币已满（{DAILY_GOLD_CAP}），明日再来～"
            )
            self._result_label.setStyleSheet(
                f"color: {_rgb(self._theme['gold_text'])}; font-weight: 600;"
            )
        else:
            self._result_label.setText(f"本局得分 {score}，未获得金币。")
            self._result_label.setStyleSheet(
                f"color: {_rgb(self._theme['text_muted'])};"
            )

        daily_left = self._economy.daily_remaining()
        self._daily_label.setText(_gold_daily_text(self._economy))

        if not hit_cap:
            self._again_btn.setVisible(True)

        if self._on_reward is not None:
            self._on_reward(score, award, hit_cap)

    def closeEvent(self, event) -> None:
        if self._game is not None:
            self._game.stop_game()
        self._end_pet_spectator()
        super().closeEvent(event)


class GameHubWindow(QDialog):
    """小游戏列表入口。"""

    def __init__(
        self,
        economy_mgr: "EconomyManager",
        on_reward: Optional[Callable[[int, int, bool], None]] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._economy = economy_mgr
        self._on_reward = on_reward
        self._theme = GAME_THEME

        self._title_label: Optional[QLabel] = None
        self._subtitle_label: Optional[QLabel] = None
        self._mini_title_label: Optional[QLabel] = None
        self._close_btn: Optional[QPushButton] = None

        self.setWindowTitle(t("game_hub.title"))
        self.setModal(False)
        self.setMinimumSize(380, 480)
        self.setStyleSheet(_game_stylesheet(self._theme))

        font = QFont(self._theme["font_family"], 10)
        self.setFont(font)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 14)
        root.setSpacing(12)

        self._title_label = QLabel(t("game_hub.title"))
        self._title_label.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_rgb(self._theme['text_accent'])};"
        )
        root.addWidget(self._title_label)

        self._subtitle_label = QLabel(t("game_hub.subtitle"))
        self._subtitle_label.setWordWrap(True)
        self._subtitle_label.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])};")
        root.addWidget(self._subtitle_label)

        self._daily_label = QLabel(_gold_daily_text(self._economy))
        self._daily_label.setStyleSheet(
            f"color: {_rgb(self._theme['gold_text'])}; font-weight: 600;"
        )
        root.addWidget(self._daily_label)

        root.addWidget(self._build_richman_feature())
        root.addWidget(self._build_chess_feature())

        self._mini_title_label = QLabel(t("game_hub.mini_games"))
        self._mini_title_label.setStyleSheet(
            f"color: {_rgb(self._theme['text_muted'])}; font-size: 12px; margin-top: 4px;"
        )
        root.addWidget(self._mini_title_label)

        for game_id, meta in list_games().items():
            root.addWidget(self._build_game_card(game_id, meta))

        root.addStretch(1)

        self._close_btn = QPushButton(t("game_hub.close"))
        self._close_btn.setObjectName("ghost")
        self._close_btn.clicked.connect(self.close)
        root.addWidget(self._close_btn)

    def retranslate_ui(self) -> None:
        self.setWindowTitle(t("game_hub.title"))
        if self._title_label:
            self._title_label.setText(t("game_hub.title"))
        if self._subtitle_label:
            self._subtitle_label.setText(t("game_hub.subtitle"))
        if self._mini_title_label:
            self._mini_title_label.setText(t("game_hub.mini_games"))
        if self._close_btn:
            self._close_btn.setText(t("game_hub.close"))
        self.refresh()

    def refresh(self) -> None:
        self._daily_label.setText(_gold_daily_text(self._economy))

    def _build_richman_feature(self) -> QFrame:
        meta = RICHMAN_FEATURE
        i18n = game_meta(meta["id"])
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setStyleSheet(
            f"QFrame#panel {{ border: 2px solid {_rgb(self._theme['accent'])}; }}"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(16, 14, 16, 14)

        title = QLabel(
            f"{meta['emoji']}  {i18n['name']}  · {t('game_hub.featured')}"
        )
        title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_rgb(self._theme['text_accent'])};"
        )
        row.addWidget(title)

        desc = QLabel(i18n.get("description", ""))
        desc.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        row.addWidget(desc)

        stats = self._economy.get_game_stats(meta["id"])
        wins = stats.get("wins", 0)
        if wins > 0:
            badge = QLabel(t("game_hub.wins_badge", count=wins))
            badge.setStyleSheet(f"color: {_rgb(self._theme['gold_text'])}; font-size: 12px;")
            row.addWidget(badge)

        row.addStretch(1)

        play_btn = QPushButton(t("game_hub.enter_3d_board"))
        play_btn.setObjectName("primary")
        play_btn.clicked.connect(self._open_richman)
        row.addWidget(play_btn)

        return frame

    def _open_richman(self) -> None:
        from ..games.richman.player_setup import pick_richman_setup
        from ..games.richman.session_window import RichmanSessionWindow

        setup = pick_richman_setup(parent=self)
        if setup is None:
            return
        dialog = RichmanSessionWindow(setup=setup, parent=self)
        dialog.exec()
        self.refresh()

    def _build_chess_feature(self) -> QFrame:
        meta = CHESS_FEATURE
        i18n = game_meta(meta["id"])
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setStyleSheet(
            f"QFrame#panel {{ border: 2px solid {_rgb(self._theme['accent'])}; }}"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(16, 14, 16, 14)

        title = QLabel(
            f"{meta['emoji']}  {i18n['name']}  · {t('game_hub.featured')}"
        )
        title.setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {_rgb(self._theme['text_accent'])};"
        )
        row.addWidget(title)

        desc = QLabel(i18n.get("description", ""))
        desc.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        row.addWidget(desc)

        stats = self._economy.get_game_stats(meta["id"])
        wins = stats.get("wins", 0)
        if wins > 0:
            badge = QLabel(t("game_hub.wins_badge", count=wins))
            badge.setStyleSheet(f"color: {_rgb(self._theme['gold_text'])}; font-size: 12px;")
            row.addWidget(badge)

        row.addStretch(1)

        play_btn = QPushButton(t("game_hub.start_match"))
        play_btn.setObjectName("primary")
        play_btn.clicked.connect(self._open_chess)
        row.addWidget(play_btn)

        return frame

    def _open_chess(self) -> None:
        from ..games.chess.player_setup import pick_chess_setup
        from ..games.chess.session_window import ChessSessionWindow

        setup = pick_chess_setup(parent=self)
        if setup is None:
            return
        dialog = ChessSessionWindow(setup=setup, parent=self)
        dialog.exec()
        self.refresh()

    def _build_game_card(self, game_id: str, meta: dict) -> QFrame:
        i18n = game_meta(game_id)
        frame = QFrame()
        frame.setObjectName("panel")
        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 12, 14, 12)

        emoji = meta.get("emoji", "🎮")
        name = QLabel(f"{emoji}  {i18n.get('name', meta.get('name', game_id))}")
        name.setStyleSheet("font-size: 14px; font-weight: 600;")
        row.addWidget(name)

        stats = self._economy.get_game_stats(game_id)
        best = stats.get("best_score", 0)
        if best > 0:
            badge = QLabel(t("game_hub.best_score", score=best))
            badge.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 12px;")
            row.addWidget(badge)

        row.addStretch(1)

        play_btn = QPushButton(t("game_hub.start"))
        play_btn.setObjectName("primary")
        play_btn.clicked.connect(lambda: self._play(game_id))
        row.addWidget(play_btn)

        return frame

    def _play(self, game_id: str) -> None:
        dialog = GamePlayDialog(
            game_id,
            self._economy,
            on_reward=self._on_reward,
            parent=self,
        )
        dialog.exec()
        self.refresh()

    def play_snake(self) -> None:
        """直接打开贪吃蛇（菜单快捷入口）。"""
        self._play(GAME_SNAKE_ID)
