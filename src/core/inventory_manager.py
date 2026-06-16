"""金币与背包：购买、消耗、持久化"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from ..system.data_persistence import DataPersistence
from ..utils.constants import (
    DEFAULT_GOLD,
    FEED_FOOD_ITEM_IDS,
    SHOP_CATALOG,
)

logger = logging.getLogger(__name__)


class InventoryManager(QObject):
    """管理金币与物品背包。"""

    inventory_changed = pyqtSignal()

    def __init__(self, data_persistence: DataPersistence, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._dp = data_persistence
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._dp.get_settings() is None:
            self._dp.load_settings()

    @property
    def gold(self) -> int:
        settings = self._dp.get_settings()
        return int(settings.gold) if settings else DEFAULT_GOLD

    @property
    def inventory(self) -> Dict[str, int]:
        settings = self._dp.get_settings()
        if not settings:
            return {}
        return dict(settings.inventory)

    def get_count(self, item_id: str) -> int:
        return max(0, self.inventory.get(item_id, 0))

    def feed_food_count(self) -> int:
        """背包内可用于喂食的食物总数。"""
        return sum(self.get_count(item_id) for item_id in FEED_FOOD_ITEM_IDS)

    def feed_item_count(self) -> int:
        return self.feed_food_count()

    def has_feed_food(self) -> bool:
        return self.feed_food_count() > 0

    def can_afford(self, item_id: str, quantity: int = 1) -> bool:
        item = SHOP_CATALOG.get(item_id)
        if not item or quantity <= 0:
            return False
        return self.gold >= int(item["price"]) * quantity

    def buy(self, item_id: str, quantity: int = 1) -> bool:
        if item_id not in SHOP_CATALOG or quantity <= 0:
            return False
        price = int(SHOP_CATALOG[item_id]["price"]) * quantity
        if self.gold < price:
            logger.info("金币不足: 需要 %s, 现有 %s", price, self.gold)
            return False

        settings = self._dp.get_settings()
        if settings is None:
            return False

        settings.gold -= price
        inv = dict(settings.inventory)
        inv[item_id] = inv.get(item_id, 0) + quantity
        settings.inventory = inv
        self._dp.save_settings(settings)

        logger.info("购买 %s x%s, 花费 %s 金币, 剩余 %s", item_id, quantity, price, settings.gold)
        self.inventory_changed.emit()
        return True

    def consume(self, item_id: str, quantity: int = 1) -> bool:
        if quantity <= 0:
            return False
        settings = self._dp.get_settings()
        if settings is None:
            return False

        current = settings.inventory.get(item_id, 0)
        if current < quantity:
            return False

        inv = dict(settings.inventory)
        remaining = current - quantity
        if remaining > 0:
            inv[item_id] = remaining
        else:
            inv.pop(item_id, None)
        settings.inventory = inv
        self._dp.save_settings(settings)

        logger.info("消耗 %s x%s, 剩余 %s", item_id, quantity, inv.get(item_id, 0))
        self.inventory_changed.emit()
        return True

    def consume_feed_item(self) -> bool:
        for item_id in FEED_FOOD_ITEM_IDS:
            if self.get_count(item_id) > 0:
                return self.consume(item_id, 1)
        return False

    def catalog(self) -> dict:
        return dict(SHOP_CATALOG)
