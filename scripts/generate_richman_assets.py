"""生成大富翁贴图资源（委托 M3 烘焙器）"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.games.richman.texture_baker import bake_all_assets  # noqa: E402


def main() -> None:
    path = bake_all_assets(force=True)
    print(f"已烘焙 H5 级贴图: {path}")


if __name__ == "__main__":
    main()
