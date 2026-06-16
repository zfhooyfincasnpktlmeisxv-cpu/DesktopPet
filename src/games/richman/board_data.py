"""大富翁棋盘地块定义（24 格环形，经典大富翁简化版）"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

from .game_balance import INITIAL_MONEY, PASS_START_SALARY, START_BONUS, TAX_AMOUNT


class TileKind(str, Enum):
    START = "start"
    PROPERTY = "property"
    CHANCE = "chance"
    FATE = "fate"
    TAX = "tax"
    JAIL = "jail"
    GO_TO_JAIL = "go_to_jail"
    PARKING = "parking"


@dataclass(frozen=True)
class TileDef:
    index: int
    name: str
    kind: TileKind
    price: int = 0
    rent: int = 0
    color: Tuple[int, int, int] = (80, 100, 130)
    group: str = ""


# 颜色组：蓝 / 青 / 粉 / 橙 / 红 / 紫
# 与 board_layout.path_grid 顺序对齐（右上角 index 12 = 台北）
_OLD_TILES: List[TileDef] = [
    TileDef(0, "起点", TileKind.START, color=(72, 220, 160)),
    TileDef(1, "天津", TileKind.PROPERTY, 80, 35, (0, 160, 220), "蓝"),
    TileDef(2, "机会", TileKind.CHANCE, color=(255, 198, 120)),
    TileDef(3, "重庆", TileKind.PROPERTY, 80, 35, (0, 160, 220), "蓝"),
    TileDef(4, "所得税", TileKind.TAX, color=(255, 120, 100)),
    TileDef(5, "上海", TileKind.PROPERTY, 280, 140, (255, 150, 70), "橙"),
    TileDef(6, "南京", TileKind.PROPERTY, 140, 50, (0, 200, 255), "青"),
    TileDef(7, "机会", TileKind.CHANCE, color=(255, 198, 120)),
    TileDef(8, "杭州", TileKind.PROPERTY, 140, 50, (0, 200, 255), "青"),
    TileDef(9, "监狱", TileKind.JAIL, color=(140, 150, 170)),
    TileDef(10, "苏州", TileKind.PROPERTY, 160, 60, (255, 183, 197), "粉"),
    TileDef(11, "武汉", TileKind.PROPERTY, 160, 60, (255, 183, 197), "粉"),
    TileDef(12, "免费停车", TileKind.PARKING, color=(120, 140, 180)),
    TileDef(13, "成都", TileKind.PROPERTY, 220, 85, (255, 150, 70), "橙"),
    TileDef(14, "机会", TileKind.CHANCE, color=(255, 198, 120)),
    TileDef(15, "西安", TileKind.PROPERTY, 220, 85, (255, 150, 70), "橙"),
    TileDef(16, "广州", TileKind.PROPERTY, 280, 140, (255, 100, 120), "红"),
    TileDef(17, "深圳", TileKind.PROPERTY, 300, 155, (255, 100, 120), "红"),
    TileDef(18, "进监狱", TileKind.GO_TO_JAIL, color=(180, 60, 80)),
    TileDef(19, "北京", TileKind.PROPERTY, 360, 190, (180, 140, 255), "紫"),
    TileDef(20, "奢侈税", TileKind.TAX, color=(255, 120, 100)),
    TileDef(21, "香港", TileKind.PROPERTY, 380, 210, (180, 140, 255), "紫"),
    TileDef(22, "命运", TileKind.FATE, color=(255, 160, 200)),
    TileDef(23, "台北", TileKind.PROPERTY, 400, 225, (180, 140, 255), "紫"),
]

# 路径修正后：在 (6,6) 插入顶角，台北置于 index 12，其余顶/左侧顺延一格
_PATH_TILE_PERM = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
    23, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22,
]

_TILES: List[TileDef] = [
    TileDef(
        new_i,
        _OLD_TILES[old_i].name,
        _OLD_TILES[old_i].kind,
        _OLD_TILES[old_i].price,
        _OLD_TILES[old_i].rent,
        _OLD_TILES[old_i].color,
        _OLD_TILES[old_i].group,
    )
    for new_i, old_i in enumerate(_PATH_TILE_PERM)
]


def tile_count() -> int:
    return len(_TILES)


def get_tile(index: int) -> TileDef:
    return _TILES[index % len(_TILES)]


def all_tiles() -> List[TileDef]:
    return list(_TILES)


MAX_DICE = 6
