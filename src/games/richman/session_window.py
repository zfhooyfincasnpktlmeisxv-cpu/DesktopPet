"""大富翁旗舰会话窗口"""
from __future__ import annotations

import logging
import random
from typing import Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...utils.constants import GAME_THEME, RICHMAN_PACE
from .audio_manager import RichmanAudioManager
from .board_data import get_tile
from .dice_panel import RichmanDicePanel
from .game_balance import JAIL_BAIL
from .game_engine import GamePhase, RichmanEngine
from .player_setup import RichmanSetup
from .property_rules import compute_rent

logger = logging.getLogger(__name__)


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


class RichmanSessionWindow(QDialog):
    """全屏级大富翁对局窗口。"""

    def __init__(self, setup: RichmanSetup, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup = setup
        self._theme = GAME_THEME
        self._engine = RichmanEngine(self)
        self._turn_timer = QTimer(self)
        self._turn_timer.setSingleShot(True)
        self._turn_timer.timeout.connect(self._on_turn_timer)
        self._game_session_active = False
        self._audio = RichmanAudioManager(self)
        self._audio.prepare()

        self.setWindowTitle("陪玩打工 · 大富翁")
        self.setMinimumSize(1080, 720)
        self.resize(1180, 760)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._apply_style()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("🎲  大富翁")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {_rgb(self._theme['text_accent'])};"
        )
        header.addWidget(title)
        self._phase_label = QLabel("")
        self._phase_label.setStyleSheet(f"color: {_rgb(self._theme['gold_text'])};")
        header.addWidget(self._phase_label)
        header.addStretch(1)
        hint = QLabel("滚轮缩放棋盘 · 左键拖移")
        hint.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        header.addWidget(hint)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._viewport = self._create_viewport()
        splitter.addWidget(self._viewport)

        side = QFrame()
        side.setObjectName("side")
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(10)

        self._dice_panel = RichmanDicePanel()
        side_layout.addWidget(self._dice_panel)

        self._players_widget = QWidget()
        self._players_layout = QVBoxLayout(self._players_widget)
        self._players_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(self._players_widget)

        self._tile_label = QLabel("")
        self._tile_label.setWordWrap(True)
        self._tile_label.setStyleSheet(
            f"background: rgb(18,26,40); border: 1px solid {_rgb(self._theme['surface_border'])};"
            f" border-radius: 8px; padding: 10px; color: {_rgb(self._theme['text'])};"
        )
        side_layout.addWidget(self._tile_label)

        self._action_hint = QLabel("")
        self._action_hint.setWordWrap(True)
        self._action_hint.setStyleSheet(
            f"color: {_rgb(self._theme['gold_text'])}; font-size: 12px; padding: 2px 4px;"
        )
        side_layout.addWidget(self._action_hint)

        log_scroll = QScrollArea()
        log_scroll.setWidgetResizable(True)
        log_scroll.setMinimumHeight(160)
        self._log_label = QLabel("")
        self._log_label.setWordWrap(True)
        self._log_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        log_scroll.setWidget(self._log_label)
        side_layout.addWidget(log_scroll, stretch=1)

        btn_row = QHBoxLayout()
        self._roll_btn = QPushButton("掷骰子")
        self._roll_btn.setObjectName("primary")
        self._roll_btn.clicked.connect(self._on_roll)
        btn_row.addWidget(self._roll_btn)

        self._build_btn = QPushButton("盖房")
        self._build_btn.setObjectName("ghost")
        self._build_btn.clicked.connect(self._on_build)
        btn_row.addWidget(self._build_btn)

        self._bail_btn = QPushButton("交保释金")
        self._bail_btn.setObjectName("ghost")
        self._bail_btn.clicked.connect(self._on_bail)
        btn_row.addWidget(self._bail_btn)

        self._buy_btn = QPushButton("购买地产")
        self._buy_btn.setObjectName("ghost")
        self._buy_btn.clicked.connect(self._on_buy)
        btn_row.addWidget(self._buy_btn)

        self._skip_btn = QPushButton("跳过")
        self._skip_btn.setObjectName("ghost")
        self._skip_btn.clicked.connect(self._on_skip)
        btn_row.addWidget(self._skip_btn)
        side_layout.addLayout(btn_row)

        close_btn = QPushButton("结束对局")
        close_btn.setObjectName("ghost")
        close_btn.clicked.connect(self.close)
        side_layout.addWidget(close_btn)

        splitter.addWidget(side)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        self._engine.log_message.connect(self._append_log)
        self._engine.state_changed.connect(self._refresh_ui)
        self._engine.phase_changed.connect(self._refresh_ui)
        self._engine.dice_rolled.connect(self._on_dice_rolled)
        self._engine.card_drawn.connect(self._on_card_drawn)
        self._engine.movement_finished.connect(self._on_movement_finished)
        self._engine.game_over.connect(self._on_game_over)
        self._engine.game_event.connect(self._on_game_event)

        self._engine.new_game(players=setup.players)
        self._begin_pet_spectator()
        self._audio.start_bgm()
        self._refresh_ui()

    def _create_viewport(self) -> QWidget:
        from .viewport_factory import create_board_viewport

        return create_board_viewport(self._engine, self)

    def _apply_style(self) -> None:
        t = self._theme
        self.setStyleSheet(
            f"""
            QDialog {{ background: {_rgb(t['background'])}; color: {_rgb(t['text'])}; }}
            QLabel {{ color: {_rgb(t['text'])}; }}
            QFrame#side {{
                background: {_rgb(t['surface'])};
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: {t['radius']}px;
            }}
            QPushButton#primary {{
                background: {_rgb(t['accent'])};
                color: rgb(14,18,28);
                border: none;
                border-radius: 9px;
                padding: 10px 16px;
                font-weight: 700;
            }}
            QPushButton#primary:hover {{ background: {_rgb(t['accent_hover'])}; }}
            QPushButton#primary:disabled {{ background: rgb(60,70,90); color: rgb(140,150,165); }}
            QPushButton#ghost {{
                background: transparent;
                color: {_rgb(t['text_muted'])};
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: 9px;
                padding: 9px 14px;
            }}
            QPushButton#ghost:hover {{ background: rgb(30,38,54); color: {_rgb(t['text'])}; }}
            QPushButton#ghost:disabled {{
                color: rgb(78, 88, 108);
                border-color: rgb(42, 50, 66);
                background: transparent;
            }}
            QScrollArea {{ border: none; background: transparent; }}
            """
        )
        self.setFont(QFont(t["font_family"], 10))

    def _get_pet_app(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        return app.property("desktop_pet_app") if app else None

    def _begin_pet_spectator(self) -> None:
        pet_app = self._get_pet_app()
        if pet_app and hasattr(pet_app, "begin_game_session"):
            pet_app.begin_game_session()
            self._game_session_active = True

    def _end_pet_spectator(self) -> None:
        if not self._game_session_active:
            return
        pet_app = self._get_pet_app()
        if pet_app and hasattr(pet_app, "end_game_session"):
            pet_app.end_game_session()
        self._game_session_active = False

    def _append_log(self, text: str) -> None:
        prev = self._log_label.text()
        self._log_label.setText((prev + "\n" + text).strip())

    def _refresh_ui(self) -> None:
        while self._players_layout.count():
            item = self._players_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        cp = self._engine.current_player
        for p in self._engine.players():
            mark = "▶ " if p.id == cp.id else "   "
            role = "👤" if p.is_human else "🤖"
            state = "破产" if p.bankrupt else f"¥{p.money}"
            lbl = QLabel(f"{mark}{role} {p.name}  {state}")
            if p.id == cp.id:
                lbl.setStyleSheet(f"color: {_rgb(self._theme['text_accent'])}; font-weight: 600;")
            elif p.bankrupt:
                lbl.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])};")
            self._players_layout.addWidget(lbl)

        tile = get_tile(cp.position)
        prop = self._engine.property_at(cp.position)
        owner = ""
        if prop.owner_id is not None:
            owner = self._engine.players()[prop.owner_id].name
        build_hint = ""
        if prop.level > 0:
            build_hint = f"  建筑：{'酒店' if prop.level >= 4 else f'{prop.level} 栋'}"
        rent_hint = tile.rent
        if prop.owner_id is not None:
            rent_hint = compute_rent(tile, prop, self._engine._properties)
        self._tile_label.setText(
            f"当前格：【{tile.name}】\n"
            f"类型：{tile.kind.value}  地价：¥{tile.price}  租金：¥{rent_hint}{build_hint}\n"
            f"地主：{owner or '—'}"
        )

        phase = self._engine.phase
        human_active = self._engine.is_human_turn()

        if phase == GamePhase.GAME_OVER:
            self._phase_label.setText("对局结束")
            self._action_hint.setText("")
        elif cp.pending_jail_skip and phase == GamePhase.WAIT_ROLL:
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（监狱 · 停一回合）"
            )
            self._action_hint.setText(
                f"本回合无法掷骰。可交保释金 ¥{JAIL_BAIL} 立即行动，"
                f"或等待自动跳过 / 点「跳过回合」"
            )
        elif cp.in_jail and phase == GamePhase.WAIT_ROLL:
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（监狱 · 可掷骰出狱）"
            )
            self._action_hint.setText("已停过一回合，掷骰即可离开监狱格")
        elif human_active and phase == GamePhase.WAIT_ROLL:
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（本地玩家 · 你的回合）"
            )
            self._action_hint.setText("▶ 轮到你了，请点击「掷骰子」")
        elif cp.is_human and not cp.bankrupt and phase == GamePhase.MOVING:
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（移动中）"
            )
            self._action_hint.setText("棋子逐格前进中…")
        elif human_active and phase == GamePhase.ACTION:
            tile = get_tile(cp.position)
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（你的回合）"
            )
            if self._engine.can_buy_current():
                self._action_hint.setText(
                    f"▶ 抵达【{tile.name}】，可选择「购买地产」或「跳过」"
                )
            else:
                self._action_hint.setText(
                    f"▶ 抵达【{tile.name}】，资金不足购买，请点击「跳过」"
                )
        elif human_active and phase == GamePhase.RESOLVING:
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（结算中）"
            )
            self._action_hint.setText("本回合结算中，稍候自动进入下一位玩家…")
        elif not cp.is_human and phase in (
            GamePhase.WAIT_ROLL,
            GamePhase.ACTION,
            GamePhase.RESOLVING,
        ):
            self._phase_label.setText(
                f"第 {self._engine.turn_number} 轮 · {cp.name}（思考中…）"
            )
            self._action_hint.setText("等待其他玩家行动，请稍候…")
        else:
            self._phase_label.setText(f"第 {self._engine.turn_number} 轮 · {cp.name}")
            self._action_hint.setText("")

        self._roll_btn.setEnabled(
            human_active
            and phase == GamePhase.WAIT_ROLL
            and self._engine.can_roll()
            and not self._engine.is_moving
        )
        self._build_btn.setEnabled(human_active and self._engine.can_build_house())
        self._bail_btn.setEnabled(human_active and self._engine.can_pay_jail_bail())
        self._buy_btn.setEnabled(human_active and self._engine.can_buy_current())
        skip_jail = human_active and self._engine.can_skip_jail_turn()
        skip_buy = human_active and self._engine.can_skip_current() and not skip_jail
        self._skip_btn.setEnabled(skip_jail or skip_buy)
        self._skip_btn.setText("跳过回合" if skip_jail else "跳过")

        self._dice_panel.sync_from_engine(self._engine)
        self._schedule_turn_flow()

    def _on_dice_rolled(self, d1: int, d2: int) -> None:
        roller = self._engine.current_player
        self._dice_panel.on_dice_rolled(roller.id, d1, d2)
        self._audio.play_dice()
        if hasattr(self._viewport, "play_fx"):
            self._viewport.play_fx("dice", roller.position)
        self._refresh_ui()

    def _on_movement_finished(self, player_id: int) -> None:
        if hasattr(self._viewport, "sync_player_token"):
            self._viewport.sync_player_token(player_id)
        self._audio.play("dice_land")
        if hasattr(self._viewport, "play_fx"):
            self._viewport.play_fx("dice_land")
        self._refresh_ui()

    def _on_game_event(self, event: str) -> None:
        self._audio.play(event)
        if hasattr(self._viewport, "play_fx"):
            self._viewport.play_fx(event)

    def _on_card_drawn(self, deck_name: str, text: str) -> None:
        from .card_dialog import show_card

        show_card(self, deck_name, text)
        self._refresh_ui()

    def _on_build(self) -> None:
        self._engine.build_house()
        self._refresh_ui()

    def _on_bail(self) -> None:
        self._turn_timer.stop()
        self._engine.pay_jail_bail()
        self._refresh_ui()

    def _bot_delay_ms(self) -> int:
        pace = RICHMAN_PACE
        return random.randint(pace["bot_delay_min_ms"], pace["bot_delay_max_ms"])

    def _resolve_delay_ms(self) -> int:
        pace = RICHMAN_PACE
        if self._engine.current_player.is_human:
            return int(pace["human_resolve_ms"])
        return int(pace["bot_resolve_ms"])

    def _schedule_turn_flow(self) -> None:
        cp = self._engine.current_player
        phase = self._engine.phase

        if phase == GamePhase.GAME_OVER or phase == GamePhase.MOVING:
            self._turn_timer.stop()
            return

        if phase == GamePhase.RESOLVING:
            if self._turn_timer.isActive():
                return
            self._turn_timer.start(self._resolve_delay_ms())
            return

        if cp.is_human:
            if phase == GamePhase.WAIT_ROLL and self._engine.can_skip_jail_turn():
                if not self._turn_timer.isActive():
                    self._turn_timer.start(2000)
                return
            if phase != GamePhase.RESOLVING:
                self._turn_timer.stop()
            return

        if phase in (GamePhase.WAIT_ROLL, GamePhase.ACTION):
            if self._turn_timer.isActive():
                return
            self._turn_timer.start(self._bot_delay_ms())

    def _on_turn_timer(self) -> None:
        phase = self._engine.phase
        if phase == GamePhase.RESOLVING:
            if self._engine.is_human_turn():
                self._engine.complete_turn()
            else:
                self._engine.bot_take_turn()
        elif self._engine.can_skip_jail_turn() and self._engine.is_human_turn():
            self._engine.skip_jail_turn()
            self._refresh_ui()
        else:
            self._engine.bot_take_turn()
        self._schedule_turn_flow()

    def _on_roll(self) -> None:
        self._engine.roll_dice()
        self._refresh_ui()

    def _on_buy(self) -> None:
        self._engine.buy_current_property()
        self._refresh_ui()

    def _on_skip(self) -> None:
        self._turn_timer.stop()
        self._engine.skip_action()
        self._refresh_ui()

    def _on_game_over(self, winner_id: int) -> None:
        self._turn_timer.stop()
        winner = self._engine.players()[winner_id]
        self._audio.fade_bgm_for_win()
        self._audio.play("win")
        if hasattr(self._viewport, "play_fx"):
            self._viewport.play_fx("win")
        self._append_log(f"对局结束，恭喜 {winner.name}！")
        pet_app = self._get_pet_app()
        if pet_app and hasattr(pet_app, "on_richman_finished"):
            pet_app.on_richman_finished(winner.is_human)

    def closeEvent(self, event) -> None:
        self._turn_timer.stop()
        self._audio.shutdown()
        self._end_pet_spectator()
        super().closeEvent(event)
