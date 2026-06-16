"""下载大富翁城市地标照片（Pexels 免费可商用）"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.games.richman.city_images import ensure_city_images  # noqa: E402


def main() -> None:
    app = QApplication(sys.argv)
    folder = ensure_city_images(force=False)
    manifest = folder / "manifest.json"
    jpgs = [p for p in folder.glob("*.jpg") if p.stat().st_size > 2048]
    print(f"城市图片目录: {folder}")
    print(f"有效图片 {len(jpgs)} 张（清单: {manifest.name}）")
    del app


if __name__ == "__main__":
    main()
