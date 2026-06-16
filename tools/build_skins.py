#!/usr/bin/env python3
"""从 人物序列图 生成皮肤；日常启动不跑本脚本。"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from skin_pipeline import (
    batch_content_height,
    build_animation_frames,
    build_portrait_idle,
    content_bbox,
    cut_sheet,
    matte_cells,
)

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[0]


def resolve_source_dir() -> Path:
    """优先 DesktopPet/人物序列图，兼容旧版放在仓库根目录的情况。"""
    candidates = (
        PROJECT_ROOT / "人物序列图",
        PROJECT_ROOT.parent / "人物序列图",
    )
    for path in candidates:
        if path.is_dir() and any(path.iterdir()):
            return path
    return candidates[0]


SOURCE_DIR = resolve_source_dir()
SKINS_DIR = PROJECT_ROOT / "skins" / "default"
MANIFEST_PATH = ROOT / "skins_manifest.json"
DEFAULT_TARGET_SIZE = (256, 426)
PORTRAIT_NAME = "人物本体（并非序列图，为本体）.jpg"


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    return {"target_size": list(DEFAULT_TARGET_SIZE), "animations": [], "derived": {}}


def choose_grid(entry: dict) -> dict:
    legacy = entry.get("legacy")
    if entry.get("force_legacy") and legacy:
        print(f"  {entry['name']}: legacy sheet")
        return legacy
    if legacy:
        return legacy
    return {
        "rows": entry["rows"],
        "cols": entry["cols"],
        "max_frames": entry.get("max_frames"),
        "row_offset": entry.get("row_offset", 0),
        "row_count": entry.get("row_count"),
    }


def resolve_source(entry: dict, grid: dict) -> Path:
    for key in (grid.get("source"), entry.get("source")):
        if key:
            path = SOURCE_DIR / key
            if path.exists():
                return path
    raise FileNotFoundError(entry.get("source", "?"))


def load_raw_cells(entry: dict) -> list[Image.Image] | None:
    if entry.get("from"):
        return None
    try:
        grid = choose_grid(entry)
        src = resolve_source(entry, grid)
    except FileNotFoundError:
        return None
    return cut_sheet(
        src,
        grid["rows"],
        grid["cols"],
        row_offset=grid.get("row_offset", 0),
        row_count=grid.get("row_count"),
        max_frames=grid.get("max_frames"),
    )


def save_frames(frames: list[Image.Image], dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for old in dst.glob("*.png"):
        try:
            old.unlink()
        except OSError as e:
            print(f"  warn: cannot remove {old.name} ({e}); stop DesktopPet and rebuild")
    for i, frame in enumerate(frames, start=1):
        frame.save(dst / f"{i:03d}.png")


def dup(frames: list[Image.Image], count: int) -> list[Image.Image]:
    if not frames:
        return frames
    out: list[Image.Image] = []
    while len(out) < count:
        out.extend(frames)
    return out[:count]


def copy_anim(src_dir: Path, name: str, count: int) -> None:
    files = sorted(src_dir.glob("*.png"))
    if not files:
        return
    frames = [Image.open(p).convert("RGBA") for p in files]
    save_frames(dup(frames, count), SKINS_DIR / name)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build DesktopPet skins from 人物序列图")
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ANIM",
        help="只重建指定动画目录（如 walk），不删除其它已生成皮肤",
    )
    args = parser.parse_args()
    only: set[str] | None = set(args.only) if args.only else None

    manifest = load_manifest()
    canvas = tuple(manifest.get("target_size", DEFAULT_TARGET_SIZE))
    policy = manifest.get("build_policy", {})
    default_anchor = bool(policy.get("foot_anchor", True))

    print("DesktopPet skin build (skin_pipeline)")
    if not SOURCE_DIR.exists():
        raise SystemExit(f"missing: {SOURCE_DIR}")

    if only:
        for name in only:
            dst = SKINS_DIR / name
            if dst.exists():
                shutil.rmtree(dst)
        print(f"  partial rebuild: {', '.join(sorted(only))}")
    elif SKINS_DIR.exists():
        for item in SKINS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        SKINS_DIR.mkdir(parents=True, exist_ok=True)
    else:
        SKINS_DIR.mkdir(parents=True, exist_ok=True)

    portrait_name = manifest.get("portrait_source", PORTRAIT_NAME)
    portrait_path = SOURCE_DIR / portrait_name

    pending: list[tuple[dict, list[Image.Image] | None]] = []
    for entry in manifest.get("animations", []):
        name = entry["name"]
        if only and name not in only and entry.get("type") != "portrait":
            if entry.get("from") and entry.get("from") in only:
                pass
            elif entry.get("from"):
                continue
            elif name not in only:
                if not (entry.get("type") == "portrait" and "idle" in only):
                    continue
        if entry.get("type") == "portrait":
            if only and "idle" not in only and name not in (only or set()):
                continue
            pending.append((entry, None))
            continue
        if entry.get("from"):
            continue
        raw = load_raw_cells(entry)
        if raw:
            pending.append((entry, raw))
        else:
            print(f"  skip {entry['name']} (no source)")

    need_idle_height = only is None or "idle" in only or "walk" in (only or set())
    global_h = 0
    if need_idle_height and portrait_path.exists():
        tmp = build_portrait_idle(portrait_path, canvas)
        bbox = content_bbox(tmp)
        if bbox:
            global_h = batch_content_height([tmp.crop(bbox)], canvas)
    elif only and "walk" in only and (SKINS_DIR / "idle" / "001.png").exists():
        idle_img = Image.open(SKINS_DIR / "idle" / "001.png").convert("RGBA")
        bbox = content_bbox(idle_img)
        if bbox:
            global_h = batch_content_height([idle_img.crop(bbox)], canvas)

    for _entry, raw in pending:
        if raw is None:
            continue
        mattes = matte_cells(raw)
        crops = [m.crop(b) for m in mattes if (b := content_bbox(m))]
        if crops and not _entry.get("uniform_scale"):
            global_h = max(global_h, batch_content_height(crops, canvas))

    if global_h:
        print(f"  global character height: {global_h}px")

    idle_frames: list[Image.Image] = []
    for entry, raw in pending:
        name = entry["name"]

        if entry.get("type") == "portrait":
            if not portrait_path.exists():
                print(f"  skip idle: missing {portrait_name}")
                continue
            frame = build_portrait_idle(portrait_path, canvas, target_h=global_h or None)
            frames = [frame]
            save_frames(frames, SKINS_DIR / "idle")
            idle_frames = frames
            print(f"  idle: 1 portrait frame OK")
            continue

        nh = None if entry.get("uniform_scale") else (global_h or None)
        frames = build_animation_frames(
            raw,
            canvas,
            target_h=nh,
            anchor_feet=bool(entry.get("anchor_feet", default_anchor)),
            uniform_scale=bool(entry.get("uniform_scale")),
        )
        save_frames(frames, SKINS_DIR / name)
        print(f"  {name}: {len(frames)} frames OK")

    if only is None:
        for entry in manifest.get("animations", []):
            if entry.get("from") == "hover" and (SKINS_DIR / "hover").exists():
                save_frames(
                    [Image.open(p).convert("RGBA") for p in sorted((SKINS_DIR / "hover").glob("*.png"))],
                    SKINS_DIR / "click",
                )
                print("  click: copied from hover")

        derived = manifest.get("derived", {})
        if idle_frames and (SKINS_DIR / "idle").exists():
            if "grabbed" in derived:
                copy_anim(SKINS_DIR / "idle", "grabbed", derived["grabbed"].get("dup_to", 3))
            hold = derived.get("fall", {}).get("hold_first", 3)
            save_frames(dup([idle_frames[0]], hold), SKINS_DIR / "fall")

    print("DONE")


if __name__ == "__main__":
    main()
