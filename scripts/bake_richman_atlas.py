"""烘焙大富翁 H5 级贴图图集"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.games.richman.texture_baker import bake_all_assets  # noqa: E402


def main() -> None:
    path = bake_all_assets(force=True)
    print(f"已烘焙贴图图集: {path}")
    print(f"中央展台: {path.parent / 'center_board.png'}")


if __name__ == "__main__":
    main()
