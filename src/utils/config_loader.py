"""
配置加载工具
处理配置文件路径、编码转换等
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

from .constants import (
    SETTINGS_FIELDS,
    PET_DATA_FIELDS,
    SETTINGS_FILE,
    PETS_FILE,
    BACKUP_SUFFIX,
    HUNGER_DECAY_PER_MINUTE,
    MOOD_DECAY_PER_MINUTE,
    get_config_dir,
)

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    配置加载器
    负责配置文件的读写、编码处理、数据验证
    """

    def __init__(self):
        """初始化配置加载器"""
        self.config_dir = get_config_dir()
        self.settings_path = self.config_dir / SETTINGS_FILE
        self.pets_path = self.config_dir / PETS_FILE

    def load_json(self, file_path: Path) -> Dict[str, Any]:
        """
        加载JSON文件
        支持自动备份损坏的文件

        Args:
            file_path: JSON文件路径

        Returns:
            加载的数据字典，失败返回空字典
        """
        if not file_path.exists():
            logger.warning(f"配置文件不存在: {file_path}")
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"成功加载配置文件: {file_path}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {file_path}, 错误: {e}")
            self._backup_corrupted_file(file_path)
            return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {file_path}, 错误: {e}")
            return {}

    def save_json(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """
        保存数据到JSON文件

        Args:
            file_path: JSON文件路径
            data: 要保存的数据

        Returns:
            是否保存成功
        """
        try:
            # 先保存到临时文件，再重命名（原子操作）
            temp_path = file_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            temp_path.replace(file_path)
            logger.info(f"成功保存配置文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {file_path}, 错误: {e}")
            return False

    def load_settings(self) -> Dict[str, Any]:
        """
        加载设置数据
        如果文件不存在或损坏，返回默认设置

        Returns:
            设置数据字典
        """
        data = self.load_json(self.settings_path)
        if not data:
            # 返回默认设置
            return dict(SETTINGS_FIELDS)

        # 验证并补充缺失的字段
        validated = self._validate_settings(data)
        return validated

    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        保存设置数据

        Args:
            settings: 设置数据字典

        Returns:
            是否保存成功
        """
        return self.save_json(self.settings_path, settings)

    def load_pets(self) -> Dict[str, Any]:
        """
        加载宠物数据
        如果文件不存在或损坏，返回空数据

        Returns:
            宠物数据字典，格式: {"pets": [pet1, pet2, ...]}
        """
        data = self.load_json(self.pets_path)
        if not data:
            return {"pets": []}

        # 验证宠物数据
        if "pets" not in data or not isinstance(data["pets"], list):
            logger.warning("宠物数据格式错误，返回空列表")
            return {"pets": []}

        return data

    def save_pets(self, pets: Dict[str, Any]) -> bool:
        """
        保存宠物数据

        Args:
            pets: 宠物数据字典

        Returns:
            是否保存成功
        """
        return self.save_json(self.pets_path, pets)

    def _validate_settings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证设置数据，补充缺失的字段

        Args:
            data: 原始设置数据

        Returns:
            验证后的设置数据
        """
        validated = dict(SETTINGS_FIELDS)  # 先复制默认值
        for key, default_value in SETTINGS_FIELDS.items():
            if key in data:
                # 类型检查
                if isinstance(default_value, type(data[key])):
                    validated[key] = data[key]
                else:
                    logger.warning(f"设置项 {key} 类型错误，使用默认值")
            # 如果缺失，保持默认值

        # 旧版 settings 按「每秒」存 1~2，自动迁移为每分钟默认值
        if validated.get("hunger_decay_rate", 50) <= 5:
            validated["hunger_decay_rate"] = HUNGER_DECAY_PER_MINUTE
        if validated.get("mood_decay_rate", 25) <= 10:
            validated["mood_decay_rate"] = MOOD_DECAY_PER_MINUTE

        if "gold" not in data:
            from .constants import DEFAULT_GOLD
            validated["gold"] = DEFAULT_GOLD
        elif isinstance(validated.get("gold"), (int, float)):
            validated["gold"] = max(0, int(validated["gold"]))

        if "inventory" in data and isinstance(data["inventory"], dict):
            validated["inventory"] = {
                str(k): max(0, int(v))
                for k, v in data["inventory"].items()
                if int(v) > 0
            }
        elif "inventory" not in data:
            validated["inventory"] = {}

        return validated

    def _backup_corrupted_file(self, file_path: Path) -> None:
        """
        备份损坏的配置文件

        Args:
            file_path: 要备份的文件路径
        """
        try:
            backup_path = file_path.with_suffix(BACKUP_SUFFIX)
            # 如果备份已存在，添加时间戳
            if backup_path.exists():
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = file_path.with_name(
                    f"{file_path.stem}{timestamp}{BACKUP_SUFFIX}"
                )

            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"已备份损坏的配置文件到: {backup_path}")

            # 删除损坏的文件，下次启动会使用默认配置
            file_path.unlink()
            logger.info(f"已删除损坏的配置文件: {file_path}")
        except Exception as e:
            logger.error(f"备份配置文件失败: {e}")

    @staticmethod
    def reset_to_default() -> None:
        """重置所有配置为默认值"""
        config_dir = get_config_dir()
        settings_path = config_dir / SETTINGS_FILE
        pets_path = config_dir / PETS_FILE

        # 删除现有配置文件
        for path in [settings_path, pets_path]:
            if path.exists():
                try:
                    path.unlink()
                    logger.info(f"已删除配置文件: {path}")
                except Exception as e:
                    logger.error(f"删除配置文件失败: {path}, 错误: {e}")

        logger.info("已重置所有配置为默认值")
