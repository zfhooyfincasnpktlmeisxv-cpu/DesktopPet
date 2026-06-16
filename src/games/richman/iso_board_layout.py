"""经典方形棋盘布局 — 格子平铺四边，文字始终横排"""
from __future__ import annotations

from typing import List, Tuple

from .board_layout import path_grid

GAP_RATIO = 0.06


def tile_grid(index: int) -> Tuple[int, int]:
    grid = path_grid()
    return grid[index % len(grid)]


def _cell_and_origin(cx: float, cy: float, zoom: float, view_w: float, view_h: float) -> Tuple[float, float, float, float]:
    """返回 cell, gap, origin_x, origin_y（左上角）。"""
    margin = 36.0
    avail = min(view_w - margin * 2, view_h - margin * 2) * zoom
    gap = max(2.0, avail * GAP_RATIO / 7.0)
    cell = (avail - gap * 6.0) / 7.0
    board = cell * 7.0 + gap * 6.0
    origin_x = cx - board / 2.0
    origin_y = cy - board / 2.0
    return cell, gap, origin_x, origin_y


def tile_screen_pos(
    index: int, cx: float, cy: float, zoom: float = 1.0, view_w: float = 600.0, view_h: float = 600.0
) -> Tuple[float, float]:
    gx, gz = tile_grid(index)
    cell, gap, ox, oy = _cell_and_origin(cx, cy, zoom, view_w, view_h)
    stride = cell + gap
    sx = ox + gx * stride + cell / 2.0
    sy = oy + (6 - gz) * stride + cell / 2.0
    return sx, sy


def tile_cell_size(cx: float, cy: float, zoom: float, view_w: float, view_h: float) -> Tuple[float, float]:
    cell, gap, _, _ = _cell_and_origin(cx, cy, zoom, view_w, view_h)
    return cell, gap


def tile_paint_order(index: int) -> float:
    """越小越先画（后方），越大越后画（前方）。"""
    gx, gz = tile_grid(index)
    if gz == 0:
        return 100 + gx
    if gx == 6:
        return 200 + gz
    if gz == 6:
        return 300 + (6 - gx)
    if gx == 0:
        return 400 + (6 - gz)
    return 500 + gx + gz


def center_rect(cx: float, cy: float, zoom: float, view_w: float, view_h: float) -> Tuple[float, float, float, float]:
    cell, gap, ox, oy = _cell_and_origin(cx, cy, zoom, view_w, view_h)
    stride = cell + gap
    x = ox + stride
    y = oy + stride
    w = stride * 5 - gap
    h = stride * 5 - gap
    return x, y, w, h
