"""国际象棋会话窗口"""
from __future__ import annotations

import logging
from typing import Optional

import chess
from PyQt6.QtCore import Qt, QThread, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...utils.constants import GAME_THEME
from .ai_worker import ChessAiWorker
from .board_viewport import ChessBoardViewport
from .game_engine import ChessEngine, ChessPhase
from .player_setup import ChessSetup

logger = logging.getLogger(__name__)

_AI_DELAY_MS = 450


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


class ChessSessionWindow(QDialog):
    def __init__(self, setup: ChessSetup, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup = setup
        self._theme = GAME_THEME
        self._engine = ChessEngine(self)
        self._ai_timer = QTimer(self)
        self._ai_timer.setSingleShot(True)
        self._ai_timer.timeout.connect(self._start_ai_compute)
        self._ai_thread = QThread(self)
        self._ai_worker = ChessAiWorker()
        self._ai_worker.moveToThread(self._ai_thread)
        self._ai_worker.move_ready.connect(self._apply_ai_move)
        self._ai_thread.start()
        self._ai_busy = False
        self._game_session_active = False
        self._pending_from: Optional[int] = None

        self.setWindowTitle("陪玩打工 · 国际象棋")
        self.setMinimumSize(920, 640)
        self.resize(980, 700)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self._apply_style()

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("♟  国际象棋")
        title.setStyleSheet(
            f"font-size: 20px; font-weight: 700; color: {_rgb(self._theme['text_accent'])};"
        )
        header.addWidget(title)
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {_rgb(self._theme['gold_text'])};")
        header.addWidget(self._status_label)
        header.addStretch(1)
        root.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._board = ChessBoardViewport(self._engine, self)
        self._board.set_flipped(
            setup.black_is_human and not setup.white_is_human
        )
        self._board.square_clicked.connect(self._on_square_clicked)
        splitter.addWidget(self._board)

        side = QFrame()
        side.setObjectName("side")
        side_layout = QVBoxLayout(side)
        side_layout.setSpacing(10)

        self._turn_label = QLabel("")
        self._turn_label.setWordWrap(True)
        side_layout.addWidget(self._turn_label)

        self._hint_label = QLabel("点击棋子选中，再点击目标格走棋（每回合只能走一步）")
        self._hint_label.setWordWrap(True)
        self._hint_label.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        side_layout.addWidget(self._hint_label)

        self._log_label = QLabel("")
        self._log_label.setWordWrap(True)
        self._log_label.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        side_layout.addWidget(self._log_label)

        side_layout.addStretch(1)

        self._resign_btn = QPushButton("认输")
        self._resign_btn.setObjectName("ghost")
        self._resign_btn.clicked.connect(self._on_resign)
        side_layout.addWidget(self._resign_btn)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("ghost")
        close_btn.clicked.connect(self.close)
        side_layout.addWidget(close_btn)

        splitter.addWidget(side)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        self._engine.log_message.connect(self._append_log)
        self._engine.state_changed.connect(self._refresh_ui)
        self._engine.move_made.connect(self._on_move_made)
        self._engine.game_over.connect(self._on_game_over)

        self._engine.new_game(setup)
        self._begin_pet_spectator()
        self._refresh_ui()
        self._maybe_schedule_ai()

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
                padding: 12px;
            }}
            QPushButton#ghost {{
                background: transparent;
                color: {_rgb(t['text_muted'])};
                border: 1px solid {_rgb(t['surface_border'])};
                border-radius: 9px;
                padding: 9px 14px;
            }}
            QPushButton#ghost:hover {{ background: rgb(30,38,54); color: {_rgb(t['text'])}; }}
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

    def _can_human_input(self) -> bool:
        return (
            self._engine.phase == ChessPhase.WAIT_MOVE
            and not self._ai_busy
            and self._engine.is_human_turn()
        )

    def _refresh_ui(self) -> None:
        phase = self._engine.phase
        if phase == ChessPhase.GAME_OVER:
            self._status_label.setText(self._engine.result_text)
            self._turn_label.setText("对局结束")
            self._resign_btn.setEnabled(False)
            return

        name = self._engine.current_player_name()
        side = "白方" if self._engine.board.turn == chess.WHITE else "黑方"
        if phase == ChessPhase.THINKING or self._ai_busy:
            self._status_label.setText(f"{name} 思考中…")
        else:
            self._status_label.setText(f"轮到 {name}（{side}）")
        self._turn_label.setText(
            f"白：{self._setup.white_name}"
            + (" 👤" if self._setup.white_is_human else " 🤖")
            + f"\n黑：{self._setup.black_name}"
            + (" 👤" if self._setup.black_is_human else " 🤖")
        )
        self._resign_btn.setEnabled(True)

    def _clear_pick(self) -> None:
        self._pending_from = None
        self._board.clear_selection()

    def _on_move_made(self, _uci: str, _san: str) -> None:
        self._clear_pick()

    def _on_square_clicked(self, sq: int) -> None:
        if not self._can_human_input():
            self._clear_pick()
            return

        piece = self._engine.board.piece_at(sq)
        turn = self._engine.board.turn

        if self._pending_from is not None:
            from_sq = self._pending_from
            if sq == from_sq:
                self._clear_pick()
                return
            uci = chess.square_name(from_sq) + chess.square_name(sq)
            if self._try_move(uci):
                self._maybe_schedule_ai()
                return
            if piece and piece.color == turn:
                self._pending_from = sq
                targets = [m.to_square for m in self._engine.legal_moves_from(sq)]
                self._board.select_square(sq, targets)
                return
            self._clear_pick()
            return

        if piece and piece.color == turn:
            self._pending_from = sq
            targets = [m.to_square for m in self._engine.legal_moves_from(sq)]
            self._board.select_square(sq, targets)

    def _try_move(self, uci: str) -> bool:
        if not self._can_human_input():
            return False
        if self._engine.needs_promotion(uci):
            promo = self._ask_promotion()
            if not promo:
                return False
            return self._engine.make_move(uci, promo)
        return self._engine.make_move(uci)

    def _ask_promotion(self) -> Optional[str]:
        box = QMessageBox(self)
        box.setWindowTitle("升变")
        box.setText("请选择升变棋子")
        queen = box.addButton("后", QMessageBox.ButtonRole.AcceptRole)
        rook = box.addButton("车", QMessageBox.ButtonRole.AcceptRole)
        bishop = box.addButton("象", QMessageBox.ButtonRole.AcceptRole)
        knight = box.addButton("马", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == queen:
            return "q"
        if clicked == rook:
            return "r"
        if clicked == bishop:
            return "b"
        if clicked == knight:
            return "n"
        return None

    def _maybe_schedule_ai(self) -> None:
        if self._engine.phase == ChessPhase.GAME_OVER:
            return
        if self._engine.is_human_turn():
            return
        self._clear_pick()
        self._engine.set_thinking(True)
        if not self._ai_timer.isActive():
            self._ai_timer.start(_AI_DELAY_MS)

    def _start_ai_compute(self) -> None:
        if self._engine.phase == ChessPhase.GAME_OVER:
            return
        if self._engine.is_human_turn():
            self._engine.set_thinking(False)
            return
        if self._ai_busy:
            return
        setup = self._engine.setup
        diff = setup.difficulty if setup else "normal"
        self._ai_busy = True
        self._ai_worker.compute.emit(self._engine.fen(), diff)

    def _apply_ai_move(self, move: object) -> None:
        self._ai_busy = False
        if self._engine.phase == ChessPhase.GAME_OVER:
            return
        self._engine.set_thinking(False)
        if move is None:
            self._engine.sync_game_over()
            self._maybe_schedule_ai()
            return
        uci = move.uci()
        if self._engine.needs_promotion(uci):
            uci = uci[:4] + "q"
        if not self._engine.make_move(uci):
            logger.warning("AI move rejected: %s", uci)
            self._engine.sync_game_over()
        self._maybe_schedule_ai()

    def _on_resign(self) -> None:
        if self._engine.phase == ChessPhase.GAME_OVER:
            return
        self._engine.resign()

    def _on_game_over(self, text: str, human_won: bool) -> None:
        self._ai_timer.stop()
        self._ai_busy = False
        self._clear_pick()
        pet_app = self._get_pet_app()
        if pet_app and hasattr(pet_app, "on_chess_finished"):
            pet_app.on_chess_finished(human_won)

    def closeEvent(self, event) -> None:
        self._ai_timer.stop()
        self._ai_thread.quit()
        self._ai_thread.wait(2000)
        self._end_pet_spectator()
        super().closeEvent(event)
