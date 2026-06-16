"""
好感等级曲线：前期升级快，越往后每级所需经验越多。

累计好感 xp 达到阈值即升级。单级所需经验：
  Lv1→2: BASE
  Lv2→3: BASE + STEP
  Lv3→4: BASE + 2*STEP
  ...
"""
from __future__ import annotations

from ..utils.constants import INTIMACY_LEVEL_BASE, INTIMACY_LEVEL_STEP


def xp_to_reach_level(level: int) -> int:
    """达到指定等级所需的累计好感（Lv.1 = 0）。"""
    if level <= 1:
        return 0
    n = level - 1
    return n * INTIMACY_LEVEL_BASE + INTIMACY_LEVEL_STEP * n * (n - 1) // 2


def xp_for_next_level(current_level: int) -> int:
    """从当前等级升到下一级还需要的经验。"""
    return INTIMACY_LEVEL_BASE + INTIMACY_LEVEL_STEP * max(0, current_level - 1)


def intimacy_level(intimacy: int) -> int:
    """根据累计好感计算当前等级。"""
    intimacy = max(0, intimacy)
    level = 1
    while xp_to_reach_level(level + 1) <= intimacy:
        level += 1
    return level


def intimacy_level_progress(intimacy: int) -> tuple[int, int, int]:
    """
    本级进度。

    Returns:
        (等级, 本级已获得经验, 升到下一级所需经验)
    """
    intimacy = max(0, intimacy)
    level = intimacy_level(intimacy)
    floor = xp_to_reach_level(level)
    need = xp_for_next_level(level)
    have = intimacy - floor
    return level, have, need
