"""地产租金、垄断、盖房规则（经典大富翁 · 快节奏）"""
from __future__ import annotations

from typing import Dict, List

from .board_data import TileDef, TileKind, get_tile, all_tiles
from .game_balance import MAX_BUILD_LEVEL, RENT_MULTIPLIERS


def tiles_in_group(group: str) -> List[int]:
    if not group:
        return []
    return [t.index for t in all_tiles() if t.group == group]


def owns_full_group(properties: Dict[int, object], owner_id: int, group: str) -> bool:
    indices = tiles_in_group(group)
    if not indices:
        return False
    for idx in indices:
        prop = properties[idx]
        if getattr(prop, "owner_id", None) != owner_id:
            return False
    return True


def compute_rent(tile: TileDef, prop, properties: Dict[int, object]) -> int:
    if tile.kind != TileKind.PROPERTY:
        return 0
    level = min(MAX_BUILD_LEVEL, max(0, prop.level))
    base = tile.rent * RENT_MULTIPLIERS[level]
    if level == 0 and owns_full_group(properties, prop.owner_id, tile.group):
        return tile.rent * 2
    return base


def house_cost(tile: TileDef) -> int:
    return max(80, tile.price // 2)


def can_build_on(
    tile_index: int,
    player_id: int,
    money: int,
    properties: Dict[int, object],
) -> bool:
    tile = get_tile(tile_index)
    if tile.kind != TileKind.PROPERTY or not tile.group:
        return False
    prop = properties[tile_index]
    if prop.owner_id != player_id:
        return False
    if prop.level >= MAX_BUILD_LEVEL:
        return False
    if not owns_full_group(properties, player_id, tile.group):
        return False
    if money < house_cost(tile):
        return False
    group_indices = tiles_in_group(tile.group)
    levels = [properties[i].level for i in group_indices]
    min_level = min(levels)
    if prop.level > min_level:
        return False
    return True


def build_house(tile_index: int, player_id: int, properties: Dict[int, object]) -> int:
    """盖一级，返回花费。"""
    tile = get_tile(tile_index)
    cost = house_cost(tile)
    prop = properties[tile_index]
    if prop.owner_id != player_id:
        return 0
    prop.level += 1
    return cost
