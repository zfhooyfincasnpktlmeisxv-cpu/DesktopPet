"""下载 CC0 大富翁相关素材（Kenney Board Game Bits 等）"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "richman" / "textures"

# Kenney Board Game Kit (CC0) — 官方 CDN 直链
KENNEY_BOARDGAME_ZIP = (
    "https://kenney.nl/media/pages/assets/board-game-kit/"
    "e8381caa48-1677589475/kenney_board-game-kit.zip"
)


def _extract_pngs(data: bytes, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            if not name.lower().endswith(".png"):
                continue
            base = Path(name).name
            if base.lower() in {"dice.png", "pawn.png", "tile.png", "board.png"}:
                continue
            target = dest / base
            target.write_bytes(zf.read(name))
            count += 1
    return count


def main() -> None:
    print("正在下载 Kenney Board Game Kit (CC0)…")
    try:
        with urlopen(KENNEY_BOARDGAME_ZIP, timeout=60) as resp:
            data = resp.read()
    except Exception as exc:
        print(f"下载失败: {exc}")
        print("请手动运行: python scripts/generate_richman_assets.py")
        return

    n = _extract_pngs(data, OUT)
    print(f"已解压 {n} 张 PNG 到 {OUT}")

    # 确保占位图存在
    import subprocess
    import sys

    subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_richman_assets.py")], check=False)
    print("完成。来源: Kenney.nl — CC0")


if __name__ == "__main__":
    main()
