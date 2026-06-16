"""OpenGL 3D 棋盘 — M3 贴图换皮 + 光照着色"""
from __future__ import annotations

import logging
import math
import time
from typing import Dict, List, Optional, Tuple

import numpy as np

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QMatrix4x4, QPainter, QPen, QColor
from PyQt6.QtOpenGL import (
    QOpenGLBuffer,
    QOpenGLFunctions_2_0,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
    QOpenGLVertexArrayObject,
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

from ...utils.constants import RICHMAN_PACE
from .board_data import TileKind, all_tiles
from .board_layout import board_radius, tile_world_position
from .board_projection import default_distance, make_camera_matrices, project_point
from .board_textures import create_atlas_texture, create_center_texture, ensure_textures, tile_uv
from .game_engine import GamePhase, RichmanEngine
from .movement_anim import StepHopAnimator
from .tile_style import PLAYER_COLORS, draw_center_logo, draw_tile_badge

logger = logging.getLogger(__name__)

COLOR_VERT = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aColor;
uniform mat4 uMVP;
out vec3 vColor;
void main() {
    vColor = aColor;
    gl_Position = uMVP * vec4(aPos, 1.0);
}
"""

COLOR_FRAG = """
#version 330 core
in vec3 vColor;
out vec4 fragColor;
void main() {
    fragColor = vec4(vColor, 1.0);
}
"""

TEX_VERT = """
#version 330 core
layout(location = 0) in vec3 aPos;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV;
layout(location = 3) in vec3 aTint;
uniform mat4 uMVP;
out vec3 vNormal;
out vec2 vUV;
out vec3 vTint;
void main() {
    vNormal = aNormal;
    vUV = aUV;
    vTint = aTint;
    gl_Position = uMVP * vec4(aPos, 1.0);
}
"""

TEX_FRAG = """
#version 330 core
in vec3 vNormal;
in vec2 vUV;
in vec3 vTint;
uniform sampler2D uAtlas;
uniform vec3 uLightDir;
uniform float uGloss;
out vec4 fragColor;
void main() {
    vec4 tex = texture(uAtlas, vUV);
    if (tex.a < 0.04) discard;
    float diff = clamp(dot(normalize(vNormal), normalize(uLightDir)), 0.35, 1.0);
    vec3 col = tex.rgb * diff * vTint;
    float spec = pow(clamp(1.0 - vUV.y, 0.0, 1.0), 3.0) * 0.22 * uGloss;
    col += vec3(spec);
    fragColor = vec4(col, tex.a);
}
"""

GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_COLOR_BUFFER_BIT = 0x00004000
GL_DEPTH_BUFFER_BIT = 0x00000100
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE = 1
GL_ONE_MINUS_SRC_ALPHA = 0x0303


class _ColorMesh:
    STRIDE = 24

    def __init__(self):
        self._vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self._vao = QOpenGLVertexArrayObject()
        self._count = 0

    def upload(self, vertices: np.ndarray) -> None:
        self._count = int(vertices.shape[0])
        if self._count == 0:
            return
        if not self._vbo.isCreated():
            self._vbo.create()
        if not self._vao.isCreated():
            self._vao.create()
        self._vao.bind()
        self._vbo.bind()
        self._vbo.allocate(vertices.tobytes(), vertices.nbytes)
        self._vao.release()

    def draw(self, program: QOpenGLShaderProgram, gl: QOpenGLFunctions_2_0) -> None:
        if self._count <= 0:
            return
        self._vao.bind()
        self._vbo.bind()
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, self.STRIDE)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 12, 3, self.STRIDE)
        gl.glDrawArrays(GL_TRIANGLES, 0, self._count)
        program.disableAttributeArray(0)
        program.disableAttributeArray(1)
        self._vao.release()


class _TexMesh:
    STRIDE = 44  # 3+3+2+3 floats + pad

    def __init__(self):
        self._vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        self._vao = QOpenGLVertexArrayObject()
        self._count = 0

    def upload(self, vertices: np.ndarray) -> None:
        self._count = int(vertices.shape[0])
        if self._count == 0:
            return
        if not self._vbo.isCreated():
            self._vbo.create()
        if not self._vao.isCreated():
            self._vao.create()
        self._vao.bind()
        self._vbo.bind()
        self._vbo.allocate(vertices.tobytes(), vertices.nbytes)
        self._vao.release()

    def draw(self, program: QOpenGLShaderProgram, gl: QOpenGLFunctions_2_0) -> None:
        if self._count <= 0:
            return
        self._vao.bind()
        self._vbo.bind()
        program.enableAttributeArray(0)
        program.setAttributeBuffer(0, GL_FLOAT, 0, 3, self.STRIDE)
        program.enableAttributeArray(1)
        program.setAttributeBuffer(1, GL_FLOAT, 12, 3, self.STRIDE)
        program.enableAttributeArray(2)
        program.setAttributeBuffer(2, GL_FLOAT, 24, 2, self.STRIDE)
        program.enableAttributeArray(3)
        program.setAttributeBuffer(3, GL_FLOAT, 32, 3, self.STRIDE)
        gl.glDrawArrays(GL_TRIANGLES, 0, self._count)
        program.disableAttributeArray(0)
        program.disableAttributeArray(1)
        program.disableAttributeArray(2)
        program.disableAttributeArray(3)
        self._vao.release()


class RichmanGLViewport(QOpenGLWidget):
    init_failed = pyqtSignal(str)

    TOKEN_COLORS = [
        (0.2, 0.95, 0.75),
        (0.4, 0.7, 1.0),
        (1.0, 0.55, 0.75),
        (1.0, 0.75, 0.35),
    ]

    def __init__(self, engine: RichmanEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._gl: Optional[QOpenGLFunctions_2_0] = None
        self._color_prog: Optional[QOpenGLShaderProgram] = None
        self._tex_prog: Optional[QOpenGLShaderProgram] = None
        self._atlas_tex: Optional[QOpenGLTexture] = None
        self._center_tex: Optional[QOpenGLTexture] = None
        self._body_mesh = _ColorMesh()
        self._top_mesh = _TexMesh()
        self._center_mesh = _TexMesh()
        self._glow_mesh = _TexMesh()
        self._token_mesh = _ColorMesh()
        self._gl_ready = False

        self._yaw = 36.0
        self._pitch = 64.0
        self._distance = default_distance()
        self._last_mouse = QPoint()
        self._dragging = False
        self._last_proj = QMatrix4x4()
        self._last_view = QMatrix4x4()
        self._pulse = 0.0

        self._display_positions: Dict[int, Tuple[float, float, float]] = {}
        self._hop = StepHopAnimator(self, duration_ms=int(RICHMAN_PACE["step_hop_ms"]), hop_peak=0.62)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(33)
        self._pulse_timer.timeout.connect(self._tick_pulse)

        self._engine.state_changed.connect(self._rebuild_meshes)
        self._engine.player_stepped.connect(self._on_player_stepped)
        self._engine.phase_changed.connect(lambda _: self.update())
        self.setMinimumSize(520, 520)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _tick_pulse(self) -> None:
        self._pulse = (time.time() * 2.5) % (2 * math.pi)
        if self._engine.phase != GamePhase.GAME_OVER:
            self.update()

    def _rebuild_meshes(self) -> None:
        if not self._gl_ready:
            return
        self.makeCurrent()
        body, tops, glow = self._build_board_geometry()
        self._body_mesh.upload(body)
        self._top_mesh.upload(tops)
        self._glow_mesh.upload(glow)
        self._center_mesh.upload(self._build_center_quad())
        self._token_mesh.upload(self._build_token_vertices(self.TOKEN_COLORS[0]))
        self.doneCurrent()
        self.update()

    def _token_world_pos(self, tile_index: int) -> Tuple[float, float, float]:
        x, y, z = tile_world_position(tile_index)
        return (x, y + 0.48, z)

    def _on_player_stepped(self, player_id: int, tile_index: int) -> None:
        target = self._token_world_pos(tile_index)
        start = self._display_positions.get(player_id, target)
        self._hop.start(start, target, lambda pos, pid=player_id: self._set_token_pos(pid, pos), self.update)

    def _set_token_pos(self, player_id: int, pos: Tuple[float, float, float]) -> None:
        self._display_positions[player_id] = pos
        self.update()

    def initializeGL(self) -> None:
        try:
            ensure_textures()
            gl = QOpenGLFunctions_2_0()
            gl.initializeOpenGLFunctions()
            self._gl = gl
            gl.glEnable(GL_DEPTH_TEST)
            gl.glClearColor(0.04, 0.07, 0.12, 1.0)

            self._color_prog = QOpenGLShaderProgram(self)
            self._color_prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, COLOR_VERT)
            self._color_prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, COLOR_FRAG)
            if not self._color_prog.link():
                raise RuntimeError(self._color_prog.log())

            self._tex_prog = QOpenGLShaderProgram(self)
            self._tex_prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, TEX_VERT)
            self._tex_prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, TEX_FRAG)
            if not self._tex_prog.link():
                raise RuntimeError(self._tex_prog.log())

            self._atlas_tex = create_atlas_texture(self)
            self._center_tex = create_center_texture(self)

            for p in self._engine.players():
                self._display_positions[p.id] = self._token_world_pos(p.position)

            self._gl_ready = True
            self._pulse_timer.start()
            self._rebuild_meshes()
        except Exception as exc:
            self._gl_ready = False
            logger.exception("大富翁 OpenGL 初始化失败")
            self.init_failed.emit(str(exc))

    def paintGL(self) -> None:
        if not self._gl_ready or not self._gl or not self._color_prog or not self._tex_prog:
            return
        gl = self._gl
        gl.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        proj, view = make_camera_matrices(self.width(), self.height(), self._yaw, self._pitch, self._distance)
        self._last_proj = proj
        self._last_view = view
        mvp = proj * view

        # 底座
        self._color_prog.bind()
        mvp_loc = self._color_prog.uniformLocation("uMVP")
        self._color_prog.setUniformValue(mvp_loc, mvp)
        self._body_mesh.draw(self._color_prog, gl)
        self._color_prog.release()

        # 贴图顶面（仅底座阴影，格子信息由屏幕叠层卡片绘制）
        # self._top_mesh / glow 保留几何但不绘制，避免与文字卡片抢视觉

        # 棋子
        self._color_prog.bind()
        self._color_prog.setUniformValue(mvp_loc, mvp)
        for p in self._engine.players():
            if p.bankrupt:
                continue
            pos = self._display_positions.get(p.id, self._token_world_pos(p.position))
            offset = (p.id - self._engine.current_player.id) * 0.14
            model = QMatrix4x4()
            model.translate(pos[0] + offset, pos[1], pos[2] + offset)
            model.scale(0.24)
            color = self.TOKEN_COLORS[p.id % len(self.TOKEN_COLORS)]
            self._token_mesh.upload(self._build_token_vertices(color))
            self._color_prog.setUniformValue(mvp_loc, mvp * model)
            self._token_mesh.draw(self._color_prog, gl)
        self._color_prog.release()

        self._draw_overlay()

    def _draw_overlay(self) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        cp_pos: Optional[int] = None
        if self._engine.players() and self._engine.phase != GamePhase.GAME_OVER:
            cp_pos = self._engine.current_player.position

        center_pt = project_point(0, 0.12, 0, self._last_proj, self._last_view, self.width(), self.height())
        if center_pt:
            draw_center_logo(painter, center_pt[0], center_pt[1])

        tile_entries: List[Tuple[float, float, float, object]] = []
        for tile in all_tiles():
            wx, wy, wz = tile_world_position(tile.index)
            pt = project_point(wx, wy + 0.08, wz, self._last_proj, self._last_view, self.width(), self.height())
            if pt:
                tile_entries.append((pt[1], pt[2], pt[0], tile))
        tile_entries.sort(key=lambda e: e[0])

        for sy, depth, sx, tile in tile_entries:
            prop = self._engine.property_at(tile.index)
            owner_col = None
            if prop.owner_id is not None:
                owner_col = PLAYER_COLORS[prop.owner_id % len(PLAYER_COLORS)]
            badge_scale = 1.08 + max(0.0, min(0.3, (depth + 0.15) * 0.2))
            draw_tile_badge(
                painter,
                sx,
                sy,
                tile,
                owned=prop.owner_id is not None,
                level=prop.level,
                owner_color=owner_col,
                highlight=tile.index == cp_pos,
                scale=badge_scale,
            )

        for pl in self._engine.players():
            if pl.bankrupt:
                continue
            pos = self._display_positions.get(pl.id, self._token_world_pos(pl.position))
            pt = project_point(pos[0], pos[1] + 0.35, pos[2], self._last_proj, self._last_view, self.width(), self.height())
            if not pt:
                continue
            col = PLAYER_COLORS[pl.id % len(PLAYER_COLORS)]
            painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
            painter.setPen(col)
            painter.drawText(int(pt[0] - 28), int(pt[1] - 38), 56, 18, Qt.AlignmentFlag.AlignCenter, pl.name[:3])

        painter.end()

    def _build_board_geometry(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        body: List[float] = []
        tops: List[float] = []
        glow: List[float] = []
        tw, td = 0.92, 0.92
        th_body = 0.035
        cp_pos: Optional[int] = None
        if self._engine.players() and self._engine.phase != GamePhase.GAME_OVER:
            cp_pos = self._engine.current_player.position

        self._add_box(body, 0, 0.02, 0, 4.4, 0.05, 3.8, (0.06, 0.09, 0.14))

        for tile in all_tiles():
            cx, cy, cz = tile_world_position(tile.index)
            prop = self._engine.property_at(tile.index)
            self._add_box(body, cx, cy + th_body / 2, cz, tw, th_body, td, (0.05, 0.07, 0.11))

            tint = (1.0, 1.0, 1.0)
            if prop.owner_id is not None:
                oc = PLAYER_COLORS[prop.owner_id % len(PLAYER_COLORS)]
                tint = (oc.redF() * 0.35 + 0.75, oc.greenF() * 0.35 + 0.75, oc.blueF() * 0.35 + 0.75)

            y = cy + th_body + 0.005
            hw, hd = tw * 0.38, td * 0.38
            u0, v0, u1, v1 = tile_uv(tile.index)
            self._add_tex_quad(tops, cx, y, cz, hw, hd, u0, v0, u1, v1, tint)

            if tile.index == cp_pos:
                pulse = 0.06 + 0.02 * math.sin(self._pulse)
                self._add_tex_quad(
                    glow, cx, y + 0.02, cz, hw + pulse, hd + pulse, u0, v0, u1, v1, (0.3, 0.95, 1.0)
                )

            if tile.kind == TileKind.PROPERTY and prop.owner_id is not None and prop.level > 0:
                for i in range(min(prop.level, 4)):
                    ox = (i - 1.5) * 0.13
                    hh = 0.07 + i * 0.035
                    self._add_box(body, cx + ox, y + hh / 2 + 0.04, cz + 0.1, 0.09, hh, 0.09, (0.92, 0.95, 1.0))

        return (
            np.array(body, dtype=np.float32).reshape(-1, 6),
            np.array(tops, dtype=np.float32).reshape(-1, 11),
            np.array(glow, dtype=np.float32).reshape(-1, 11),
        )

    def _build_center_quad(self) -> np.ndarray:
        tops: List[float] = []
        y = 0.11
        self._add_tex_quad(tops, 0, y, 0, 1.65, 1.15, 0.0, 0.0, 1.0, 1.0, (1.0, 1.0, 1.0))
        return np.array(tops, dtype=np.float32).reshape(-1, 11)

    def _add_tex_quad(
        self,
        verts: List[float],
        cx: float,
        y: float,
        cz: float,
        hw: float,
        hd: float,
        u0: float,
        v0: float,
        u1: float,
        v1: float,
        tint: Tuple[float, float, float],
    ) -> None:
        n = (0.0, 1.0, 0.0)
        corners = [
            (cx - hw, y, cz - hd, u0, v1),
            (cx + hw, y, cz - hd, u1, v1),
            (cx + hw, y, cz + hd, u1, v0),
            (cx - hw, y, cz + hd, u0, v0),
        ]
        tris = [(0, 1, 2), (0, 2, 3)]
        for a, b, c in tris:
            for idx in (a, b, c):
                x, yy, z, u, v = corners[idx]
                verts.extend([x, yy, z, n[0], n[1], n[2], u, v, tint[0], tint[1], tint[2]])

    def _build_token_vertices(self, color: Tuple[float, float, float]) -> np.ndarray:
        verts: List[float] = []
        self._add_box(verts, 0, 0.18, 0, 0.8, 0.8, 0.8, color)
        self._add_box(verts, 0, 0.65, 0, 0.38, 0.22, 0.38, (min(1.0, color[0] + 0.2), min(1.0, color[1] + 0.2), min(1.0, color[2] + 0.2)))
        return np.array(verts, dtype=np.float32).reshape(-1, 6)

    def _add_box(
        self,
        verts: List[float],
        cx: float,
        cy: float,
        cz: float,
        w: float,
        h: float,
        d: float,
        color: Tuple[float, float, float],
    ) -> None:
        hw, hh, hd = w / 2, h / 2, d / 2
        c = [
            (cx - hw, cy - hh, cz - hd),
            (cx + hw, cy - hh, cz - hd),
            (cx + hw, cy + hh, cz - hd),
            (cx - hw, cy + hh, cz - hd),
            (cx - hw, cy - hh, cz + hd),
            (cx + hw, cy - hh, cz + hd),
            (cx + hw, cy + hh, cz + hd),
            (cx - hw, cy + hh, cz + hd),
        ]
        faces = [(0, 1, 2, 3), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 3, 7, 4), (1, 2, 6, 5)]
        shade = [1.0, 0.82, 0.68, 0.9, 0.75, 0.88]
        for i, face in enumerate(faces):
            sc = shade[i % len(shade)]
            col = (color[0] * sc, color[1] * sc, color[2] * sc)
            for idx in (face[0], face[1], face[2], face[0], face[2], face[3]):
                p = c[idx]
                verts.extend([p[0], p[1], p[2], col[0], col[1], col[2]])

    def resizeGL(self, w: int, h: int) -> None:
        if self._gl_ready and self._gl:
            self._gl.glViewport(0, 0, w, h)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_mouse = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            delta = event.position().toPoint() - self._last_mouse
            self._last_mouse = event.position().toPoint()
            self._yaw += delta.x() * 0.35
            self._pitch = max(48.0, min(72.0, self._pitch - delta.y() * 0.25))
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False

    def wheelEvent(self, event) -> None:
        self._distance = max(board_radius() * 1.4, min(board_radius() * 3.8, self._distance - event.angleDelta().y() * 0.012))
        self.update()
