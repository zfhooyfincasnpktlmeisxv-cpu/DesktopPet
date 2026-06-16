"""世界坐标 → 屏幕坐标（与 OpenGL 相机一致）"""
from __future__ import annotations

import math
from typing import Optional, Tuple

from PyQt6.QtGui import QMatrix4x4, QVector3D, QVector4D

from .board_layout import board_radius


def make_camera_matrices(
    width: int,
    height: int,
    yaw: float,
    pitch: float,
    distance: float,
) -> tuple[QMatrix4x4, QMatrix4x4]:
    proj = QMatrix4x4()
    aspect = width / max(1, height)
    proj.perspective(34.0, aspect, 0.15, 120.0)

    view = QMatrix4x4()
    yaw_r = math.radians(yaw)
    pitch_r = math.radians(pitch)
    eye_x = distance * math.cos(pitch_r) * math.sin(yaw_r)
    eye_y = distance * math.sin(pitch_r) + 2.8
    eye_z = distance * math.cos(pitch_r) * math.cos(yaw_r)
    view.lookAt(
        QVector3D(eye_x, eye_y, eye_z),
        QVector3D(0, 0.0, 0),
        QVector3D(0, 1, 0),
    )
    return proj, view


def project_point(
    x: float,
    y: float,
    z: float,
    proj: QMatrix4x4,
    view: QMatrix4x4,
    width: int,
    height: int,
) -> Optional[Tuple[float, float, float]]:
    """返回 (sx, sy, depth) depth 越大越靠前。"""
    mvp = proj * view
    v = mvp * QVector4D(x, y, z, 1.0)
    if v.w() <= 0.01:
        return None
    ndc_x = v.x() / v.w()
    ndc_y = v.y() / v.w()
    ndc_z = v.z() / v.w()
    if ndc_x < -1.1 or ndc_x > 1.1 or ndc_y < -1.1 or ndc_y > 1.1:
        return None
    sx = (ndc_x + 1.0) * 0.5 * width
    sy = (1.0 - ndc_y) * 0.5 * height
    return (sx, sy, ndc_z)


def default_distance() -> float:
    return board_radius() * 1.75
