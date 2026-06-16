"""大富翁音频播放 — PyQt6 QtMultimedia，Kenney CC0 素材"""
from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from .audio_assets import bgm_path, ensure_richman_audio, sfx_path

_POOL_SIZE = 8


class RichmanAudioManager:
    """对局内 BGM 循环 + 多轨 SFX 叠加。"""

    def __init__(self, parent=None):
        self._enabled = True
        self._bgm_vol = 0.38
        self._sfx_vol = 0.72
        self._ready = False

        self._bgm = QMediaPlayer(parent)
        self._bgm_out = QAudioOutput(parent)
        self._bgm.setAudioOutput(self._bgm_out)
        self._bgm.setLoops(QMediaPlayer.Loops.Infinite)

        self._pool: List[Tuple[QMediaPlayer, QAudioOutput]] = []
        self._pool_idx = 0
        for _ in range(_POOL_SIZE):
            player = QMediaPlayer(parent)
            out = QAudioOutput(parent)
            player.setAudioOutput(out)
            self._pool.append((player, out))

        self._sfx_cache: Dict[str, Path] = {}

    def prepare(self) -> None:
        try:
            ensure_richman_audio()
            bgm = bgm_path()
            if bgm:
                self._bgm.setSource(QUrl.fromLocalFile(str(bgm.resolve())))
            for name in (
                "dice_roll",
                "dice_land",
                "buy",
                "build",
                "card",
                "money_in",
                "money_out",
                "jail",
                "win",
                "fanfare",
                "click",
            ):
                p = sfx_path(name)
                if p:
                    self._sfx_cache[name] = p
            self._apply_volumes()
            self._ready = bool(self._sfx_cache or bgm)
        except OSError:
            self._ready = False

    def set_enabled(self, on: bool) -> None:
        self._enabled = on
        if not on:
            self.stop_bgm()

    def start_bgm(self) -> None:
        if not self._enabled or not self._ready:
            return
        if self._bgm.source().isValid() and self._bgm.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
            self._bgm.play()

    def stop_bgm(self) -> None:
        self._bgm.stop()

    def fade_bgm_for_win(self) -> None:
        if self._bgm_out:
            self._bgm_out.setVolume(max(0.12, self._bgm_vol * 0.35))

    def play(self, event: str) -> None:
        if not self._enabled or not self._ready:
            return
        mapping = {
            "dice": "dice_roll",
            "dice_land": "dice_land",
            "buy": "buy",
            "build": "build",
            "card": "card",
            "pass_start": "money_in",
            "rent": "money_out",
            "tax": "money_out",
            "jail": "jail",
            "win": "win",
            "fanfare": "fanfare",
            "click": "click",
        }
        key = mapping.get(event, event)
        path = self._sfx_cache.get(key)
        if not path:
            return
        player, out = self._pool[self._pool_idx % len(self._pool)]
        self._pool_idx += 1
        out.setVolume(self._sfx_vol * random.uniform(0.92, 1.0))
        player.stop()
        player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        player.play()

    def play_dice(self) -> None:
        self.play("dice")

    def _apply_volumes(self) -> None:
        self._bgm_out.setVolume(self._bgm_vol)
        for _, out in self._pool:
            out.setVolume(self._sfx_vol)

    def shutdown(self) -> None:
        self.stop_bgm()
        for player, _ in self._pool:
            player.stop()
