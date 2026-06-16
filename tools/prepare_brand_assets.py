"""Generate exe icon, tray icon, and installer wizard images from the pet model."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
BRANDING = ROOT / "assets" / "branding"
SOURCE = BRANDING / "pet-source.png"
OUT_DIR = BRANDING / "generated"
ICON_PNG = ROOT / "assets" / "icon.png"
ICON_ICO = ROOT / "assets" / "icon.ico"

# Inno Setup modern wizard header background
_WIZARD_HEADER_BG = (255, 255, 255)


def _key_black_to_alpha(img: Image.Image) -> Image.Image:
    """Remove black backdrop from试玩图 and soften edges to avoid halos."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            brightness = max(r, g, b)
            # Hard key near-black pixels
            if brightness < 28:
                px[x, y] = (r, g, b, 0)
                continue
            # Soft feather on dark fringe (typical JPG/PNG matte edge)
            if brightness < 55:
                t = (brightness - 28) / 27.0
                px[x, y] = (r, g, b, int(a * t))
    return img.filter(ImageFilter.GaussianBlur(radius=0.6))


def _load_source() -> Image.Image:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Pet source image missing: {SOURCE}")
    return _key_black_to_alpha(Image.open(SOURCE))


def _fit(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    im = im.copy()
    im.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    ox = (size[0] - im.width) // 2
    oy = (size[1] - im.height) // 2
    canvas.paste(im, (ox, oy), im)
    return canvas


def _composite_on_bg(rgba: Image.Image, canvas_size: tuple[int, int], bg: tuple[int, int, int]) -> Image.Image:
    """Alpha-composite pet onto a solid background (BMP has no transparency)."""
    canvas = Image.new("RGBA", canvas_size, bg + (255,))
    pet = _fit(rgba, (canvas_size[0] - 6, canvas_size[1] - 6))
    ox = (canvas_size[0] - pet.width) // 2
    oy = (canvas_size[1] - pet.height) // 2
    canvas.paste(pet, (ox, oy), pet)
    return canvas.convert("RGB")


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
    banner = _gradient_bg((164, 314)).convert("RGBA")
    pet = _fit(src, (136, 256))
    banner.paste(pet, ((164 - pet.width) // 2, 314 - pet.height - 20), pet)
    banner_path = OUT_DIR / "wizard-banner.bmp"
    banner.convert("RGB").save(banner_path, format="BMP")
    print(f"Wrote {banner_path}")

    # Top-right: match modern wizard white header, composite with alpha
    small_path = OUT_DIR / "wizard-small.bmp"
    _composite_on_bg(src, (55, 55), _WIZARD_HEADER_BG).save(small_path, format="BMP")
    print(f"Wrote {small_path}")


def main() -> int:
    src = _load_source()
    write_icons(src)
    write_installer_art(src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
