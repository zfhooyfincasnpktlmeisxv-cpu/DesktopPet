"""
宠物主窗口
透明无边框、流畅动作系统、固定画布防抖动
"""
import logging
import math
import random
import time
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from ..animation import ActionManager, AnimationController
from ..animation.action_state import ActionState
from ..core.animation_manager import AnimationManager
from ..core.skin_manager import SkinManager
from ..core.state_manager import StateManager
from ..ui.speech_bubble import SpeechBubble
from ..ui.stat_hud import hud_height, hud_required_width, paint_stat_hud
from ..utils.blink_overlay import apply_blink_to_pixmap
from ..utils.constants import (
    ANIMATION_IDLE,
    CLICK_THRESHOLD_MS,
    CLICK_THRESHOLD_PX,
    DEFAULT_OPACITY,
    DEFAULT_SCALE,
    FORWARD_LEAN_DEG,
    GLIDE_BODY_SCALE,
    GLIDE_MIRROR_X,
    MOONWALK_LEAN_DEG,
    get_skins_dir,
)
from ..i18n import text_pool

logger = logging.getLogger(__name__)


class PetWindow(QWidget):
    closed = pyqtSignal()
    position_changed = pyqtSignal(int, int)
    stat_hud_changed = pyqtSignal(bool)

    def __init__(
        self,
        pet_id: str,
        skin_name: str = "default",
        auto_walk_enabled: bool = True,
        show_stat_hud: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.pet_id = pet_id
        self.skin_name = skin_name
        self.auto_walk_enabled = auto_walk_enabled
        self._stat_hud_visible = show_stat_hud
        self.scale = DEFAULT_SCALE
        self.opacity = DEFAULT_OPACITY

        self.is_dragging = False
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()
        self.mouse_press_time = 0
        self.mouse_press_pos = QPoint()

        self.skin_mgr = SkinManager()
        self.animation_mgr = AnimationManager(self.skin_mgr, self)
        self.anim_ctrl = AnimationController(self.animation_mgr)
        self.action_mgr = ActionManager(
            self.anim_ctrl,
            auto_walk_enabled=auto_walk_enabled,
            parent=self,
        )
        self.state_mgr = StateManager(self)

        self.bubble: Optional[SpeechBubble] = None
        self._display_pixmap: Optional[QPixmap] = None
        self._display_offset = QPoint(0, 0)
        self._canvas_w = 128
        self._canvas_h = 213
        self._body_offset_x = 0
        self._stat_hud_h = 0
        self._eye_regions: list[tuple[int, int, int, int]] = []

        self._walk_timer = QTimer(self)
        self._walk_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._walk_timer.timeout.connect(self._on_walk_tick)
        self._is_walking = False
        self._walk_dir = 1
        self._walk_speed = 55
        self._walk_target = 200
        self._walk_done = 0
        self._walk_carry = 0.0
        self._walk_tick_ms = 16
        self._walk_bob_phase = 0.0
        self._walk_bob_y = 0
        self._moonwalk_mode = False
        self._forced_glide_dir: Optional[int] = None
        self._forced_glide_dist: Optional[int] = None

        self._game_mode_locked = False
        self._game_mode_saved_pos: Optional[QPoint] = None
        self._game_mode_saved_flags: Optional[int] = None

        self._bubble_cooldown_ms = 45_000
        self._last_bubble_at: Dict[str, float] = {}

        self._init_ui()
        self._init_connections()
        self.set_skin(skin_name)
        self.action_mgr.start()
        self._refresh_display()

        logger.info("宠物 %s 就绪 (auto_walk=%s)", pet_id, auto_walk_enabled)

    def _init_ui(self) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setWindowOpacity(self.opacity)
        self.bubble = SpeechBubble(self)

    def _init_connections(self) -> None:
        self.animation_mgr.frame_updated.connect(lambda _: self._refresh_display())
        self.action_mgr.state_changed.connect(self._on_action_state_changed)
        self.action_mgr.blink_frame_changed.connect(lambda _: self._refresh_display())
        self.state_mgr.state_critical.connect(self._on_state_critical)
        self.state_mgr.hunger_changed.connect(self._on_hunger_changed)
        self.state_mgr.mood_changed.connect(self._on_stat_value_changed)
        self.state_mgr.intimacy_changed.connect(self._on_stat_value_changed)

    def _load_eye_regions(self) -> None:
        from ..utils.blink_overlay import load_eye_specs_from_skin

        skin_dir = get_skins_dir() / self.skin_name
        idle_path = skin_dir / "idle" / "001.png"
        idle_img = None
        if idle_path.exists():
            from PIL import Image
            idle_img = Image.open(idle_path).convert("RGBA")
        specs = load_eye_specs_from_skin(skin_dir, idle_img)
        self._eye_regions = [s.as_tuple() for s in specs]
        if self._eye_regions:
            logger.info("眼位已定位(v2): %s", self._eye_regions)
        else:
            logger.warning("眼位检测失败，眨眼可能不可用")

    def _lock_canvas_size(self, frame: QPixmap) -> None:
        self._canvas_w = max(1, int(frame.width() * self.scale))
        self._canvas_h = max(1, int(frame.height() * self.scale))
        self._apply_window_size()

    def _apply_window_size(self) -> None:
        self._stat_hud_h = hud_height(self.scale) if self._stat_hud_visible else 0
        win_w = self._canvas_w
        if self._stat_hud_visible:
            win_w = max(self._canvas_w, hud_required_width(self.scale))
        self._body_offset_x = max(0, (win_w - self._canvas_w) // 2)
        self.setFixedSize(win_w, self._canvas_h + self._stat_hud_h)

    def is_stat_hud_visible(self) -> bool:
        return self._stat_hud_visible

    def set_stat_hud_visible(self, visible: bool, *, persist: bool = True) -> None:
        visible = bool(visible)
        if self._stat_hud_visible == visible:
            return
        self._stat_hud_visible = visible
        self._apply_window_size()
        self.update()
        if persist:
            self.stat_hud_changed.emit(visible)

    def set_skin(self, skin_name: str) -> None:
        if not self.skin_mgr.has_skin(skin_name):
            skin_name = "default"
        self.skin_name = skin_name
        self.animation_mgr.set_skin(skin_name)
        self._load_eye_regions()
        if self.animation_mgr.load_animation(ANIMATION_IDLE):
            frame = self.animation_mgr.get_current_frame()
            if frame:
                self._lock_canvas_size(frame)
        self.action_mgr.force_idle()
        self._refresh_display()

    def _compose_frame(self) -> Optional[QPixmap]:
        frame = self.animation_mgr.get_current_frame()
        if not frame or frame.isNull():
            return None
        if self.action_mgr.is_blinking:
            frame = apply_blink_to_pixmap(
                frame,
                self.action_mgr.blink_frame,
                eyes=self._eye_regions or None,
            )
        return frame

    def _refresh_display(self) -> None:
        frame = self._compose_frame()
        if not frame or frame.isNull():
            self._display_pixmap = None
            self.update()
            return
        scaled = frame.scaled(
            self._canvas_w,
            self._canvas_h,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._display_pixmap = scaled
        self._display_offset = QPoint(0, 0)
        self.update()

    def paintEvent(self, event) -> None:
        if not self._display_pixmap or self._display_pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        walking = (
            self._is_walking
            and self.action_mgr.current_state == ActionState.WALK
        )
        body_x = self._body_offset_x
        if walking:
            cw, ch = self._canvas_w, self._canvas_h
            lean = MOONWALK_LEAN_DEG if self._moonwalk_mode else FORWARD_LEAN_DEG
            sx = GLIDE_MIRROR_X * GLIDE_BODY_SCALE
            sy = GLIDE_BODY_SCALE
            painter.translate(body_x + cw / 2, ch / 2 + self._walk_bob_y)
            painter.rotate(lean)
            painter.scale(sx, sy)
            painter.translate(-cw / 2, -ch / 2)
        else:
            painter.translate(body_x, 0)

        painter.drawPixmap(self._display_offset, self._display_pixmap)
        painter.resetTransform()

        if self._stat_hud_visible and self._stat_hud_h > 0:
            self._paint_stat_hud(painter)

        painter.end()

    def _paint_stat_hud(self, painter: QPainter) -> None:
        paint_stat_hud(
            painter,
            x=0,
            y=self._canvas_h,
            width=self.width(),
            height=self._stat_hud_h,
            hunger=self.state_mgr.hunger,
            mood=self.state_mgr.mood,
            intimacy=self.state_mgr.intimacy,
            scale=self.scale,
        )

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._refresh_display()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._sync_bubble_position()

    def _sync_bubble_position(self) -> None:
        if self.bubble and self.bubble.is_showing:
            self.bubble.move_above(self.x(), self.y(), self.width())

    def feed(self) -> bool:
        inv = self._get_inventory_manager()
        if inv is None or not inv.consume_feed_item():
            self._show_random_text("no_food", force=True)
            return False
        self.state_mgr.feed()
        self.action_mgr.on_user_interaction()
        self.action_mgr.trigger_eat()
        self._show_random_text("feed")
        return True

    @staticmethod
    def _get_inventory_manager():
        app = QApplication.instance()
        if not app:
            return None
        pet_app = app.property("desktop_pet_app")
        if pet_app is None:
            return None
        return getattr(pet_app, "inventory_mgr", None)

    def pet(self) -> None:
        self.state_mgr.pet()
        self.action_mgr.on_user_interaction()
        self.action_mgr.trigger_happy()
        self._show_random_text("pet")

    def show_bubble_pool(self, pool_name: str, force: bool = True) -> None:
        """对外展示指定文案池的气泡（小游戏结算等）。"""
        self._show_random_text(pool_name, force=force)

    def enter_game_spectator_mode(self) -> None:
        """玩小游戏时：固定到屏幕右侧旁观，禁止拖动与随机走动。"""
        if self._game_mode_locked:
            return
        self._game_mode_locked = True
        self._game_mode_saved_pos = self.pos()
        self._stop_walk()
        self.action_mgr.pause_scheduler()
        self.action_mgr.force_idle()

        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            margin = 16
            x = geo.right() - self.width() - margin
            y = max(geo.top() + margin, geo.center().y() - self.height() // 2)
            self.move(x, y)
            self.position_changed.emit(x, y)

        self._game_mode_saved_flags = self.windowFlags()
        flags = int(self._game_mode_saved_flags)
        flags &= ~int(Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowFlags(Qt.WindowType(flags))
        self.show()
        logger.info("宠物进入小游戏旁观模式")

    def leave_game_spectator_mode(self) -> None:
        """结束小游戏：恢复位置与交互。"""
        if not self._game_mode_locked:
            return
        self._game_mode_locked = False
        if self._game_mode_saved_pos is not None:
            self.move(self._game_mode_saved_pos)
            self.position_changed.emit(self.x(), self.y())
        self._game_mode_saved_pos = None

        if self._game_mode_saved_flags is not None:
            self.setWindowFlags(self._game_mode_saved_flags)
            self._game_mode_saved_flags = None
            self.show()
            self.raise_()

        self.action_mgr.resume_scheduler()
        logger.info("宠物退出小游戏旁观模式")

    def hide_pet(self) -> None:
        if self.bubble:
            self.bubble.dismiss()
        self._display_pixmap = None
        self.update()
        self.hide()

    def shutdown(self) -> None:
        self._shutting_down = True
        self._stop_walk()
        if self.bubble:
            self.bubble.dismiss()
        self.action_mgr.stop()
        self.state_mgr.stop()
        self.animation_mgr.stop()
        if self.bubble:
            self.bubble.close()
            self.bubble = None
        self.close()

    def set_scale(self, scale: float) -> None:
        self.scale = max(0.5, min(2.0, scale))
        frame = self.animation_mgr.get_current_frame()
        if frame:
            self._lock_canvas_size(frame)
        self._refresh_display()

    def set_opacity(self, opacity: float) -> None:
        self.opacity = max(0.3, min(1.0, opacity))
        self.setWindowOpacity(self.opacity)

    def _show_random_text(self, pool_name: str, *, force: bool = False) -> None:
        now = time.monotonic()
        last = self._last_bubble_at.get(pool_name, 0.0)
        if not force and (now - last) * 1000 < self._bubble_cooldown_ms:
            return
        self._last_bubble_at[pool_name] = now
        pool = text_pool(pool_name)
        if pool and self.bubble and self.isVisible():
            self.bubble.show_text(random.choice(pool), style=pool_name)
            self._sync_bubble_position()

    def _on_hunger_changed(self, value: int) -> None:
        if value < 30 and self.action_mgr.current_state == ActionState.IDLE:
            self.action_mgr.request_action(ActionState.SAD)
        if self._stat_hud_visible:
            self.update()

    def _on_stat_value_changed(self, _value: int) -> None:
        if self._stat_hud_visible:
            self.update()

    def _on_state_critical(self, state_type: str) -> None:
        if state_type == "hunger":
            self._show_random_text("hungry")
        elif state_type == "mood":
            self._show_random_text("sad")

    def _on_action_state_changed(self, old: str, new: str) -> None:
        if new == ActionState.WALK:
            self._start_walk()
        elif old == ActionState.WALK:
            self._stop_walk()
        self._refresh_display()

    def _screen_walk_bounds(self) -> tuple[int, int]:
        from PyQt6.QtGui import QGuiApplication

        screen = QGuiApplication.primaryScreen()
        if not screen:
            return 0, 1920 - self.width()
        max_x = screen.geometry().width() - self.width()
        return 0, max(0, max_x)

    def _pick_walk_plan(self) -> tuple[int, int]:
        """随机选方向和步数，偏向空间更大的一侧。"""
        min_x, max_x = self._screen_walk_bounds()
        cur_x = self.x()
        space_left = cur_x - min_x
        space_right = max_x - cur_x

        if random.random() < 0.72:
            direction = 1 if space_right >= space_left else -1
        else:
            direction = random.choice([-1, 1])

        available = space_right if direction > 0 else space_left
        if available < 50:
            direction *= -1
            available = space_left if direction < 0 else space_right

        if available < 30:
            return direction, random.randint(40, 80)

        ratio = random.uniform(0.22, 0.58)
        target = int(available * ratio)
        target = max(60, min(260, target))
        if random.random() < 0.12:
            target = min(int(available * 0.75), random.randint(200, 340))
        return direction, target

    def debug_glide_forward(self) -> None:
        self._trigger_debug_glide(direction=1)

    def debug_glide_backward(self) -> None:
        self._trigger_debug_glide(direction=-1)

    def debug_stop_glide(self) -> None:
        if self._is_walking:
            self._finish_walk(schedule_next=False)
        elif self.action_mgr.current_state == ActionState.WALK:
            self.action_mgr.force_idle()

    def _trigger_debug_glide(self, *, direction: int) -> None:
        if self._is_walking:
            self._finish_walk(schedule_next=False)
        self.action_mgr.on_user_interaction()
        self._forced_glide_dir = direction
        self._forced_glide_dist = 220
        self.action_mgr.request_action(ActionState.WALK)

    def _start_walk(self) -> None:
        if self._is_walking:
            return
        cfg = self.action_mgr._config.get_anim_config(ActionState.WALK)
        self._walk_speed = int(cfg.get("speed_px_per_sec", 50))
        if self._forced_glide_dir is not None:
            self._walk_dir = self._forced_glide_dir
            self._walk_target = self._forced_glide_dist or 220
            self._forced_glide_dir = None
            self._forced_glide_dist = None
        else:
            self._walk_dir, self._walk_target = self._pick_walk_plan()
        self._walk_done = 0
        self._walk_carry = 0.0
        self._walk_bob_phase = 0.0
        self._walk_bob_y = 0
        self._is_walking = True

        self._moonwalk_mode = self._walk_dir < 0
        # 滑翔统一用待机立绘，避免 hover 帧人物偏大
        self.anim_ctrl.show_static_frame("idle", 0)
        if self._moonwalk_mode:
            self._walk_speed = max(28, int(self._walk_speed * 0.82))
            logger.info("倒着飞（月球漫步）")
        else:
            self._walk_speed = max(32, int(self._walk_speed * 0.88))
            logger.info("正着飞（朝前滑翔）")

        self._walk_timer.start(self._walk_tick_ms)
        logger.info(
            "开始移动: dir=%s 目标=%spx 速度=%spx/s 倒着=%s",
            self._walk_dir,
            self._walk_target,
            self._walk_speed,
            self._moonwalk_mode,
        )

    def _stop_walk(self) -> None:
        self._is_walking = False
        self._moonwalk_mode = False
        self._walk_bob_y = 0
        self._walk_timer.stop()

    def _update_walk_bob(self) -> None:
        self._walk_bob_phase += 0.15
        if self._moonwalk_mode:
            self._walk_bob_y = int(-7 + math.sin(self._walk_bob_phase) * 9)
        else:
            self._walk_bob_y = int(-5 + math.sin(self._walk_bob_phase) * 8)

    def _finish_walk(self, *, schedule_next: bool = True) -> None:
        self._stop_walk()
        if self.action_mgr.current_state == ActionState.WALK:
            self.action_mgr.request_action(ActionState.IDLE)
        if schedule_next:
            self.action_mgr.notify_walk_finished()

    def _on_walk_tick(self) -> None:
        if not self._is_walking:
            return
        dt = self._walk_tick_ms / 1000.0
        self._walk_carry += self._walk_speed * dt
        step = int(self._walk_carry)
        if step <= 0:
            return
        self._walk_carry -= step
        delta = step * self._walk_dir
        nx = self.x() + delta

        min_x, max_x = self._screen_walk_bounds()
        if nx <= min_x or nx >= max_x:
            nx = max(min_x, min(nx, max_x))
            self.move(nx, self.y())
            self.position_changed.emit(nx, self.y())
            self._finish_walk()
            return

        self.move(nx, self.y())
        self.position_changed.emit(nx, self.y())
        self._walk_done += step
        self._update_walk_bob()
        self.update()
        if self._walk_done >= self._walk_target:
            self._finish_walk()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._game_mode_locked:
            if event.button() == Qt.MouseButton.RightButton:
                from .context_menu import ContextMenu
                menu = ContextMenu(parent=None, pet_window=self)
                menu.update_sleep_state(self.action_mgr.is_sleeping)
                menu.update_stat_hud_state(self.is_stat_hud_visible())
                inv = self._get_inventory_manager()
                food = inv.feed_food_count() if inv else 0
                menu.update_inventory_state(food, self.action_mgr.is_sleeping)
                menu.exec(event.globalPosition().toPoint())
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse_press_time = event.timestamp()
            self.mouse_press_pos = event.globalPosition().toPoint()
            self.drag_start_pos = self.mouse_press_pos
            self.window_start_pos = self.pos()
            self.is_dragging = False
            if self._is_walking:
                self._finish_walk(schedule_next=False)
            self.action_mgr.on_user_interaction()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._game_mode_locked:
            event.accept()
            return
        if event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            if delta.manhattanLength() >= CLICK_THRESHOLD_PX:
                self.move(self.window_start_pos + delta)
                self.is_dragging = True
                self.position_changed.emit(self.x(), self.y())
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._game_mode_locked:
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            dt = event.timestamp() - self.mouse_press_time
            dist = (event.globalPosition().toPoint() - self.mouse_press_pos).manhattanLength()
            if not self.is_dragging and dt < CLICK_THRESHOLD_MS and dist < CLICK_THRESHOLD_PX:
                self._handle_click()
            elif self.is_dragging:
                self.action_mgr.on_user_interaction()
            self.is_dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            from .context_menu import ContextMenu
            menu = ContextMenu(parent=None, pet_window=self)
            menu.update_sleep_state(self.action_mgr.is_sleeping)
            menu.update_stat_hud_state(self.is_stat_hud_visible())
            inv = self._get_inventory_manager()
            food = inv.feed_food_count() if inv else 0
            menu.update_inventory_state(food, self.action_mgr.is_sleeping)
            menu.exec(event.globalPosition().toPoint())
            event.accept()

    def _handle_click(self) -> None:
        self.action_mgr.on_user_interaction()
        self.state_mgr.pet()
        self._show_random_text(self.state_mgr.get_mood_text())
        self.action_mgr.request_action(ActionState.CLICK)

    def closeEvent(self, event) -> None:
        if self.bubble:
            self.bubble.dismiss()
        if getattr(self, "_shutting_down", False):
            event.accept()
            return
        self.hide()
        self.closed.emit()
        event.ignore()

    def get_pet_data(self) -> Dict:
        return {
            "id": self.pet_id,
            "skin_name": self.skin_name,
            "x": self.x(),
            "y": self.y(),
            "scale": self.scale,
            "hunger": self.state_mgr.hunger,
            "mood": self.state_mgr.mood,
            "intimacy": self.state_mgr.intimacy,
            "is_visible": self.isVisible(),
        }

    def restore_state(self, data: Dict) -> None:
        self.move(data.get("x", 100), data.get("y", 100))
        self.set_skin(data.get("skin_name", "default"))
        self.set_scale(data.get("scale", DEFAULT_SCALE))
        self.state_mgr.set_state(
            data.get("hunger", 100),
            data.get("mood", 100),
            data.get("intimacy", 0),
        )
        if data.get("is_visible", True):
            self.show()
            self.raise_()
        else:
            self.hide()

    def apply_settings(self, settings) -> None:
        """Apply persisted settings (language, HUD, opacity, auto-walk)."""
        self.auto_walk_enabled = bool(settings.auto_walk_enabled)
        self.action_mgr.set_auto_walk_enabled(self.auto_walk_enabled)
        self.set_opacity(float(settings.opacity))
        self.set_stat_hud_visible(bool(settings.show_stat_hud), persist=False)
