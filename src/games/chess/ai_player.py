"""国际象棋电脑 — 随机 / 浅层搜索（限制节点，避免卡 UI）"""
from __future__ import annotations

import random
from typing import Optional

import chess

_PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000,
}

_MAX_NODES = 6000


def _evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -30000 if board.turn == chess.WHITE else 30000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0
    score = 0
    for piece in board.piece_map().values():
        v = _PIECE_VALUE.get(piece.piece_type, 0)
        score += v if piece.color == chess.WHITE else -v
    return score


_nodes = 0


def _minimax(board: chess.Board, depth: int, alpha: int, beta: int) -> int:
    global _nodes
    if _nodes >= _MAX_NODES or depth == 0 or board.is_game_over():
        return _evaluate(board)
    _nodes += 1
    if board.turn == chess.WHITE:
        best = -10**9
        for move in board.legal_moves:
            board.push(move)
            best = max(best, _minimax(board, depth - 1, alpha, beta))
            board.pop()
            alpha = max(alpha, best)
            if beta <= alpha or _nodes >= _MAX_NODES:
                break
        return best
    best = 10**9
    for move in board.legal_moves:
        board.push(move)
        best = min(best, _minimax(board, depth - 1, alpha, beta))
        board.pop()
        beta = min(beta, best)
        if beta <= alpha or _nodes >= _MAX_NODES:
            break
    return best


def pick_ai_move(board: chess.Board, difficulty: str = "normal") -> Optional[chess.Move]:
    global _nodes
    moves = list(board.legal_moves)
    if not moves:
        return None
    if difficulty == "easy":
        return random.choice(moves)

    depth = 1 if difficulty == "normal" else 2
    _nodes = 0
    best_move: Optional[chess.Move] = None
    if board.turn == chess.WHITE:
        best_score = -10**9
        for move in moves:
            board.push(move)
            score = _minimax(board, depth - 1, -10**9, 10**9)
            board.pop()
            if score > best_score:
                best_score = score
                best_move = move
    else:
        best_score = 10**9
        for move in moves:
            board.push(move)
            score = _minimax(board, depth - 1, -10**9, 10**9)
            board.pop()
            if score < best_score:
                best_score = score
                best_move = move
    return best_move or random.choice(moves)
