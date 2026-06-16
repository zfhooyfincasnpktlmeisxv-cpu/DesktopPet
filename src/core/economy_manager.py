"""小游戏金币奖励与每日上限"""
from __future__ import annotations

import logging
from datetime import date
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal

from ..system.data_persistence import DataPersistence
from ..utils.constants import DAILY_GOLD_CAP, GAME_CATALOG, GAME_CHESS_ID, GAME_RICHMAN_ID, CHESS_FEATURE, RICHMAN_FEATURE

logger = logging.getLogger(__name__)


def _reward_meta(game_id: str) -> Optional[dict]:
    if game_id == GAME_RICHMAN_ID:
        return RICHMAN_FEATURE
    if game_id == GAME_CHESS_ID:
        return CHESS_FEATURE
    return GAME_CATALOG.get(game_id)


class EconomyManager(QObject):
    """管理打工小游戏金币产出与每日上限。"""

    gold_changed = pyqtSignal()

    def __init__(
        self,
        data_persistence: DataPersistence,
        inventory_mgr: Optional[object] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._dp = data_persistence
        self._inventory = inventory_mgr
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._dp.get_settings() is None:
            self._dp.load_settings()

    def _today(self) -> str:
        return date.today().isoformat()

    def _ensure_daily_reset(self) -> None:
        settings = self._dp.get_settings()
        if settings is None:
            return
        if settings.daily_reset_date != self._today():
            settings.daily_gold_earned = 0
            settings.daily_reset_date = self._today()
            self._dp.save_settings(settings)
            logger.info("每日打工金币计数已重置")

    def daily_earned(self) -> int:
        self._ensure_daily_reset()
        settings = self._dp.get_settings()
        return int(settings.daily_gold_earned) if settings else 0

    def daily_remaining(self) -> int:
        return max(0, DAILY_GOLD_CAP - self.daily_earned())

    def calc_game_reward(self, game_id: str, score: int) -> int:
        """根据得分计算本局可发放金币（受每日剩余额度限制）。"""
        meta = _reward_meta(game_id)
        if not meta or score <= 0:
            return 0
        per = int(meta.get("reward_per_food", meta.get("reward_win_score", 1)))
        raw = int(meta["reward_base"]) + score * per
        return min(raw, self.daily_remaining())

    def award_game_reward(self, game_id: str, score: int) -> Tuple[int, bool]:
        """
        发放小游戏奖励。

        Returns:
            (实际发放金币, 是否已达今日上限)
        """
        self._ensure_daily_reset()
        settings = self._dp.get_settings()
        if settings is None:
            return 0, False

        award = self.calc_game_reward(game_id, score)
        hit_cap = self.daily_remaining() <= 0

        if award > 0:
            settings.gold += award
            settings.daily_gold_earned += award
            stats = dict(settings.game_stats)
            game_stat = dict(stats.get(game_id, {}))
            game_stat["plays"] = int(game_stat.get("plays", 0)) + 1
            game_stat["best_score"] = max(int(game_stat.get("best_score", 0)), score)
            game_stat["total_score"] = int(game_stat.get("total_score", 0)) + score
            if game_id in (GAME_RICHMAN_ID, GAME_CHESS_ID):
                game_stat["wins"] = int(game_stat.get("wins", 0)) + 1
            stats[game_id] = game_stat
            settings.game_stats = stats
            self._dp.save_settings(settings)
            logger.info(
                "小游戏奖励 %s: score=%s gold=%s daily=%s/%s",
                game_id,
                score,
                award,
                settings.daily_gold_earned,
                DAILY_GOLD_CAP,
            )
            if self._inventory is not None:
                self._inventory.inventory_changed.emit()
            self.gold_changed.emit()

        hit_cap = settings.daily_gold_earned >= DAILY_GOLD_CAP
        return award, hit_cap

    def get_game_stats(self, game_id: str) -> Dict[str, int]:
        settings = self._dp.get_settings()
        if not settings:
            return {}
        return dict(settings.game_stats.get(game_id, {}))
