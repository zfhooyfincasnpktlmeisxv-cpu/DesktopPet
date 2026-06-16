"""国际象棋棋盘视口 — 经典绿格 + Unicode 棋子（无版权素材）"""
from __future__ import annotations

from typing import List, Optional, Set

import chess
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from .game_engine import ChessEngine

_LIGHT = QColor(240, 217, 181)
_DARK = QColor(181, 136, 99)
_SELECT = QColor(106, 169, 255, 100)
_LAST = QColor(255, 220, 80, 100)
_HINT = QColor(60, 120, 200, 200)
_CHECK = QColor(255, 80, 80, 120)

_UNICODE = {
    (chess.WHITE, chess.KING): "♔",
    (chess.WHITE, chess.QUEEN): "♕",
    (chess.WHITE, chess.ROOK): "♖",
    (chess.WHITE, chess.BISHOP): "♗",
    (chess.WHITE, chess.KNIGHT): "♘",
    (chess.WHITE, chess.PAWN): "♙",
    (chess.BLACK, chess.KING): "♚",
    (chess.BLACK, chess.QUEEN): "♛",
    (chess.BLACK, chess.ROOK): "♜",
    (chess.BLACK, chess.BISHOP): "♝",
    (chess.BLACK, chess.KNIGHT): "♞",
    (chess.BLACK, chess.PAWN): "♟",
}


class ChessBoardViewport(QWidget):
    square_clicked = pyqtSignal(int)

    def __init__(self, engine: ChessEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._selected: Optional[int] = None
        self._hints: Set[int] = set()
        self._last_from: Optional[int] = None
        self._last_to: Optional[int] = None
        self._flip = False
        self._engine.state_changed.connect(self.update)
        self._engine.move_made.connect(self._on_move)
        self.setMinimumSize(480, 480)
        self.setMouseTracking(True)

    def set_flipped(self, flipped: bool) -> None:
        self._flip = flipped
        self.update()

    def clear_selection(self) -> None:
        self._selected = None
        self._hints.clear()
        self.update()

    def _on_move(self, uci: str, _san: str) -> None:
        if len(uci) >= 4:
            self._last_from = chess.parse_square(uci[0:2])
            self._last_to = chess.parse_square(uci[2:4])
        self._selected = None
        self._hints.clear()
        self.update()

    def _square_at(self, px: int, py: int) -> Optional[int]:
        margin = 28
        size = min(self.width(), self.height()) - margin * 2
        if size <= 0:
            return None
        cell = size / 8
        ox = (self.width() - size) / 2
        oy = (self.height() - size) / 2
        col = int((px - ox) / cell)
        row = int((py - oy) / cell)
        if col < 0 or col > 7 or row < 0 or row > 7:
            return None
        if self._flip:
            file_i, rank_i = col, row
        else:
            file_i, rank_i = col, 7 - row
        return chess.square(file_i, rank_i)

    def _geom(self) -> tuple[float, float, float]:
        margin = 28
        size = min(self.width(), self.height()) - margin * 2
        cell = size / 8
        ox = (self.width() - size) / 2
        oy = (self.height() - size) / 2
        return ox, oy, cell

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        sq = self._square_at(int(event.position().x()), int(event.position().y()))
        if sq is None:
            return
        self.square_clicked.emit(sq)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(22, 28, 42))

        board = self._engine.board
        ox, oy, cell = self._geom()
        icell = max(1, int(cell))

        king_sq = None
        if board.is_check():
            king_sq = board.king(board.turn)

        for rank in range(8):
            for file_i in range(8):
                sq = chess.square(file_i, rank)
                if self._flip:
                    col, row = file_i, rank
                else:
                    col, row = file_i, 7 - rank
                x = int(ox + col * cell)
                y = int(oy + row * cell)
                light = (file_i + rank) % 2 == 1
                p.fillRect(x, y, icell, icell, _LIGHT if light else _DARK)

                if sq == self._last_from or sq == self._last_to:
                    p.fillRect(x, y, icell, icell, _LAST)
                if sq == self._selected:
                    p.fillRect(x, y, icell, icell, _SELECT)
                if sq in self._hints:
                    p.save()
                    p.setBrush(_HINT)
                    p.setPen(Qt.PenStyle.NoPen)
                    r = cell * 0.16
                    cx = int(x + cell / 2)
                    cy = int(y + cell / 2)
                    ir = max(2, int(r))
                    p.drawEllipse(cx - ir, cy - ir, ir * 2, ir * 2)
                    p.restore()
                if sq == king_sq:
                    p.fillRect(x, y, icell, icell, _CHECK)

        labels = "abcdefgh"
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(180, 190, 210))
        for i in range(8):
            file_label = labels[i]
            rank_label = str(8 - i if not self._flip else i + 1)
            p.drawText(int(ox + i * cell + 4), int(oy - 6), file_label)
            p.drawText(int(ox - 18), int(oy + i * cell + cell - 6), rank_label)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setFont(QFont("Segoe UI Symbol", int(cell * 0.72)))
        for sq, piece in board.piece_map().items():
            file_i = chess.square_file(sq)
            rank = chess.square_rank(sq)
            if self._flip:
                col, row = file_i, rank
            else:
                col, row = file_i, 7 - rank
            x = int(ox + col * cell)
            y = int(oy + row * cell)
            sym = _UNICODE.get((piece.color, piece.piece_type), "?")
            p.setPen(QColor(20, 20, 20))
            p.drawText(x, y, icell, icell, Qt.AlignmentFlag.AlignCenter, sym)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(60, 72, 96), 2))
        p.drawRect(int(ox), int(oy), icell * 8, icell * 8)

    def select_square(self, sq: int, hints: List[int]) -> None:
        self._selected = sq
        self._hints = set(hints)
        self.update()
