"""后台 AI 计算 — 避免 minimax 卡住主线程"""
from __future__ import annotations

import chess
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .ai_player import pick_ai_move


class ChessAiWorker(QObject):
    move_ready = pyqtSignal(object)
    compute = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.compute.connect(self._on_compute)

    @pyqtSlot(str, str)
    def _on_compute(self, fen: str, difficulty: str) -> None:
        board = chess.Board(fen)
        move = pick_ai_move(board, difficulty)
        self.move_ready.emit(move)
