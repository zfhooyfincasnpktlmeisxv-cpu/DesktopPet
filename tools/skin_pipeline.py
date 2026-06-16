"""
DesktopPet 皮肤构建管线（唯一底层实现）

从 regenerate_skins_v3 提炼：整格切图 → 角点采样去背景 → 统一高度 → 脚线对齐。
不做颜色增强、不做 rembg、不做额外后处理，尽量保留原图画质。
"""
from __future__ import annotations

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BG_SAMPLE = 8
BG_DIST = 22
BLUR_RADIUS = 0.8


def _flood_fill(mask: np.ndarray, start_y: int, start_x: int) -> np.ndarray:
    h, w = mask.shape
    out = np.zeros((h, w), dtype=bool)
    if not mask[start_y, start_x]:
        return out
    stack = [(start_y, start_x)]
    out[start_y, start_x] = True
    while stack:
        y, x = stack.pop()
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not out[ny, nx]:
                out[ny, nx] = True
                stack.append((ny, nx))
    return out


def remove_background(frame_rgb: np.ndarray) -> Image.Image:
    """角点采样背景色 + 连通 flood + alpha 羽化（v3 同款）"""
    h, w = frame_rgb.shape[:2]
    bg_samples = []
    for y, x in (
        (0, 0),
        (0, w - BG_SAMPLE),
        (h - BG_SAMPLE, 0),
        (h - BG_SAMPLE, w - BG_SAMPLE),
    ):
        sample = frame_rgb[y : y + BG_SAMPLE, x : x + BG_SAMPLE]
        bg_samples.append(sample.mean(axis=(0, 1)))
    bg_color = np.mean(bg_samples, axis=0)

    dist = np.sqrt(((frame_rgb.astype(np.float32) - bg_color) ** 2).sum(axis=2))
    initial_bg = dist < BG_DIST

    bg_mask = np.zeros((h, w), dtype=bool)
    for y, x in ((0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)):
        if initial_bg[y, x]:
            bg_mask |= _flood_fill(initial_bg, y, x)

    alpha = np.where(bg_mask, 0, 255).astype(np.uint8)
    rgba = np.dstack((frame_rgb[:, :, 0], frame_rgb[:, :, 1], frame_rgb[:, :, 2], alpha))
    return Image.fromarray(rgba, "RGBA")


def soften_edges(img: Image.Image) -> Image.Image:
    """主体确定后再羽化边缘，避免碎块被糊进主体"""
    r, g, b, a = img.split()
    a = a.filter(ImageFilter.GaussianBlur(radius=BLUR_RADIUS))
    return Image.merge("RGBA", (r, g, b, a))


def keep_largest_component(img: Image.Image, alpha_min: int = 40) -> Image.Image:
    """只保留最大连通块，去掉底部/边缘多出来的碎块（多出来的脑袋）"""
    data = np.array(img.convert("RGBA"))
    alpha = data[:, :, 3]
    h, w = alpha.shape
    solid = alpha > alpha_min
    seen = np.zeros((h, w), dtype=bool)
    best: list[tuple[int, int]] = []

    for sy in range(h):
        for sx in range(w):
            if not solid[sy, sx] or seen[sy, sx]:
                continue
            q = deque([(sy, sx)])
            seen[sy, sx] = True
            cells: list[tuple[int, int]] = []
            while q:
                y, x = q.popleft()
                cells.append((y, x))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and solid[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        q.append((ny, nx))
            if len(cells) > len(best):
                best = cells

    out = np.zeros_like(data)
    for y, x in best:
        out[y, x] = data[y, x]
    return Image.fromarray(out, "RGBA")


def content_bbox(img: Image.Image, alpha_min: int = 30) -> tuple[int, int, int, int] | None:
    data = np.array(keep_largest_component(img, alpha_min))
    alpha = data[:, :, 3]
    rows = np.any(alpha > alpha_min, axis=1)
    cols = np.any(alpha > alpha_min, axis=0)
    if not np.any(rows) or not np.any(cols):
        return None
    top = int(np.argmax(rows))
    bottom = int(len(rows) - np.argmax(rows[::-1]))
    left = int(np.argmax(cols))
    right = int(len(cols) - np.argmax(cols[::-1]))
    return left, top, right, bottom


def foot_anchor(img: Image.Image) -> tuple[int, int]:
    """脚底区域 (cx, bottom)，仅基于主体最大连通块"""
    img = keep_largest_component(img)
    bbox = content_bbox(img)
    if bbox is None:
        w, h = img.size
        return w // 2, h
    left, top, right, bottom = bbox
    data = np.array(img.convert("RGBA"))
    band_top = max(top, bottom - max(4, (bottom - top) // 7))
    xs: list[int] = []
    for y in range(band_top, bottom):
        for x in range(left, right):
            if data[y, x, 3] > 40:
                xs.append(x)
    cx = sum(xs) // len(xs) if xs else (left + right) // 2
    return cx, bottom


def batch_content_height(contents: list[Image.Image], canvas: tuple[int, int]) -> int:
    tw, th = canvas
    if not contents:
        return max(1, int(th * 0.85))
    max_cw = max(c.size[0] for c in contents)
    max_ch = max(c.size[1] for c in contents)
    scale = min(tw * 0.88 / max_cw, th * 0.90 / max_ch)
    return max(1, int(max_ch * scale))


def cut_sheet(
    src: Path,
    rows: int,
    cols: int,
    *,
    row_offset: int = 0,
    row_count: int | None = None,
    max_frames: int | None = None,
) -> list[Image.Image]:
    """整格切图，不裁 inset，保留原图像素"""
    img = Image.open(src).convert("RGB")
    w, h = img.size
    fw, fh = w // cols, h // rows
    use_rows = row_count if row_count is not None else rows
    out: list[Image.Image] = []
    for r in range(row_offset, row_offset + use_rows):
        if r >= rows:
            break
        for c in range(cols):
            box = (c * fw, r * fh, (c + 1) * fw, (r + 1) * fh)
            out.append(img.crop(box))
            if max_frames and len(out) >= max_frames:
                return out
    return out


def matte_cells(raw_cells: list[Image.Image]) -> list[Image.Image]:
    out: list[Image.Image] = []
    for cell in raw_cells:
        rgba = remove_background(np.array(cell.convert("RGB")))
        rgba = keep_largest_component(rgba)
        out.append(soften_edges(rgba))
    return out


def compose_frames(
    mattes: list[Image.Image],
    canvas: tuple[int, int],
    *,
    target_h: int | None = None,
    anchor_feet: bool = True,
    uniform_scale: bool = False,
) -> list[Image.Image]:
    """统一缩放；uniform_scale 时各帧同一比例，避免喂食等动画越播越大"""
    tw, th = canvas
    margin_y = int(th * 0.04)

    crops: list[Image.Image | None] = []
    for img in mattes:
        bbox = content_bbox(img)
        crops.append(img.crop(bbox) if bbox else None)

    valid = [c for c in crops if c is not None]
    if not valid:
        blank = Image.new("RGBA", canvas, (0, 0, 0, 0))
        return [blank.copy() for _ in mattes]

    if target_h is None:
        target_h = batch_content_height(valid, canvas)

    unit_scale: float | None = None
    if uniform_scale:
        unit_scale = min(
            (tw * 0.88) / max(c.size[0] for c in valid),
            target_h / max(c.size[1] for c in valid),
        )

    target_foot_x = tw // 2
    target_foot_y = th - margin_y
    result: list[Image.Image] = []

    for crop in crops:
        frame = Image.new("RGBA", canvas, (0, 0, 0, 0))
        if crop is None:
            result.append(frame)
            continue

        cw, ch = crop.size
        if unit_scale is not None:
            nw = max(1, int(cw * unit_scale))
            nh = max(1, int(ch * unit_scale))
        else:
            nh = target_h
            nw = max(1, int(cw * nh / ch))
            if nw > int(tw * 0.88):
                nh = max(1, int(nh * (tw * 0.88) / nw))
                nw = max(1, int(tw * 0.88))

        resized = crop.resize((nw, nh), Image.Resampling.LANCZOS)

        if anchor_feet:
            cx, bottom = foot_anchor(resized)
            paste_x = target_foot_x - cx
            paste_y = target_foot_y - bottom
        else:
            paste_x = (tw - nw) // 2
            paste_y = (th - nh) // 2

        frame.paste(resized, (paste_x, paste_y), resized)
        result.append(frame)

    return result


def build_portrait_idle(
    src: Path,
    canvas: tuple[int, int],
    *,
    target_h: int | None = None,
) -> Image.Image:
    """人物立绘单张 → 待机画布（静态美立绘）"""
    img = Image.open(src).convert("RGB")
    rgba = soften_edges(keep_largest_component(remove_background(np.array(img))))
    return compose_frames(
        [rgba],
        canvas,
        target_h=target_h,
        anchor_feet=True,
        uniform_scale=True,
    )[0]


def build_animation_frames(
    raw_cells: list[Image.Image],
    canvas: tuple[int, int],
    *,
    target_h: int | None = None,
    anchor_feet: bool = True,
    uniform_scale: bool = False,
) -> list[Image.Image]:
    mattes = matte_cells(raw_cells)
    return compose_frames(
        mattes,
        canvas,
        target_h=target_h,
        anchor_feet=anchor_feet,
        uniform_scale=uniform_scale,
    )


def _iris_centroid(
    data: np.ndarray,
    x0: int,
    x1: int,
    y0: int,
    y1: int,
) -> tuple[int, int, int, int] | None:
    """在指定区域内取蓝色虹膜质心 → (cx, cy, rx, ry)"""
    region = data[y0:y1, x0:x1]
    alpha = region[:, :, 3] > 128
    rgb = region[:, :, :3]
    mask = alpha & (rgb[:, :, 2] > rgb[:, :, 0] + 12) & (rgb[:, :, 2] > 85)
    ys, xs = np.where(mask)
    if len(xs) < 20:
        return None
    cx = int(xs.mean()) + x0
    cy = int(ys.mean()) + y0
    rx = max(5, min(9, int((xs.max() - xs.min()) / 2) + 1))
    ry = max(3, min(6, int((ys.max() - ys.min()) / 2) + 1))
    return cx, cy, rx, ry


_EYE_FRAC_REFS: tuple[tuple[float, float, float, float], ...] = (
    (0.321, 0.365, 0.040, 0.028),
    (0.754, 0.368, 0.045, 0.028),
)


def _find_eye_regions(
    idle_frame: Image.Image,
    bbox: tuple[int, int, int, int] | None = None,
) -> list[tuple[int, int, int, int]]:
    """按人物主体 bbox 比例定位双眼。"""
    if bbox is None:
        bbox = content_bbox(idle_frame)
    if bbox is None:
        return []

    left, top, right, bottom = bbox
    fw = max(1, right - left)
    fh = max(1, bottom - top)
    eyes: list[tuple[int, int, int, int]] = []
    for fx, fy, frx, fry in _EYE_FRAC_REFS:
        cx = left + int(round(fw * fx))
        cy = top + int(round(fh * fy))
        rx = max(5, int(round(fw * frx)))
        ry = max(4, int(round(fh * fry)))
        eyes.append((cx, cy, rx, ry))
    return eyes


def _sample_lid_tone(
    img: Image.Image, cx: int, cy: int, rx: int, ry: int
) -> tuple[int, int, int, int]:
    """在眼睛上方/两侧取样肤色，避免采到蓝色虹膜"""
    data = np.array(img.convert("RGBA"))
    h, w = data.shape[:2]
    samples: list[np.ndarray] = []
    for dy in (-5, -9, -13, -17):
        for dx in (-rx, -rx // 2, 0, rx // 2, rx):
            y = cy + dy
            x = cx + dx
            if 0 <= y < h and 0 <= x < w:
                px = data[y, x]
                r, g, b, a = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                if a > 80 and b < r + 8 and b < 195 and r > 140:
                    samples.append(np.array([r, g, b]))
    if not samples:
        for dy in (-6, -10, -14, -18):
            y = cy + dy
            x = cx
            if 0 <= y < h and 0 <= x < w:
                px = data[y, x]
                r, g, b, a = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                if a > 80:
                    samples.append(np.array([r, g, b]))
    if not samples:
        return (238, 228, 222, 255)

    mean = np.mean(samples, axis=0).astype(int)
    r, g, b = int(mean[0]), int(mean[1]), int(mean[2])
    avg = (r + g) // 2
    b = min(b, avg + 2)
    r = max(min(r, avg + 10), avg - 8)
    g = max(min(g, avg + 8), avg - 6)
    return r, g, b, 255


def _sample_skin_tone(img: Image.Image, cx: int, cy: int) -> tuple[int, int, int, int]:
    """在眼下取样，用于绘制眼睑色"""
    data = np.array(img.convert("RGBA"))
    h, w = data.shape[:2]
    samples: list[np.ndarray] = []
    for dy in range(4, 14):
        y = min(h - 1, cy + dy)
        x = min(w - 1, max(0, cx))
        px = data[y, x]
        if px[3] > 80:
            samples.append(px[:3])
    if not samples:
        return (210, 180, 170, 255)
    mean = np.mean(samples, axis=0).astype(int)
    return int(mean[0]), int(mean[1]), int(mean[2]), 255


def _draw_eyelids(
    base: Image.Image,
    eyes: list[tuple[int, int, int, int]],
    close: float,
) -> Image.Image:
    """从上往下盖肤色眼睑，遮住虹膜；不用黑线横切瞳孔"""
    if close <= 0.01:
        return base.copy()
    out = base.copy()
    draw = ImageDraw.Draw(out)
    for cx, cy, rx, ry in eyes:
        lid = _sample_lid_tone(base, cx, cy, rx, ry)
        eye_top = cy - ry - 1
        eye_bottom = cy + ry + 1
        lid_w = rx + 2

        if close >= 0.92:
            draw.ellipse(
                (cx - lid_w, eye_top - 1, cx + lid_w, eye_bottom + 1),
                fill=lid,
            )
            continue

        eye_h = eye_bottom - eye_top
        lid_edge = min(eye_bottom, eye_top + int(eye_h * (0.38 + close * 0.72)))
        draw.ellipse(
            (cx - lid_w, eye_top - 1, cx + lid_w, lid_edge + 1),
            fill=lid,
        )
        draw.rectangle((cx - lid_w, eye_top, cx + lid_w, lid_edge), fill=lid)
        if close >= 0.45:
            draw.chord(
                (cx - lid_w, lid_edge - max(2, ry // 2), cx + lid_w, lid_edge + max(2, ry // 3)),
                start=0,
                end=180,
                fill=lid,
            )
    return out


def build_blink_frames(idle_frame: Image.Image) -> list[Image.Image]:
    """
    由待机立绘生成眨眼序列（仅改眼部，身体不动）。
    帧序：睁开 → 半闭 → 全闭 → 半闭 → 睁开
    """
    bbox = content_bbox(idle_frame)
    if bbox is None:
        return [idle_frame.copy() for _ in range(3)]

    eyes = _find_eye_regions(idle_frame, bbox)
    open_frame = idle_frame.copy()
    return [
        open_frame.copy(),
        _draw_eyelids(open_frame, eyes, 0.5),
        _draw_eyelids(open_frame, eyes, 1.0),
        _draw_eyelids(open_frame, eyes, 0.5),
        open_frame.copy(),
    ]
