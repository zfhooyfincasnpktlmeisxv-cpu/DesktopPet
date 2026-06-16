"""经典方形 2.5D 棋盘 — 四边平铺，文字横排"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget

from ...utils.constants import RICHMAN_PACE
from .board_data import all_tiles
from .board_fx import RichmanBoardFxOverlay
from .game_engine import GamePhase, RichmanEngine
from .h5_board_style import (
    PLAYER_COLORS,
    draw_board_tray,
    draw_center_field,
    draw_forest_background,
    draw_h5_tile,
    draw_h5_token,
)
from .city_images import ensure_city_images
from .iso_board_layout import center_rect, tile_cell_size, tile_paint_order, tile_screen_pos
from .movement_anim import StepHopAnimator, hop_arc, smoothstep
from .player_avatars import load_avatar_pixmap


@dataclass
class _ActiveHop:
    player_id: int
    from_tile: int
    to_tile: int
    t: float = 0.0


class RichmanPainterViewport(QWidget):
    """中间棋盘：经典方形大富翁，右侧 UI 不变。"""

    def __init__(self, engine: RichmanEngine, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._settled: Dict[int, int] = {}
        self._active_hop: Optional[_ActiveHop] = None
        self._hop_queue: Dict[int, list[int]] = {}
        self._zoom = 1.0
        self._drag = False
        self._last = QPoint()
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._hop = StepHopAnimator(self, duration_ms=int(RICHMAN_PACE["step_hop_ms"]), hop_peak=10.0)
        self._engine.state_changed.connect(self.update)
        self._engine.phase_changed.connect(lambda _: self.update())
        self._engine.player_stepped.connect(self._on_player_stepped)
        self._engine.player_moved.connect(self._on_player_moved)
        self.setMinimumSize(520, 520)
        ensure_city_images()
        self._fx = RichmanBoardFxOverlay(self)
        self._fx.raise_()
        self._sync_tokens()

    def sync_player_token(self, player_id: int) -> None:
        """移动结算后对齐棋子落点，避免与引擎坐标错位。"""
        self._hop_queue.pop(player_id, None)
        if self._active_hop and self._active_hop.player_id == player_id:
            self._hop.cancel()
            self._active_hop = None
        for p in self._engine.players():
            if p.id == player_id:
                self._settled[player_id] = p.position
                break
        self.update()

    def play_fx(self, event: str, tile_index: Optional[int] = None) -> None:
        idx = tile_index if tile_index is not None else self._engine.current_player.position
        x, y = self._tile_pos(idx)
        if event == "dice":
            self._fx.shake(5.0, 0.28)
            self._fx.burst(x, y, QColor(255, 255, 255), count=12, spread=3.5)
        elif event == "dice_land":
            pass  # 逐格移动时不叠光晕，避免像第二个棋子
        elif event == "buy":
            self._fx.burst(x, y, QColor(255, 210, 80), count=22, spread=5.0)
            self._fx.tile_glow(x, y)
            self._fx.flash(QColor(255, 220, 120), 0.22)
        elif event == "build":
            self._fx.burst(x, y, QColor(120, 220, 255), count=16, spread=4.0)
            self._fx.tile_glow(x, y)
        elif event == "card":
            self._fx.flash(QColor(255, 198, 120), 0.32)
            self._fx.burst(x, y, QColor(255, 180, 100), count=20, spread=4.5)
        elif event == "pass_start":
            self._fx.burst(x, y, QColor(72, 220, 160), count=18, spread=4.2)
            self._fx.tile_glow(x, y)
        elif event == "rent":
            self._fx.flash(QColor(255, 100, 120), 0.25)
            self._fx.burst(x, y, QColor(255, 120, 150), count=14, spread=3.8)
        elif event == "tax":
            self._fx.flash(QColor(255, 120, 100), 0.28)
        elif event == "jail":
            self._fx.flash(QColor(140, 150, 190), 0.35)
            self._fx.shake(8.0, 0.4)
        elif event == "win":
            self._fx.confetti()

    def _fit_zoom(self) -> float:
        base = min(self.width(), self.height()) / 560.0
        return self._zoom * max(0.82, min(1.15, base))

    def _board_center(self) -> Tuple[float, float]:
        return self.width() / 2 + self._pan_x, self.height() / 2 + self._pan_y

    def _tile_pos(self, index: int) -> Tuple[float, float]:
        cx, cy = self._board_center()
        z = self._fit_zoom()
        return tile_screen_pos(index, cx, cy, z, self.width(), self.height())

    def _sync_tokens(self) -> None:
        for p in self._engine.players():
            if self._active_hop and self._active_hop.player_id == p.id and self._hop.is_running():
                continue
            self._settled[p.id] = p.position

    def _token_screen_pos(self, player_id: int) -> Tuple[float, float]:
        hop = self._active_hop
        if hop and hop.player_id == player_id:
            if hop.t < 1.0:
                fx, fy = self._tile_pos(hop.from_tile)
                tx, ty = self._tile_pos(hop.to_tile)
                e = smoothstep(hop.t)
                x = fx + (tx - fx) * e
                y = fy + (ty - fy) * e + hop_arc(hop.t, 10.0)
                return x, y
            return self._tile_pos(hop.to_tile)

        tile = self._settled.get(player_id)
        if tile is None:
            for p in self._engine.players():
                if p.id == player_id:
                    tile = p.position
                    break
        if tile is None:
            tile = 0
        return self._tile_pos(tile)

    def _start_token_hop(self, player_id: int, to_tile: int) -> None:
        from_tile = self._settled.get(player_id, to_tile)
        if self._active_hop and self._active_hop.player_id == player_id:
            from_tile = self._active_hop.to_tile

        if from_tile == to_tile:
            self._settled[player_id] = to_tile
            self.update()
            return

        self._hop.cancel()
        self._active_hop = _ActiveHop(player_id, from_tile, to_tile, 0.0)
        self._hop.start(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            self._on_hop_frame,
            self._on_hop_done,
        )

    def _on_player_stepped(self, player_id: int, tile_index: int) -> None:
        if (
            self._active_hop
            and self._active_hop.player_id == player_id
            and self._hop.is_running()
        ):
            q = self._hop_queue.setdefault(player_id, [])
            if not q or q[-1] != tile_index:
                q.append(tile_index)
            return
        self._start_token_hop(player_id, tile_index)

    def _on_player_moved(self, player_id: int, tile_index: int) -> None:
        """卡面/传送/进监狱等瞬移 — 不干扰已在终点或正在跳的格。"""
        hop = self._active_hop
        if hop and hop.player_id == player_id:
            if hop.to_tile == tile_index:
                return
            if self._hop.is_running():
                self._settled[player_id] = hop.to_tile
        else:
            settled = self._settled.get(player_id)
            if settled == tile_index and not self._hop_queue.get(player_id):
                return

        self._hop_queue.pop(player_id, None)
        self._hop.cancel()
        self._active_hop = None
        self._start_token_hop(player_id, tile_index)

    def _on_hop_frame(self, pos: Tuple[float, float, float]) -> None:
        if self._active_hop:
            self._active_hop.t = pos[0]
        self.update()

    def _on_hop_done(self) -> None:
        if not self._active_hop:
            self.update()
            return

        player_id = self._active_hop.player_id
        self._settled[player_id] = self._active_hop.to_tile
        self._active_hop = None

        pending = self._hop_queue.get(player_id, [])
        if pending:
            next_tile = pending.pop(0)
            if not pending:
                self._hop_queue.pop(player_id, None)
            self._start_token_hop(player_id, next_tile)
            return

        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        ox, oy = self._fx.shake_offset()
        if ox or oy:
            p.translate(ox, oy)

        draw_forest_background(p, self.width(), self.height())

        cx, cy = self._board_center()
        z = self._fit_zoom()
        cell, gap = tile_cell_size(cx, cy, z, self.width(), self.height())
        stride = cell + gap
        board_w = stride * 7 - gap
        board_h = stride * 7 - gap
        tray_x = cx - board_w / 2 - 8
        tray_y = cy - board_h / 2 - 8
        draw_board_tray(p, tray_x, tray_y, board_w + 16, board_h + 16)

        fx, fy, fw, fh = center_rect(cx, cy, z, self.width(), self.height())
        draw_center_field(p, fx, fy, fw, fh, self._engine.turn_number)

        cp_pos = None
        cp_id = None
        if self._engine.players() and self._engine.phase != GamePhase.GAME_OVER:
            cp = self._engine.current_player
            cp_pos = cp.position
            cp_id = cp.id

        ordered = sorted(all_tiles(), key=lambda t: tile_paint_order(t.index))
        players = {pl.id: pl for pl in self._engine.players()}
        for tile in ordered:
            sx, sy = self._tile_pos(tile.index)
            prop = self._engine.property_at(tile.index)
            owner_col = None
            owner_name = ""
            if prop.owner_id is not None:
                owner_col = PLAYER_COLORS[prop.owner_id % len(PLAYER_COLORS)]
                owner_name = players[prop.owner_id].name if prop.owner_id in players else ""
            draw_h5_tile(
                p,
                sx,
                sy,
                tile,
                cell=cell,
                owned=prop.owner_id is not None,
                level=prop.level,
                owner_color=owner_col,
                owner_name=owner_name,
                highlight=tile.index == cp_pos,
            )

        token_r = max(16.0, cell * 0.28)
        for pl in self._engine.players():
            if pl.bankrupt:
                continue
            pos = self._token_screen_pos(pl.id)
            col = PLAYER_COLORS[pl.id % len(PLAYER_COLORS)]
            avatar_pm = load_avatar_pixmap(pl.avatar_id, pl.avatar_path, int(token_r * 2))
            draw_h5_token(
                p,
                pos[0],
                pos[1] - token_r * 0.35,
                col,
                pl.name,
                is_current=pl.id == cp_id,
                size=token_r * 2,
                avatar=avatar_pm,
            )

        p.setPen(QColor(255, 255, 255, 200))
        p.setFont(QFont("Microsoft YaHei UI", 9))
        p.drawText(10, self.height() - 8, "方形棋盘 · 滚轮缩放 · 左键拖移")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fx.setGeometry(self.rect())
        self._sync_tokens()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = True
            self._last = event.position().toPoint()

    def mouseMoveEvent(self, event) -> None:
        if self._drag:
            d = event.position().toPoint() - self._last
            self._last = event.position().toPoint()
            self._pan_x += d.x()
            self._pan_y += d.y()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = False

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        self._zoom = max(0.8, min(1.25, self._zoom + delta * 0.0006))
        self.update()
