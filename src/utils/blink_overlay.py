"""运行时眨眼叠加：精准眼位 + 贴合眼形的自然闭合。"""
from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap

logger = logging.getLogger(__name__)

# 快闭 → 短暂全闭 → 慢睁（13 帧，配合 15fps ≈ 0.87s）
BLINK_CURVE = (
    0.0,
    0.06,
    0.22,
    0.48,
    0.74,
    0.92,
    1.0,
    1.0,
    0.92,
    0.74,
    0.48,
    0.22,
    0.06,
    0.0,
)
BLINK_FRAME_COUNT = len(BLINK_CURVE)


@dataclass(frozen=True)
class EyeSpec:
    """单眼参数：中心、椭球半径、上睫毛弧宽比例。"""

    cx: int
    cy: int
    rx: float
    ry: float
    lash_rx: float  # 睫毛横向略宽于眼廓

    @classmethod
    def from_tuple(cls, t: tuple[int, int, int, int]) -> EyeSpec:
        cx, cy, rx, ry = t
        return cls(
            cx=cx,
            cy=cy,
            rx=float(rx),
            ry=float(ry),
            lash_rx=float(rx) * 1.12 + 1.0,
        )

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.cx, self.cy, int(round(self.rx)), int(round(self.ry))


def close_amount(frame_index: int, frame_count: int = BLINK_FRAME_COUNT) -> float:
    if frame_count <= 1:
        return 1.0
    idx = max(0, min(frame_index, frame_count - 1))
    if frame_count == len(BLINK_CURVE):
        return BLINK_CURVE[idx]
    pos = idx / max(1, frame_count - 1) * (len(BLINK_CURVE) - 1)
    i = min(int(pos), len(BLINK_CURVE) - 2)
    frac = pos - i
    return BLINK_CURVE[i] * (1.0 - frac) + BLINK_CURVE[i + 1] * frac


def _content_bbox(data: np.ndarray) -> tuple[int, int, int, int] | None:
    mask = data[:, :, 3] > 40
    ys, xs = np.where(mask)
    if len(xs) < 80:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _refine_eye_bounds(
    data: np.ndarray,
    cx: int,
    cy: int,
    cells: list[tuple[int, int]],
) -> EyeSpec:
    """
    由虹膜连通域拟合眼廓：二次元大眼横向更宽、纵向略扁，中心微上移。
    """
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    iw, ih = x1 - x0, y1 - y0

    rx = max(8.0, min(24.0, iw / 2.0 + 2.5))
    ry = max(6.0, min(16.0, ih / 2.0 + 1.5))

    # 大眼比例：略宽略扁
    rx = min(24.0, rx * 1.06)
    ry = max(6.0, ry * 0.94)

    cx = int(round((x0 + x1) / 2))
    cy = int(round((y0 + y1) / 2 - 0.8))

    return EyeSpec(cx=cx, cy=cy, rx=rx, ry=ry, lash_rx=rx * 1.14 + 1.5)


def detect_eye_regions(img: Image.Image) -> list[tuple[int, int, int, int]]:
    """检测双眼，返回 [(cx, cy, rx, ry), ...] 从左到右。"""
    specs = detect_eye_specs(img)
    return [s.as_tuple() for s in specs]


def detect_eye_specs(img: Image.Image) -> list[EyeSpec]:
    data = np.array(img.convert("RGBA"))
    bbox = _content_bbox(data)
    if bbox is None:
        return []

    left, top, right, bottom = bbox
    face_bottom = top + int((bottom - top) * 0.42)
    rgb = data[:, :, :3]
    alpha = data[:, :, 3] > 40
    blue = (
        alpha
        & (rgb[:, :, 2] > rgb[:, :, 0] + 15)
        & (rgb[:, :, 2] > 100)
        & (rgb[:, :, 2] > rgb[:, :, 1] + 5)
    )
    blue[:top, :] = False
    blue[face_bottom:, :] = False
    blue[:, :left] = False
    blue[:, right + 1 :] = False

    h, w = blue.shape
    visited = np.zeros(blue.shape, dtype=bool)
    components: list[list[tuple[int, int]]] = []

    for y in range(top, min(face_bottom, h)):
        for x in range(left, min(right + 1, w)):
            if not blue[y, x] or visited[y, x]:
                continue
            queue: deque[tuple[int, int]] = deque([(y, x)])
            visited[y, x] = True
            cells: list[tuple[int, int]] = []
            while queue:
                cy, cx = queue.popleft()
                cells.append((cx, cy))
                for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    ny, nx = cy + dy, cx + dx
                    if (
                        top <= ny < face_bottom
                        and left <= nx <= right
                        and blue[ny, nx]
                        and not visited[ny, nx]
                    ):
                        visited[ny, nx] = True
                        queue.append((ny, nx))
            if 40 < len(cells) < 1200:
                components.append(cells)

    if len(components) < 2:
        logger.warning("自动眼位检测失败，仅找到 %d 个区域", len(components))
        return []

    components.sort(key=len, reverse=True)
    specs = [_refine_eye_bounds(data, 0, 0, cells) for cells in components[:2]]
    specs.sort(key=lambda s: s.cx)
    return specs


def load_eye_regions_from_skin(skin_dir: Path, idle_frame: Image.Image | None = None) -> list[tuple[int, int, int, int]]:
    specs = load_eye_specs_from_skin(skin_dir, idle_frame)
    return [s.as_tuple() for s in specs]


def load_eye_specs_from_skin(skin_dir: Path, idle_frame: Image.Image | None = None) -> list[EyeSpec]:
    if idle_frame is not None:
        detected = detect_eye_specs(idle_frame)
        if len(detected) >= 2:
            _save_eye_specs(skin_dir, idle_frame, detected)
            return detected

    path = skin_dir / "eye_regions.json"
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            regions = raw.get("regions") or []
            specs: list[EyeSpec] = []
            for r in regions:
                rx = float(r.get("rx", 10))
                specs.append(
                    EyeSpec(
                        cx=int(r["cx"]),
                        cy=int(r["cy"]),
                        rx=rx,
                        ry=float(r.get("ry", rx * 0.75)),
                        lash_rx=float(r.get("lash_rx", rx * 1.14 + 1.5)),
                    )
                )
            if len(specs) >= 2:
                return sorted(specs, key=lambda s: s.cx)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    if idle_frame is not None:
        return detect_eye_specs(idle_frame)
    return []


def _save_eye_specs(skin_dir: Path, idle_frame: Image.Image, specs: list[EyeSpec]) -> None:
    try:
        skin_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "source": "auto_detect_v2",
            "image_size": [idle_frame.width, idle_frame.height],
            "method": "iris_connected_components_refined",
            "regions": [
                {
                    "cx": s.cx,
                    "cy": s.cy,
                    "rx": round(s.rx, 1),
                    "ry": round(s.ry, 1),
                    "lash_rx": round(s.lash_rx, 1),
                }
                for s in specs
            ],
        }
        (skin_dir / "eye_regions.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        logger.debug("无法写入 eye_regions.json: %s", e)


def _sample_skin_color(data: np.ndarray, spec: EyeSpec) -> np.ndarray:
    h, w = data.shape[:2]
    cx, cy, rx, ry = spec.cx, spec.cy, int(spec.rx), int(spec.ry)
    samples: list[np.ndarray] = []
    for dy in range(-ry - 16, -ry - 1):
        for dx in range(-rx - 2, rx + 3):
            y, x = cy + dy, cx + dx
            if not (0 <= y < h and 0 <= x < w):
                continue
            px = data[y, x]
            if px[3] < 80:
                continue
            r, g, b = int(px[0]), int(px[1]), int(px[2])
            if b > r + 12 and b > 90:
                continue
            if r < 120 or (r > 245 and g > 240 and b > 235):
                continue
            samples.append(px[:3].astype(np.float32))
    if not samples:
        y = max(0, cy - ry - 5)
        x = min(w - 1, max(0, cx))
        if data[y, x, 3] > 80:
            return data[y, x, :3].astype(np.float32)
        return np.array([248.0, 228.0, 218.0], dtype=np.float32)
    return np.median(np.stack(samples), axis=0)


def _draw_eyelids(
    base: Image.Image,
    eyes: list[tuple[int, int, int, int]] | list[EyeSpec],
    close: float,
) -> Image.Image:
    if close <= 0.01 or not eyes:
        return base.copy()

    specs = [EyeSpec.from_tuple(e) if isinstance(e, tuple) else e for e in eyes]
    data = np.array(base.convert("RGBA"), dtype=np.float32)
    h, w = data.shape[:2]
    raw = data.astype(np.uint8)

    for spec in specs:
        cx, cy, rx, ry, lash_rx = spec.cx, spec.cy, spec.rx, spec.ry, spec.lash_rx
        skin = _sample_skin_color(raw, spec)

        pad = int(max(rx, ry) + 4)
        y0, y1 = max(0, cy - pad), min(h, cy + pad + 1)
        x0, x1 = max(0, cx - pad), min(w, cx + pad + 1)

        yy, xx = np.mgrid[y0:y1, x0:x1]
        nx = (xx - cx) / rx
        ny = (yy - cy) / ry
        in_eye = (nx * nx + ny * ny) <= 1.04

        # 上眼睑曲线略弯（二次元上弧更平）
        lid_ny = -1.06 + close * 2.38
        upper_arc = 1.0 - 0.12 * (nx ** 2)
        effective_lid = lid_ny * upper_arc
        cover = in_eye & (ny <= effective_lid)

        if close >= 0.96:
            strength = np.where(in_eye, 1.0, 0.0)
        else:
            edge = np.clip((effective_lid - ny) / 0.2, 0.0, 1.0)
            strength = np.where(cover, np.maximum(edge, 0.94), 0.0)

        sub = data[y0:y1, x0:x1]
        for c in range(3):
            sub[:, :, c] = np.where(
                strength > 0,
                sub[:, :, c] * (1.0 - strength) + skin[c] * strength,
                sub[:, :, c],
            )

        # 上睫毛：只画上缘，略宽于眼白
        if close >= 0.25:
            nx_lash = (xx - cx) / lash_rx
            in_lash_band = (nx_lash ** 2) <= 1.0
            lash_zone = in_lash_band & (ny <= effective_lid + 0.05) & (ny >= effective_lid - 0.1)
            lash = np.clip(1.0 - np.abs(ny - effective_lid) / 0.07, 0, 1) * 0.5
            lash *= np.clip(1.0 - np.abs(nx) * 0.55, 0.3, 1.0)
            for c in range(3):
                dark = (42.0, 34.0, 48.0)[c]
                sub[:, :, c] = np.where(
                    lash_zone,
                    sub[:, :, c] * (1.0 - lash) + dark * lash,
                    sub[:, :, c],
                )

        if close >= 0.96:
            crease = in_eye & (np.abs(ny) < 0.14)
            shade = skin * 0.87
            for c in range(3):
                sub[:, :, c] = np.where(
                    crease,
                    sub[:, :, c] * 0.88 + shade[c] * 0.12,
                    sub[:, :, c],
                )

        data[y0:y1, x0:x1] = sub

    return Image.fromarray(np.clip(data, 0, 255).astype(np.uint8), "RGBA")


def apply_blink_to_image(
    pil: Image.Image,
    frame_index: int,
    *,
    eyes: list[tuple[int, int, int, int]] | None = None,
    frame_count: int = BLINK_FRAME_COUNT,
) -> Image.Image:
    amount = close_amount(frame_index, frame_count)
    if amount <= 0.01:
        return pil
    eye_list = eyes if eyes else detect_eye_regions(pil)
    if not eye_list:
        return pil
    return _draw_eyelids(pil, eye_list, amount)


def apply_blink_to_pixmap(
    pixmap: QPixmap,
    frame_index: int,
    *,
    eyes: list[tuple[int, int, int, int]] | None = None,
) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    img = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = img.width(), img.height()
    ptr = img.constBits()
    ptr.setsize(img.sizeInBytes())
    pil = Image.frombytes("RGBA", (w, h), bytes(ptr), "raw", "RGBA")
    result = apply_blink_to_image(pil, frame_index, eyes=eyes)
    data = result.tobytes("raw", "RGBA")
    out = QImage(data, w, h, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(out.copy())
