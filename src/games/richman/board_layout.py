"""棋盘格子在世界坐标中的布局（XZ 平面，Y 向上）"""
from __future__ import annotations

import math
from typing import List, Tuple

from .board_data import tile_count

Vec3 = Tuple[float, float, float]

TILE_SPACING = 1.35
BOARD_ELEVATION = 0.0


def _build_path_grid() -> List[Tuple[int, int]]:
    """24 格沿矩形外圈，相邻 index 在网格上必须邻接（含 23→0 回起点）。"""
    path: List[Tuple[int, int]] = []
    for x in range(7):
        path.append((x, 0))
    for z in range(1, 6):
        path.append((6, z))
    path.append((6, 6))
    for x in range(5, -1, -1):
        path.append((x, 6))
    for z in range(5, 0, -1):
        path.append((0, z))
    assert len(path) == tile_count(), f"path len {len(path)} != {tile_count()}"
    return path


_PATH_GRID = _build_path_grid()


def path_grid() -> List[Tuple[int, int]]:
    return list(_PATH_GRID)


def tile_world_position(index: int) -> Vec3:
    gx, gz = _PATH_GRID[index % len(_PATH_GRID)]
    cx = (6 * TILE_SPACING) / 2
    cz = (6 * TILE_SPACING) / 2
    x = gx * TILE_SPACING - cx
    z = gz * TILE_SPACING - cz
    return (x, BOARD_ELEVATION, z)


def tile_yaw(index: int) -> float:
    """地块朝向（弧度），便于以后放建筑。"""
    n = len(_PATH_GRID)
    i = index % n
    prev_i = (i - 1) % n
    next_i = (i + 1) % n
    x0, z0 = _PATH_GRID[prev_i]
    x1, z1 = _PATH_GRID[next_i]
    dx, dz = x1 - x0, z1 - z0
    return math.atan2(dz, dx)


def board_center() -> Vec3:
    return (0.0, 0.0, 0.0)


def board_radius() -> float:
    return 6 * TILE_SPACING * 0.85
