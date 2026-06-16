"""小游戏注册表"""
from __future__ import annotations

from typing import Dict, Type

from ..utils.constants import (
    GAME_CATALOG,
    GAME_CATCH_ID,
    GAME_DODGE_ID,
    GAME_MEMORY_ID,
    GAME_SNAKE_ID,
)
from .base_game import BaseGameWidget
from .catch_game import CatchGameWidget
from .dodge_game import DodgeGameWidget
from .memory_game import MemoryGameWidget
from .snake_game import SnakeGameWidget

_GAME_WIDGETS: Dict[str, Type[BaseGameWidget]] = {
    GAME_SNAKE_ID: SnakeGameWidget,
    GAME_CATCH_ID: CatchGameWidget,
    GAME_DODGE_ID: DodgeGameWidget,
    GAME_MEMORY_ID: MemoryGameWidget,
}


def list_games() -> dict:
    return dict(GAME_CATALOG)


def create_game_widget(game_id: str, parent=None) -> BaseGameWidget | None:
    cls = _GAME_WIDGETS.get(game_id)
    if cls is None:
        return None
    return cls(parent=parent)
