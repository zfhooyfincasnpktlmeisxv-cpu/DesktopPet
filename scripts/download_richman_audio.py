"""下载大富翁 CC0 音效与 BGM（Kenney + OpenGameArt）"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication  # noqa: E402

from src.games.richman.audio_assets import ensure_richman_audio  # noqa: E402


def main() -> None:
    app = QApplication(sys.argv)
    folder = ensure_richman_audio(force=False)
    sfx = list((folder / "sfx").glob("*.ogg"))
    bgm = list((folder / "bgm").glob("*"))
    print(f"音频目录: {folder}")
    print(f"音效 {len(sfx)} 个 · BGM {len(bgm)} 个")
    del app


if __name__ == "__main__":
    main()
