"""
皮肤管理器
负责扫描skins目录、加载PNG序列、获取可用皮肤列表
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image
from PyQt6.QtGui import QImage

from ..utils.constants import ANIMATIONS, DEFAULT_SKIN, get_skins_dir
from ..utils.frame_normalize import normalize_animation_frames

logger = logging.getLogger(__name__)

# 睡眠目录部分 PNG 为未切分的精灵图（含多个角色），按 bbox 高度过滤
_SLEEP_MAX_BBOX_HEIGHT = 115


class SkinManager:
    """
    皮肤管理器
    扫描skins目录，加载和管理皮肤资源
    """

    def __init__(self, skins_base_path: Optional[Path] = None):
        """
        初始化皮肤管理器

        Args:
            skins_base_path: 皮肤根目录路径，如果为None则使用默认路径
        """
        self.skins_base_path = skins_base_path or get_skins_dir()
        self.available_skins: List[str] = []
        self.skin_data: Dict[str, Dict[str, List[str]]] = {}  # {skin_name: {anim_name: [frame_paths]}}

        # 确保皮肤目录存在
        self.skins_base_path.mkdir(parents=True, exist_ok=True)

        # 自动扫描皮肤
        self.scan_skins()

    def scan_skins(self) -> List[str]:
        """
        扫描skins目录，获取所有可用皮肤

        Returns:
            可用皮肤名称列表
        """
        self.available_skins = []
        self.skin_data = {}

        if not self.skins_base_path.exists():
            logger.warning(f"皮肤目录不存在: {self.skins_base_path}")
            return []

        # 遍历skins目录下的所有子目录
        for skin_dir in self.skins_base_path.iterdir():
            if not skin_dir.is_dir():
                continue

            skin_name = skin_dir.name
            logger.info(f"发现皮肤: {skin_name}")

            # 扫描该皮肤下的动画目录
            animations = {}
            for anim_dir in skin_dir.iterdir():
                if not anim_dir.is_dir():
                    continue

                anim_name = anim_dir.name
                # 加载该动画下的PNG序列
                frames = self._scan_frames(anim_dir)

                if frames:
                    animations[anim_name] = frames
                    logger.debug(f"  动画 '{anim_name}': {len(frames)} 帧")

            if animations:
                self.available_skins.append(skin_name)
                self.skin_data[skin_name] = animations

        logger.info(f"扫描完成，找到 {len(self.available_skins)} 个皮肤")
        return self.available_skins

    def _scan_frames(self, anim_dir: Path) -> List[str]:
        """
        扫描动画目录下的PNG序列文件

        Args:
            anim_dir: 动画目录路径

        Returns:
            按文件名排序的PNG文件路径列表
        """
        frames = []

        if not anim_dir.exists():
            return frames

        # 获取所有PNG文件
        for file_path in anim_dir.glob("*.png"):
            if file_path.is_file():
                frames.append(str(file_path))

        # 按文件名排序（数字顺序）
        frames.sort(key=self._extract_frame_number)

        return frames

    @staticmethod
    def _extract_frame_number(file_path: str) -> int:
        """
        从文件名中提取帧编号
        支持格式: 001.png, 002.png, frame_001.png 等

        Args:
            file_path: 文件路径

        Returns:
            帧编号，如果无法提取则返回0
        """
        import re
        import os

        filename = os.path.basename(file_path)
        # 查找文件名中的数字
        numbers = re.findall(r'\d+', filename)

        if numbers:
            return int(numbers[-1])  # 使用最后一组数字

        return 0

    def load_skin(self, skin_name: str) -> bool:
        """
        加载指定皮肤

        Args:
            skin_name: 皮肤名称

        Returns:
            是否加载成功
        """
        if skin_name not in self.skin_data:
            logger.warning(f"皮肤不存在: {skin_name}")
            return False

        logger.info(f"加载皮肤: {skin_name}")
        return True

    def get_available_skins(self) -> List[str]:
        """
        获取可用皮肤列表

        Returns:
            皮肤名称列表
        """
        return self.available_skins.copy()

    def has_skin(self, skin_name: str) -> bool:
        """
        检查是否有指定皮肤

        Args:
            skin_name: 皮肤名称

        Returns:
            是否存在
        """
        return skin_name in self.skin_data

    def get_animation_frames(self, skin_name: str, anim_name: str) -> List[str]:
        """
        获取指定皮肤和动画的帧文件路径列表

        Args:
            skin_name: 皮肤名称
            anim_name: 动画名称

        Returns:
            帧文件路径列表
        """
        if skin_name not in self.skin_data:
            logger.warning(f"皮肤不存在: {skin_name}")
            return []

        if anim_name not in self.skin_data[skin_name]:
            logger.debug(f"动画不存在: {skin_name}/{anim_name}")
            return []

        return self.skin_data[skin_name][anim_name].copy()

    def has_animation(self, skin_name: str, anim_name: str) -> bool:
        """
        检查指定皮肤是否有指定动画

        Args:
            skin_name: 皮肤名称
            anim_name: 动画名称

        Returns:
            是否存在
        """
        if skin_name not in self.skin_data:
            return False

        return anim_name in self.skin_data[skin_name]

    def load_frame_image(self, frame_path: str) -> Optional[QImage]:
        """
        加载单帧图片为QImage

        Args:
            frame_path: 帧文件路径

        Returns:
            QImage对象，失败返回None
        """
        try:
            from PIL import Image
            from PIL.ImageQt import ImageQt

            pil_image = Image.open(frame_path).convert("RGBA")
            qimage = ImageQt(pil_image)
            if qimage.isNull():
                logger.error(f"QImage加载失败: {frame_path}")
                return None
            return qimage.copy()

        except Exception as e:
            logger.error(f"加载帧图片失败: {frame_path}, 错误: {e}")
            return None

    def load_animation_frames(self, skin_name: str, anim_name: str) -> List[QImage]:
        """
        加载指定动画的所有帧为QImage列表

        Args:
            skin_name: 皮肤名称
            anim_name: 动画名称

        Returns:
            QImage对象列表
        """
        frame_paths = self.get_animation_frames(skin_name, anim_name)
        pil_frames: List[Image.Image] = []

        for frame_path in frame_paths:
            try:
                pil_frames.append(Image.open(frame_path).convert("RGBA"))
            except OSError as e:
                logger.error("加载帧图片失败: %s, 错误: %s", frame_path, e)

        if anim_name == "sleep" and pil_frames:
            canvas_size = self._reference_canvas_size(skin_name, pil_frames[0].size)
            before = len(pil_frames)
            pil_frames = normalize_animation_frames(
                pil_frames,
                canvas_size,
                max_bbox_height=_SLEEP_MAX_BBOX_HEIGHT,
            )
            dropped = before - len(pil_frames)
            if dropped:
                logger.info(
                    "睡眠动画已过滤 %d 张精灵图脏帧，保留 %d 帧",
                    dropped,
                    len(pil_frames),
                )

        from PIL.ImageQt import ImageQt

        frames: List[QImage] = []
        for pil in pil_frames:
            qimage = ImageQt(pil)
            if qimage.isNull():
                continue
            frames.append(qimage.copy())

        logger.info("加载动画 '%s/%s': %d 帧", skin_name, anim_name, len(frames))
        return frames

    def _reference_canvas_size(
        self, skin_name: str, fallback: Tuple[int, int]
    ) -> Tuple[int, int]:
        idle_paths = self.get_animation_frames(skin_name, "idle")
        if idle_paths:
            try:
                with Image.open(idle_paths[0]) as ref:
                    return ref.size
            except OSError:
                pass
        return fallback

    def create_placeholder_skin(self, skin_name: str = DEFAULT_SKIN) -> bool:
        """
        创建占位皮肤（用于测试）

        Args:
            skin_name: 皮肤名称

        Returns:
            是否创建成功
        """
        import math

        skin_dir = self.skins_base_path / skin_name
        idle_dir = skin_dir / "idle"
        idle_dir.mkdir(parents=True, exist_ok=True)

        # 生成3帧占位图片（简单的圆形图案）
        for i in range(1, 4):
            img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))  # 透明背景

            # 绘制圆形（使用Pillow的ImageDraw）
            from PIL import ImageDraw

            draw = ImageDraw.Draw(img)

            # 根据帧数稍微改变颜色
            colors = [
                (255, 100, 100, 255),  # 红色
                (100, 255, 100, 255),  # 绿色
                (100, 100, 255, 255),  # 蓝色
            ]
            color = colors[i - 1]

            # 绘制圆形身体
            draw.ellipse([20, 20, 108, 108], fill=color)

            # 绘制眼睛
            draw.ellipse([45, 45, 55, 55], fill=(0, 0, 0, 255))
            draw.ellipse([73, 45, 83, 55], fill=(0, 0, 0, 255))

            # 绘制嘴巴（根据帧数变化）
            if i == 1:
                # 正常嘴巴
                draw.arc([50, 60, 78, 85], start=0, end=180, fill=(0, 0, 0, 255), width=2)
            elif i == 2:
                # 微笑
                draw.arc([50, 55, 78, 80], start=0, end=180, fill=(0, 0, 0, 255), width=2)
            else:
                # 张嘴
                draw.ellipse([58, 65, 70, 78], fill=(0, 0, 0, 255))

            # 保存
            frame_path = idle_dir / f"{i:03d}.png"
            img.save(frame_path)
            logger.info(f"创建占位帧: {frame_path}")

        logger.info(f"占位皮肤创建完成: {skin_name}")
        return True
