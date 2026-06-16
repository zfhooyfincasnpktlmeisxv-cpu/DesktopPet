"""Lightweight JSON-based UI translations."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.constants import get_locales_dir

logger = logging.getLogger(__name__)

_LOCALES_DIR = get_locales_dir()
_FALLBACK = "en"

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "English",
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
    "ja": "日本語",
    "ko": "한국어",
    "es": "Español",
    "fr": "Français",
    "de": "Deutsch",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "ar": "العربية",
    "hi": "हिन्दी",
    "th": "ไทย",
    "vi": "Tiếng Việt",
    "tr": "Türkçe",
    "pl": "Polski",
    "nl": "Nederlands",
}


class Translator:
    def __init__(self) -> None:
        self._language = _FALLBACK
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._strings: Dict[str, Any] = {}
        self.set_language(_FALLBACK)

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, code: str) -> None:
        if code not in SUPPORTED_LANGUAGES:
            logger.warning("Unsupported language %s, falling back to %s", code, _FALLBACK)
            code = _FALLBACK
        if code != self._language:
            self._cache.pop(code, None)
        self._language = code
        self._strings = self._load_merged(code)
        logger.info("UI language set to %s", code)

    def t(self, key: str, default: Optional[str] = None, **kwargs: Any) -> str:
        text = self._lookup(self._strings, key)
        if text is None and self._language != _FALLBACK:
            text = self._lookup(self._load_merged(_FALLBACK), key)
        if text is None:
            text = default if default is not None else key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError):
                return text
        return text

    @staticmethod
    def _lookup(strings: Dict[str, Any], key: str) -> Optional[str]:
        node: Any = strings
        for part in key.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        if node is None:
            return None
        if isinstance(node, (dict, list)):
            return None
        return str(node)

    def text_pool(self, name: str) -> List[str]:
        pools = self._strings.get("text_pools", {})
        if isinstance(pools, dict) and name in pools:
            items = pools[name]
            if isinstance(items, list):
                return [str(x) for x in items]
        fb = self._load_merged(_FALLBACK).get("text_pools", {})
        if isinstance(fb, dict) and name in fb:
            return [str(x) for x in fb[name]]
        return [self.t("text_pools.fallback", default="…")]

    def game_meta(self, game_id: str) -> Dict[str, str]:
        games = self._strings.get("games", {})
        if isinstance(games, dict) and game_id in games:
            meta = games[game_id]
            if isinstance(meta, dict):
                return {
                    "name": str(meta.get("name", game_id)),
                    "description": str(meta.get("description", "")),
                }
        return {"name": game_id, "description": ""}

    def shop_item(self, item_id: str) -> Dict[str, str]:
        items = self._strings.get("shop_items", {})
        if isinstance(items, dict) and item_id in items:
            meta = items[item_id]
            if isinstance(meta, dict):
                return {
                    "name": str(meta.get("name", item_id)),
                    "description": str(meta.get("description", "")),
                }
        fb = self._load_merged(_FALLBACK).get("shop_items", {})
        if isinstance(fb, dict) and item_id in fb:
            meta = fb[item_id]
            return {
                "name": str(meta.get("name", item_id)),
                "description": str(meta.get("description", "")),
            }
        return {"name": item_id, "description": ""}

    def game_feedback_line(self, game_id: str, event: str) -> str:
        import random
        from ..utils.constants import GAME_FEEDBACK

        fb = self._strings.get("game_feedback", {})
        if isinstance(fb, dict) and game_id in fb:
            game_pool = fb[game_id]
            if isinstance(game_pool, dict):
                pool = game_pool.get(event) or game_pool.get("start")
                if isinstance(pool, list) and pool:
                    return random.choice([str(x) for x in pool])
        if self._language != _FALLBACK:
            fb_en = self._load_merged(_FALLBACK).get("game_feedback", {})
            if isinstance(fb_en, dict) and game_id in fb_en:
                game_pool = fb_en[game_id]
                if isinstance(game_pool, dict):
                    pool = game_pool.get(event) or game_pool.get("start")
                    if isinstance(pool, list) and pool:
                        return random.choice([str(x) for x in pool])
        pools = GAME_FEEDBACK.get(game_id, {})
        pool = pools.get(event, pools.get("start", ["Keep going!"]))
        return random.choice(pool)

    def _load_merged(self, code: str) -> Dict[str, Any]:
        if code in self._cache:
            return self._cache[code]
        base = self._load_file(_FALLBACK)
        if code == _FALLBACK:
            merged = base
        else:
            merged = _deep_merge(base, self._load_file(code))
        self._cache[code] = merged
        return merged

    def _load_file(self, code: str) -> Dict[str, Any]:
        path = _LOCALES_DIR / f"{code}.json"
        if not path.exists():
            logger.error("Locale file missing: %s", path)
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load locale %s: %s", path, exc)
            return {}


_translator = Translator()


def init_language(code: str) -> None:
    _translator.set_language(code or _FALLBACK)


def get_language() -> str:
    return _translator.language


def set_language(code: str) -> None:
    _translator.set_language(code)


def t(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    return _translator.t(key, default=default, **kwargs)


def text_pool(name: str) -> List[str]:
    return _translator.text_pool(name)


def game_meta(game_id: str) -> Dict[str, str]:
    return _translator.game_meta(game_id)


def shop_item(item_id: str) -> Dict[str, str]:
    return _translator.shop_item(item_id)


def game_feedback_line(game_id: str, event: str) -> str:
    return _translator.game_feedback_line(game_id, event)


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out
