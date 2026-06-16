"""大富翁音频资源 — Kenney CC0 赌场音效 + 游戏 BGM"""
from __future__ import annotations

import json
import shutil
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from src.utils.constants import get_bundle_dir

AUDIO_DIR = get_bundle_dir() / "assets" / "richman" / "audio"
SRC_DIR = AUDIO_DIR / "_src"

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DesktopPet/1.0"

# Kenney Casino Audio (CC0) — 源文件相对 _src/casino/Audio/
_CASINO_MAP: Dict[str, str] = {
    "dice_roll": "die-throw-2.ogg",
    "dice_land": "die-throw-4.ogg",
    "buy": "chips-stack-3.ogg",
    "build": "chip-lay-3.ogg",
    "card": "card-shuffle.ogg",
    "money_in": "chips-collide-2.ogg",
    "money_out": "chips-handle-3.ogg",
    "jail": "card-shove-4.ogg",
    "click": "card-place-2.ogg",
}

# Kenney Music Jingles (CC0)
_JINGLE_WIN = "OGG/jingles_HIT/jingles_HIT14.ogg"
_JINGLE_CARD = "OGG/jingles_PIZZA/jingles_PIZZA05.ogg"

_BGM_REMOTE = (
    "https://opengameart.org/sites/default/files/four_loop.mp3",
    "tempo.mp3",
)
_CASINO_ZIP = (
    "https://opengameart.org/sites/default/files/kenney_casino-audio.zip",
    "casino.zip",
)
_JINGLES_ZIP = (
    "https://opengameart.org/sites/default/files/jingleSounds_Kenney.zip",
    "jingles.zip",
)


def _download(url: str, dest: Path) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp:
            dest.write_bytes(resp.read())
        return dest.stat().st_size > 512
    except OSError:
        return False


def _extract_zip(zip_path: Path, out_dir: Path) -> None:
    import zipfile

    if not zip_path.is_file():
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out_dir)


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.is_file() or src.stat().st_mtime_ns > dst.stat().st_mtime_ns:
        shutil.copy2(src, dst)
    return True


def ensure_richman_audio(force: bool = False) -> Path:
    """确保 sfx/ 与 bgm/ 就绪；缺失时从 Kenney CC0 包拉取。"""
    sfx_dir = AUDIO_DIR / "sfx"
    bgm_dir = AUDIO_DIR / "bgm"
    sfx_dir.mkdir(parents=True, exist_ok=True)
    bgm_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = AUDIO_DIR / "manifest.json"
    if manifest_path.is_file() and not force:
        ready = all((sfx_dir / f"{k}.ogg").is_file() for k in _CASINO_MAP) and (
            sfx_dir / "win.ogg"
        ).is_file()
        if ready and (bgm_dir / "game.mp3").is_file():
            return AUDIO_DIR

    casino_zip = SRC_DIR / _CASINO_ZIP[1]
    jingles_zip = SRC_DIR / _JINGLES_ZIP[1]
    if force or not casino_zip.is_file():
        _download(_CASINO_ZIP[0], casino_zip)
    if force or not jingles_zip.is_file():
        _download(_JINGLES_ZIP[0], jingles_zip)

    _extract_zip(casino_zip, SRC_DIR / "casino")
    _extract_zip(jingles_zip, SRC_DIR / "jingles")

    casino_root = SRC_DIR / "casino" / "Audio"
    for key, fname in _CASINO_MAP.items():
        _copy_if_exists(casino_root / fname, sfx_dir / f"{key}.ogg")

    _copy_if_exists(SRC_DIR / "jingles" / _JINGLE_WIN, sfx_dir / "win.ogg")
    _copy_if_exists(SRC_DIR / "jingles" / _JINGLE_CARD, sfx_dir / "fanfare.ogg")

    bgm_path = bgm_dir / "game.mp3"
    if force or not bgm_path.is_file():
        remote, name = _BGM_REMOTE
        cached = SRC_DIR / name
        if not cached.is_file():
            _download(remote, cached)
        _copy_if_exists(cached, bgm_path)

    manifest = {
        "license": "CC0 — Kenney.nl casino/jingles; BGM from OpenGameArt music-loops",
        "sfx": sorted(p.name for p in sfx_dir.glob("*.ogg")),
        "bgm": sorted(p.name for p in bgm_dir.glob("*")),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return AUDIO_DIR


def sfx_path(name: str) -> Optional[Path]:
    p = AUDIO_DIR / "sfx" / f"{name}.ogg"
    return p if p.is_file() else None


def bgm_path() -> Optional[Path]:
    for ext in (".mp3", ".ogg", ".wav"):
        p = AUDIO_DIR / "bgm" / f"game{ext}"
        if p.is_file():
            return p
    return None
