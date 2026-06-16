"""
数据持久化模块
负责Settings和PetData的JSON读写
"""
import json
import logging
import time
import uuid
from dataclasses import dataclass, asdict, field, MISSING
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..utils.constants import (
    SETTINGS_FIELDS,
    PET_DATA_FIELDS,
    SETTINGS_FILE,
    PETS_FILE,
    DEFAULT_SCALE,
    DEFAULT_GOLD,
    HUNGER_DECAY_PER_MINUTE,
    MOOD_DECAY_PER_MINUTE,
    get_config_dir,
)
from ..utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    """应用设置数据类"""
    scale: float = DEFAULT_SCALE
    fps: int = 10
    opacity: float = 1.0
    hunger_decay_rate: float = HUNGER_DECAY_PER_MINUTE
    mood_decay_rate: float = MOOD_DECAY_PER_MINUTE
    intimacy_threshold: int = 10
    max_pets: int = 5
    auto_run_enabled: bool = False
    auto_walk_enabled: bool = True
    show_stat_hud: bool = False
    language: str = "en"
    gold: int = DEFAULT_GOLD
    inventory: Dict[str, int] = field(default_factory=dict)
    daily_gold_earned: int = 0
    daily_reset_date: str = ""
    game_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    default_skin: str = "default"
    text_pools: Dict[str, List[str]] = field(default_factory=lambda: {
        "happy": ["你好呀！", "今天真开心~", "主人来陪我玩吧！", "嘿嘿～", "☀️"],
        "hungry": ["我饿了...", "想吃好吃的！", "🍖"],
        "sad": ["心情不好...", "摸摸我好不好？", "😢"],
        "normal": ["喵～", "我在哦～", "有什么事吗？", "✨"],
        "feed": ["好吃！", "谢谢主人！", "饱饱的～", "🍪", "❤️"],
        "pet": ["舒服～", "再摸摸～", "❤️", "开心！"],
    })

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """从字典创建实例"""
        # 过滤掉不在数据类字段中的键
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        for field_name, field_obj in cls.__dataclass_fields__.items():
            if field_name in filtered_data:
                continue
            if field_obj.default_factory is not MISSING and field_obj.default_factory is not None:
                filtered_data[field_name] = field_obj.default_factory()
            elif field_obj.default is not MISSING:
                filtered_data[field_name] = field_obj.default

        if "gold" in filtered_data:
            filtered_data["gold"] = max(0, int(filtered_data["gold"]))
        if "inventory" in filtered_data and isinstance(filtered_data["inventory"], dict):
            filtered_data["inventory"] = {
                str(k): max(0, int(v))
                for k, v in filtered_data["inventory"].items()
                if int(v) > 0
            }
        else:
            filtered_data.setdefault("inventory", {})

        return cls(**filtered_data)


@dataclass
class PetData:
    """单个宠物数据类"""
    id: str = ""  # 宠物唯一ID
    skin_name: str = "default"
    x: int = 0
    y: int = 0
    scale: float = DEFAULT_SCALE
    hunger: int = 100
    mood: int = 100
    intimacy: int = 0
    is_visible: bool = True
    last_saved_at: float = 0.0  # Unix 时间戳，用于离线衰减与存档

    def __post_init__(self):
        """初始化后处理"""
        if not self.id:
            self.id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PetData":
        """从字典创建实例"""
        # 过滤掉不在数据类字段中的键
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**filtered_data)


def apply_offline_stat_decay(pet: PetData, settings: Settings) -> PetData:
    """
    根据上次存档时间，补算离线期间的饱食/心情衰减（好感不变）。
    """
    if pet.last_saved_at <= 0:
        return pet

    elapsed_min = max(0.0, (time.time() - pet.last_saved_at) / 60.0)
    if elapsed_min <= 0:
        return pet

    hunger_loss = int(elapsed_min * settings.hunger_decay_rate)
    mood_loss = int(elapsed_min * settings.mood_decay_rate)
    if hunger_loss <= 0 and mood_loss <= 0:
        return pet

    pet.hunger = max(0, pet.hunger - hunger_loss)
    pet.mood = max(0, pet.mood - mood_loss)
    logger.info(
        "离线衰减 %.1f 分钟: 宠物 %s 饱食 -%s 心情 -%s (亲密 %s 保留)",
        elapsed_min,
        pet.id,
        hunger_loss,
        mood_loss,
        pet.intimacy,
    )
    return pet


class DataPersistence:
    """
    数据持久化管理器
    负责设置和宠物数据的保存与加载
    """

    def __init__(self):
        """初始化数据持久化管理器"""
        self.config_loader = ConfigLoader()
        self._settings: Optional[Settings] = None
        self._pets: List[PetData] = []

    def load_settings(self) -> Settings:
        """
        加载设置
        如果文件不存在或损坏，返回默认设置

        Returns:
            Settings对象
        """
        data = self.config_loader.load_settings()
        self._settings = Settings.from_dict(data)
        logger.info("已加载设置")
        return self._settings

    def save_settings(self, settings: Optional[Settings] = None) -> bool:
        """
        保存设置

        Args:
            settings: 要保存的设置，如果为None则保存当前设置

        Returns:
            是否保存成功
        """
        if settings is not None:
            self._settings = settings

        if self._settings is None:
            logger.warning("没有可保存的设置")
            return False

        data = self._settings.to_dict()
        success = self.config_loader.save_settings(data)

        if success:
            logger.info("设置已保存")
        else:
            logger.error("设置保存失败")

        return success

    def get_settings(self) -> Optional[Settings]:
        """
        获取当前设置对象
        如果未加载，先加载

        Returns:
            当前设置对象
        """
        if self._settings is None:
            self.load_settings()
        return self._settings

    @staticmethod
    def _normalize_pet_list(pets: List[Any]) -> List[PetData]:
        """将 PetData 或快照 dict 统一为 PetData 列表。"""
        normalized: List[PetData] = []
        for pet in pets:
            if isinstance(pet, PetData):
                normalized.append(pet)
            elif isinstance(pet, dict):
                normalized.append(PetData.from_dict(pet))
            else:
                logger.warning("无法识别的宠物存档条目: %s", type(pet))
        return normalized

    def update_settings(self, **kwargs) -> bool:
        """
        更新设置中的部分字段并保存

        Args:
            **kwargs: 要更新的字段和值

        Returns:
            是否保存成功
        """
        if self._settings is None:
            self.load_settings()

        # 更新字段
        for key, value in kwargs.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
                logger.debug(f"更新设置: {key} = {value}")
            else:
                logger.warning(f"未知的设置字段: {key}")

        # 保存
        return self.save_settings()

    def load_pets(self) -> List[PetData]:
        """
        加载宠物数据

        Returns:
            宠物数据列表
        """
        data = self.config_loader.load_pets()
        pets_data = data.get("pets", [])

        self._pets = []
        for pet_dict in pets_data:
            try:
                pet = PetData.from_dict(pet_dict)
                self._pets.append(pet)
            except Exception as e:
                logger.error(f"加载宠物数据失败: {e}, 数据: {pet_dict}")

        logger.info(f"已加载 {len(self._pets)} 个宠物")
        return self._pets

    def save_pets(self, pets: Optional[List[Any]] = None) -> bool:
        """
        保存宠物数据

        Args:
            pets: PetData 或 get_pet_data() 快照 dict 的列表

        Returns:
            是否保存成功
        """
        if pets is not None:
            self._pets = self._normalize_pet_list(pets)

        if not self._pets:
            logger.warning("没有可保存的宠物数据")
            return False

        now = time.time()
        for pet in self._pets:
            pet.last_saved_at = now

        pets_dict = {
            "pets": [pet.to_dict() for pet in self._pets],
            "schema_version": 1,
            "saved_at": now,
        }

        success = self.config_loader.save_pets(pets_dict)

        if success:
            logger.info(f"已保存 {len(self._pets)} 个宠物")
        else:
            logger.error("宠物数据保存失败")

        return success

    def get_pets(self) -> List[PetData]:
        """
        获取当前宠物列表
        如果未加载，先加载

        Returns:
            当前宠物列表
        """
        if not self._pets:
            self.load_pets()
        return self._pets

    def add_pet(self, pet: PetData) -> bool:
        """
        添加宠物并保存

        Args:
            pet: 要添加的宠物数据

        Returns:
            是否保存成功
        """
        self._pets.append(pet)
        return self.save_pets()

    def remove_pet(self, pet_id: str) -> bool:
        """
        移除宠物并保存

        Args:
            pet_id: 要移除的宠物ID

        Returns:
            是否保存成功
        """
        self._pets = [p for p in self._pets if p.id != pet_id]
        return self.save_pets()

    def update_pet(self, pet: PetData) -> bool:
        """
        更新宠物数据并保存

        Args:
            pet: 要更新的宠物数据

        Returns:
            是否保存成功
        """
        for i, p in enumerate(self._pets):
            if p.id == pet.id:
                self._pets[i] = pet
                return self.save_pets()

        logger.warning(f"未找到宠物ID: {pet.id}")
        return False

    def create_default_pet(self) -> PetData:
        """
        创建默认宠物数据（用于首次启动或数据重置）

        Returns:
            默认宠物数据
        """
        from PyQt6.QtGui import QGuiApplication

        # 获取屏幕尺寸，计算右下角位置
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = screen_geometry.width() - 200  # 距右边20px，宠物宽约180px
            y = screen_geometry.height() - 200  # 距底边20px，宠物高约180px
        else:
            x = 100
            y = 100

        pet = PetData(
            id=str(uuid.uuid4()),
            skin_name="default",
            x=x,
            y=y,
            scale=DEFAULT_SCALE,
            hunger=100,
            mood=100,
            intimacy=0,
            is_visible=True,
        )

        logger.info(f"创建默认宠物: {pet.id}")
        return pet
