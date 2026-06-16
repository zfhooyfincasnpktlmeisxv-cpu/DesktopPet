"""
动画管理器
负责帧动画播放、状态切换、定时器控制、帧率调整
"""
import logging
from typing import List, Optional

from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel

from .skin_manager import SkinManager
from ..utils.constants import ANIMATION_IDLE, DEFAULT_FPS

logger = logging.getLogger(__name__)


class AnimationManager(QObject):
    """
    动画管理器
    控制宠物动画的播放、暂停、帧切换
    """

    # 信号定义（必须在类体中，方法之前）
    animation_finished = pyqtSignal(str)  # 动画播放完成信号
    frame_updated = pyqtSignal(int)       # 帧更新信号，参数为帧索引

    def __init__(self, skin_manager: SkinManager, parent: Optional[QObject] = None):
        """
        初始化动画管理器

        Args:
            skin_manager: 皮肤管理器实例
            parent: 父对象
        """
        super().__init__(parent)

        self.skin_mgr = skin_manager
        self.skin_name: str = "default"

        # 动画帧数据
        self.frames: List[QPixmap] = []  # 当前动画的帧列表
        self.current_frame_index: int = 0
        self.current_animation: str = ""

        # 定时器（PreciseTimer 减少帧间抖动）
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._next_frame)

        # 帧率
        self.fps: int = DEFAULT_FPS
        self.interval: int = int(1000 / self.fps)  # 毫秒

        # 播放状态
        self.is_playing: bool = False
        self.loop: bool = True  # 是否循环播放
        self.ping_pong: bool = False
        self._frame_step: int = 1

        logger.info("动画管理器初始化完成")

    def load_animation(self, anim_name: str) -> bool:
        """
        加载指定动画的帧数据

        Args:
            anim_name: 动画名称

        Returns:
            是否加载成功
        """
        # 检查皮肤是否有该动画
        if not self.skin_mgr.has_animation(self.skin_name, anim_name):
            logger.debug(f"皮肤 '{self.skin_name}' 没有动画 '{anim_name}'")
            return False

        # 加载帧
        qimages = self.skin_mgr.load_animation_frames(self.skin_name, anim_name)

        if not qimages:
            logger.warning(f"动画 '{anim_name}' 没有帧")
            return False

        # 转换为QPixmap
        self.frames = [QPixmap.fromImage(img) for img in qimages]
        self.current_animation = anim_name
        self.current_frame_index = 0

        logger.info(f"加载动画 '{anim_name}': {len(self.frames)} 帧")
        return True

    def show_static_frame(self, anim_name: str, frame_index: int = 0) -> bool:
        """加载动画但只显示单帧，不启动定时器（用于待机立绘）"""
        self.stop()
        if not self.load_animation(anim_name):
            return False
        if not self.frames:
            return False
        idx = max(0, min(frame_index, len(self.frames) - 1))
        self.frames = [self.frames[idx]]
        self.current_frame_index = 0
        self.current_animation = anim_name
        self.is_playing = False
        self.loop = True
        self.ping_pong = False
        self.frame_updated.emit(0)
        return True

    def play(self, anim_name: str, loop: bool = True, ping_pong: bool = False) -> bool:
        """
        播放指定动画

        Args:
            anim_name: 动画名称
            loop: 是否循环播放
            ping_pong: 往返循环（适合待机呼吸，避免首尾跳变）
        """
        if self.is_playing and self.current_animation == anim_name and self.loop == loop and self.ping_pong == (ping_pong and loop):
            logger.debug(f"动画 '{anim_name}' 已在播放")
            return True

        # 如果正在播放非循环动画且被打断，先发出完成信号
        if self.is_playing and not self.loop and self.current_animation:
            interrupted_anim = self.current_animation
            self.stop()
            self.animation_finished.emit(interrupted_anim)
            logger.debug(f"动画 '{interrupted_anim}' 被打断，发出完成信号")

        # 加载动画
        if not self.load_animation(anim_name):
            # 加载失败，尝试播放idle
            if anim_name != ANIMATION_IDLE:
                logger.warning(f"播放动画 '{anim_name}' 失败，尝试播放idle")
                return self.play(ANIMATION_IDLE, loop=True)
            return False

        # 设置循环
        self.loop = loop
        self.ping_pong = bool(ping_pong and loop and len(self.frames) > 1)
        self._frame_step = 1

        # 开始播放
        self.current_frame_index = 0
        self.is_playing = True
        self.timer.start(self.interval)
        self.frame_updated.emit(0)

        logger.debug(f"开始播放动画: {anim_name} (FPS: {self.fps})")
        return True

    def stop(self) -> None:
        """停止动画播放"""
        if self.is_playing:
            self.timer.stop()
            self.is_playing = False
            logger.debug("动画已停止")

    def pause(self) -> None:
        """暂停动画播放"""
        if self.is_playing:
            self.timer.stop()
            logger.debug("动画已暂停")

    def resume(self) -> None:
        """恢复动画播放"""
        if not self.is_playing and self.frames:
            self.timer.start(self.interval)
            self.is_playing = True
            logger.debug("动画已恢复")

    def _next_frame(self) -> None:
        """切换到下一帧"""
        if not self.frames:
            return

        if self.ping_pong:
            next_index = self.current_frame_index + self._frame_step
            if next_index >= len(self.frames):
                self._frame_step = -1
                next_index = len(self.frames) - 2
            elif next_index < 0:
                self._frame_step = 1
                next_index = 1 if len(self.frames) > 1 else 0
            self.current_frame_index = next_index
            self.frame_updated.emit(self.current_frame_index)
            return

        # 更新帧索引
        self.current_frame_index += 1

        # 检查是否播放完成
        if self.current_frame_index >= len(self.frames):
            if self.loop:
                # 循环播放，回到第一帧
                self.current_frame_index = 0
            else:
                # 不循环，停止在最后一帧
                self.current_frame_index = len(self.frames) - 1
                self.stop()
                self.animation_finished.emit(self.current_animation)
                logger.debug(f"动画 '{self.current_animation}' 播放完成")
                return

        # 发射帧更新信号（通过当前帧索引）
        self.frame_updated.emit(self.current_frame_index)

    def get_current_frame(self) -> Optional[QPixmap]:
        """
        获取当前帧的QPixmap

        Returns:
            当前帧的QPixmap，如果没有则返回None
        """
        if not self.frames or self.current_frame_index >= len(self.frames):
            return None

        return self.frames[self.current_frame_index]

    def get_current_frame_index(self) -> int:
        """
        获取当前帧索引

        Returns:
            当前帧索引
        """
        return self.current_frame_index

    def get_frame_count(self) -> int:
        """
        获取当前动画的总帧数

        Returns:
            总帧数
        """
        return len(self.frames)

    def set_fps(self, fps: int) -> None:
        """
        设置帧率

        Args:
            fps: 帧率（FPS）
        """
        if fps < 1:
            fps = 1
        elif fps > 60:
            fps = 60

        self.fps = fps
        self.interval = int(1000 / fps)

        # 如果正在播放，重新启动定时器
        if self.is_playing:
            self.timer.stop()
            self.timer.start(self.interval)

        logger.debug(f"帧率已设置为: {fps} FPS")

    def set_skin(self, skin_name: str) -> None:
        """
        设置当前皮肤

        Args:
            skin_name: 皮肤名称
        """
        self.skin_name = skin_name
        logger.debug(f"皮肤已设置为: {skin_name}")

    def has_animation(self, anim_name: str) -> bool:
        """
        检查当前皮肤是否有指定动画

        Args:
            anim_name: 动画名称

        Returns:
            是否存在
        """
        return self.skin_mgr.has_animation(self.skin_name, anim_name)
