"""Generate exe icon, tray icon, and installer wizard images from the pet model."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / "assets" / "branding"
SOURCE = BRANDING / "pet-source.png"
OUT_DIR = BRANDING / "generated"
ICON_PNG = ROOT / "assets" / "icon.png"
ICON_ICO = ROOT / "assets" / "icon.ico"


def _load_source() -> Image.Image:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Pet source image missing: {SOURCE}")
    img = Image.open(SOURCE).convert("RGBA")
    # 试玩图是黑底，抠成透明方便托盘/图标
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r < 24 and g < 24 and b < 24:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def _fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    im = im.copy()
    im.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    ox = (size[0] - im.width) // 2
    oy = (size[1] - im.height) // 2
    canvas.paste(im, (ox, oy), im)
    return canvas


def _gradient_bg(size: tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    top = (232, 244, 255)
    bottom = (186, 214, 248)
    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=color)
    return img


def write_icons(src: Image.Image) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ICON_PNG.parent.mkdir(parents=True, exist_ok=True)

    tray = _fit(src, (256, 256))
    tray.save(ICON_PNG, format="PNG")

    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    tray.save(ICON_ICO, format="ICO", sizes=sizes)
    print(f"Wrote {ICON_PNG}")
    print(f"Wrote {ICON_ICO}")


def write_installer_art(src: Image.Image) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Inno Setup: WizardImageFile 164x314, WizardSmallImageFile 55x55
    banner = _gradient_bg((164, 314))
    pet = _fit(src, (140, 260))
    banner_rgba = banner.convert("RGBA")
    banner_rgba.paste(pet, ((164 - pet.width) // 2, 314 - pet.height - 18), pet)
    banner_path = OUT_DIR / "wizard-banner.bmp"
    banner_rgba.convert("RGB").save(banner_path, format="BMP")
    print(f"Wrote {banner_path}")

    small = _fit(src, (48, 48))
    small_bg = Image.new("RGB", (55, 55), (232, 244, 255))
    small_bg.paste(small.convert("RGB"), ((55 - small.width) // 2, (55 - small.height) // 2))
    small_path = OUT_DIR / "wizard-small.bmp"
    small_bg.save(small_path, format="BMP")
    print(f"Wrote {small_path}")


def main() -> int:
    src = _load_source()
    write_icons(src)
    write_installer_art(src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
