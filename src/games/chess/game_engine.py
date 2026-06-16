"""国际象棋规则引擎 — python-chess"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple

import chess
from PyQt6.QtCore import QObject, pyqtSignal

from .player_setup import ChessSetup


class ChessPhase(str, Enum):
    WAIT_MOVE = "wait_move"
    THINKING = "thinking"
    GAME_OVER = "game_over"


class ChessEngine(QObject):
    state_changed = pyqtSignal()
    log_message = pyqtSignal(str)
    move_made = pyqtSignal(str, str)
    game_over = pyqtSignal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._board = chess.Board()
        self._setup: Optional[ChessSetup] = None
        self._phase = ChessPhase.WAIT_MOVE
        self._winner_side: Optional[bool] = None
        self._result_text = ""
        self._move_count = 0

    @property
    def board(self) -> chess.Board:
        return self._board

    @property
    def phase(self) -> ChessPhase:
        return self._phase

    @property
    def setup(self) -> Optional[ChessSetup]:
        return self._setup

    def new_game(self, setup: ChessSetup) -> None:
        self._setup = setup
        self._board = chess.Board()
        self._phase = ChessPhase.WAIT_MOVE
        self._winner_side = None
        self._result_text = ""
        self._move_count = 0
        self.log_message.emit(
            f"新对局 · {setup.white_name}（白） vs {setup.black_name}（黑）"
        )
        self._emit_all()

    def side_name(self, is_white: bool) -> str:
        if not self._setup:
            return "白方" if is_white else "黑方"
        return self._setup.white_name if is_white else self._setup.black_name

    def is_human_side(self, is_white: bool) -> bool:
        if not self._setup:
            return True
        return self._setup.white_is_human if is_white else self._setup.black_is_human

    def is_human_turn(self) -> bool:
        return self.is_human_side(self._board.turn == chess.WHITE)

    def current_player_name(self) -> str:
        return self.side_name(self._board.turn == chess.WHITE)

    def legal_moves_from(self, square: int) -> List[chess.Move]:
        if self._phase != ChessPhase.WAIT_MOVE:
            return []
        return [m for m in self._board.legal_moves if m.from_square == square]

    def legal_uci_targets(self, square: int) -> List[str]:
        return [m.uci() for m in self.legal_moves_from(square)]

    def needs_promotion(self, uci: str) -> bool:
        move = chess.Move.from_uci(uci)
        piece = self._board.piece_at(move.from_square)
        if not piece or piece.piece_type != chess.PAWN:
            return False
        rank = chess.square_rank(move.to_square)
        return rank == 0 or rank == 7

    def make_move(self, uci: str, promotion: str = "") -> bool:
        if self._phase != ChessPhase.WAIT_MOVE:
            return False
        promo = promotion.lower() if promotion else None
        if len(uci) == 4 and promo and self.needs_promotion(uci):
            uci = uci + promo
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            return False
        if move not in self._board.legal_moves:
            return False

        mover = self.current_player_name()
        san = self._board.san(move)
        self._board.push(move)
        self._move_count += 1
        self.move_made.emit(move.uci(), san)
        self.log_message.emit(f"{mover}：{san}")

        if self._board.is_game_over():
            self._finish_game()
        else:
            self._phase = ChessPhase.WAIT_MOVE
            self.state_changed.emit()
        return True

    def sync_game_over(self) -> None:
        """无合法着法或终局状态时收尾。"""
        if self._board.is_game_over():
            self._finish_game()

    def _finish_game(self) -> None:
        self._phase = ChessPhase.GAME_OVER
        human_won = False
        if self._board.is_checkmate():
            winner_white = not self._board.turn
            self._winner_side = winner_white
            winner = self.side_name(winner_white)
            loser = self.side_name(not winner_white)
            self._result_text = f"{winner} 将死获胜！"
            human_won = self.is_human_side(winner_white)
            self.log_message.emit(self._result_text)
        elif self._board.is_stalemate():
            self._result_text = "逼和，平局"
            self.log_message.emit(self._result_text)
        elif self._board.is_insufficient_material():
            self._result_text = "子力不足，平局"
            self.log_message.emit(self._result_text)
        elif self._board.can_claim_threefold_repetition():
            self._result_text = "三次重复，平局"
            self.log_message.emit(self._result_text)
        else:
            self._result_text = "对局结束"
            self.log_message.emit(self._result_text)
        self.game_over.emit(self._result_text, human_won)
        self._emit_all()

    def resign(self) -> None:
        if self._phase == ChessPhase.GAME_OVER:
            return
        resigner_white = self._board.turn == chess.WHITE
        winner_white = not resigner_white
        self._winner_side = winner_white
        self._phase = ChessPhase.GAME_OVER
        self._result_text = f"{self.side_name(resigner_white)} 认输"
        self.log_message.emit(self._result_text)
        human_won = self.is_human_side(winner_white)
        self.game_over.emit(self._result_text, human_won)
        self._emit_all()

    def set_thinking(self, on: bool) -> None:
        if self._phase == ChessPhase.GAME_OVER:
            return
        self._phase = ChessPhase.THINKING if on else ChessPhase.WAIT_MOVE
        self.state_changed.emit()

    @property
    def result_text(self) -> str:
        return self._result_text

    def fen(self) -> str:
        return self._board.fen()

    def _emit_all(self) -> None:
        self.state_changed.emit()
