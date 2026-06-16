"""棋盘视口工厂：固定 2.5D 等距绘制"""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import QWidget

from .game_engine import RichmanEngine
from .painter_viewport import RichmanPainterViewport

logger = logging.getLogger(__name__)


def create_board_viewport(engine: RichmanEngine, parent=None) -> QWidget:
    logger.info("大富翁：使用 2.5D 等距棋盘")
    return RichmanPainterViewport(engine, parent)
