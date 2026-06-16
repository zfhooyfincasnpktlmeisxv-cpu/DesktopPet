"""动作配置加载"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .action_state import ActionState

logger = logging.getLogger(__name__)

_DEFAULTS: Dict[str, Dict[str, Any]] = {
    ActionState.IDLE: {"anim_name": "idle", "fps": 8, "loop": True, "ping_pong": False},
    ActionState.BLINK: {"anim_name": "idle", "overlay_blink": True, "fps": 15, "loop": False},
    ActionState.WALK: {"anim_name": "walk", "fps": 8, "loop": True, "speed_px_per_sec": 50},
    ActionState.EAT: {"anim_name": "eat", "fps": 8, "loop": True, "duration_ms": 5500},
    ActionState.SLEEP: {"anim_name": "sleep", "fps": 4, "loop": True, "ping_pong": True},
    ActionState.SAD: {"anim_name": "sad", "fps": 8, "loop": True},
    ActionState.HAPPY: {"anim_name": "happy", "fps": 8, "loop": False, "duration_ms": 4000},
    ActionState.CLICK: {"anim_name": "click", "fps": 5, "loop": False, "duration_ms": 1100},
    ActionState.GRABBED: {"anim_name": "hover", "fps": 10, "loop": True},
    ActionState.FALL: {"anim_name": "click", "fps": 10, "loop": False, "duration_ms": 900},
}


class ActionConfig:
    def __init__(self, config_path: Optional[str] = None):
        self._path = config_path or self._default_path()
        self._config = self._load()

    @staticmethod
    def _default_path() -> str:
        base = Path(__file__).resolve().parent.parent
        return str(base / "config" / "actions.json")

    def _load(self) -> Dict[str, Any]:
        raw: Dict[str, Any] = {}
        path = Path(self._path)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                logger.warning("动作配置解析失败: %s", e)

        anims: Dict[str, Dict[str, Any]] = {}
        for state, defaults in _DEFAULTS.items():
            merged = dict(defaults)
            merged.update(raw.get("animations", {}).get(state, {}))
            anims[state] = merged

        transitions = raw.get("transitions", {})
        schedule = raw.get("schedule", {})
        return {"animations": anims, "transitions": transitions, "schedule": schedule}

    def get_anim_config(self, state: str) -> Dict[str, Any]:
        return self._config["animations"].get(state, _DEFAULTS.get(state, {}))

    def get_schedule_config(self) -> Dict[str, Any]:
        return self._config.get("schedule", {})

    def can_transition(self, from_state: str, to_state: str) -> bool:
        if to_state == ActionState.IDLE:
            return True
        allowed = self._config.get("transitions", {}).get(from_state, {}).get(
            "allowed_to", [ActionState.IDLE]
        )
        return to_state in allowed
