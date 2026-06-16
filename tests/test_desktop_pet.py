"""
Desktop Pet 桌面宠物应用 - 综合测试
覆盖常量、配置加载、数据持久化、皮肤管理、动画管理、状态管理、对话气泡、右键菜单及集成测试
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 检查 PyQt6 是否可用
try:
    from PyQt6.QtWidgets import QApplication
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

skip_no_pyqt6 = unittest.skipIf(not HAS_PYQT6, "PyQt6 not available (requires Python 3.9+)")

# 全局 QApplication 引用（PyQt6 测试共享）
_qapp = None


def _get_qapp():
    """获取或创建全局 QApplication（每个进程只需一个）"""
    global _qapp
    if not HAS_PYQT6:
        return None
    if _qapp is None:
        _qapp = QApplication.instance() or QApplication([])
    return _qapp


def _create_test_png(path, size=(64, 64), color=(0, 0, 0, 0)):
    """创建最小的有效 RGBA PNG 文件"""
    from PIL import Image
    img = Image.new("RGBA", size, color)
    img.save(str(path))


def _create_test_skin(skins_dir, skin_name, animations):
    """
    创建测试皮肤目录结构和占位 PNG 文件

    Args:
        skins_dir: 皮肤根目录
        skin_name: 皮肤名称
        animations: dict {anim_name: frame_count}
    """
    skin_dir = skins_dir / skin_name
    skin_dir.mkdir(parents=True, exist_ok=True)
    for anim_name, frame_count in animations.items():
        anim_dir = skin_dir / anim_name
        anim_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, frame_count + 1):
            frame_path = anim_dir / f"{i:03d}.png"
            _create_test_png(frame_path)


# ============================================================
# 0. 源码 Bug 检测
# ============================================================
class TestSourceCodeBugs(unittest.TestCase):
    """检测源码中的 Bug"""

    def test_utils_init_imports_valid_constants(self):
        """[FIXED] src/utils/__init__.py 导入的常量在 constants.py 中都有定义"""
        init_path = PROJECT_ROOT / "src" / "utils" / "__init__.py"
        constants_path = PROJECT_ROOT / "src" / "utils" / "constants.py"
        init_content = init_path.read_text(encoding="utf-8")
        constants_content = constants_path.read_text(encoding="utf-8")

        # 提取 __init__.py 中 from .constants import (...) 里的名称
        import_match = re.search(r'from \.constants import \((.*?)\)', init_content, re.DOTALL)
        if import_match:
            imported_names = [n.strip().rstrip(',') for n in import_match.group(1).split('\n') if n.strip()]
            for name in imported_names:
                self.assertIn(f"{name} =", constants_content,
                    f"'{name}' 导入自 constants.py 但在该文件中未定义")

    def test_speech_bubble_qwidget_import_before_usage(self):
        """[FIXED] src/ui/speech_bubble.py 中 QWidget 在使用前已导入"""
        path = PROJECT_ROOT / "src" / "ui" / "speech_bubble.py"
        content = path.read_text(encoding="utf-8")
        lines = content.split('\n')

        import_line = None
        usage_line = None
        for i, line in enumerate(lines):
            if 'QWidget' in line and 'import' in line and not line.strip().startswith('#'):
                import_line = i
            if 'Optional[QWidget]' in line:
                usage_line = i

        if usage_line is not None:
            self.assertIsNotNone(import_line,
                "QWidget 在类型注解中使用但未导入")
            self.assertLessEqual(import_line, usage_line,
                "QWidget 应在使用前导入（当前使用在第%d行，导入在第%d行）" % (usage_line + 1, import_line + 1))


# ============================================================
# 1. 常量模块测试
# ============================================================
class TestConstants(unittest.TestCase):
    """测试常量定义"""

    def test_animation_constants_defined(self):
        """所有动画名称常量都已定义"""
        from src.utils.constants import (
            ANIMATION_IDLE, ANIMATION_WALK, ANIMATION_GRABBED,
            ANIMATION_FALL, ANIMATION_CLICK, ANIMATION_SAD,
            ANIMATION_EAT, ANIMATION_HAPPY, ANIMATION_HOVER,
            ANIMATION_SLEEP, ANIMATION_SPECIAL1, ANIMATION_SPECIAL2,
        )
        self.assertEqual(ANIMATION_IDLE, "idle")
        self.assertEqual(ANIMATION_WALK, "walk")
        self.assertEqual(ANIMATION_GRABBED, "grabbed")
        self.assertEqual(ANIMATION_FALL, "fall")
        self.assertEqual(ANIMATION_CLICK, "click")
        self.assertEqual(ANIMATION_SAD, "sad")
        self.assertEqual(ANIMATION_EAT, "eat")
        self.assertEqual(ANIMATION_HAPPY, "happy")
        self.assertEqual(ANIMATION_HOVER, "hover")
        self.assertEqual(ANIMATION_SLEEP, "sleep")

    def test_animations_list_contains_all(self):
        """ANIMATIONS 列表包含所有必需动画"""
        from src.utils.constants import ANIMATIONS, ANIMATION_IDLE, ANIMATION_WALK
        self.assertIn(ANIMATION_IDLE, ANIMATIONS)
        self.assertIn(ANIMATION_WALK, ANIMATIONS)

    def test_default_fps(self):
        from src.utils.constants import DEFAULT_FPS
        self.assertEqual(DEFAULT_FPS, 10)

    def test_scale_range(self):
        from src.utils.constants import MIN_SCALE, MAX_SCALE, DEFAULT_SCALE
        self.assertEqual(MIN_SCALE, 0.3)
        self.assertEqual(MAX_SCALE, 1.5)
        self.assertEqual(DEFAULT_SCALE, 0.5)
        self.assertTrue(MIN_SCALE <= DEFAULT_SCALE <= MAX_SCALE)

    def test_opacity_range(self):
        from src.utils.constants import MIN_OPACITY, MAX_OPACITY, DEFAULT_OPACITY
        self.assertEqual(MIN_OPACITY, 0.3)
        self.assertEqual(MAX_OPACITY, 1.0)
        self.assertEqual(DEFAULT_OPACITY, 1.0)

    def test_decay_rates(self):
        from src.utils.constants import (
            HUNGER_DECAY_PER_MINUTE,
            MOOD_DECAY_PER_MINUTE,
            HUNGER_DECAY_RATE,
            MOOD_DECAY_RATE,
        )
        self.assertEqual(HUNGER_DECAY_PER_MINUTE, 50)
        self.assertEqual(MOOD_DECAY_PER_MINUTE, 25)
        self.assertEqual(HUNGER_DECAY_RATE, HUNGER_DECAY_PER_MINUTE)
        self.assertEqual(MOOD_DECAY_RATE, MOOD_DECAY_PER_MINUTE)

    def test_thresholds(self):
        from src.utils.constants import HUNGER_LOW_THRESHOLD, MOOD_LOW_THRESHOLD, HUNGER_CRITICAL
        self.assertEqual(HUNGER_LOW_THRESHOLD, 30)
        self.assertEqual(MOOD_LOW_THRESHOLD, 20)
        self.assertEqual(HUNGER_CRITICAL, 0)

    def test_interaction_boosts(self):
        from src.utils.constants import FEED_HUNGER_BOOST, FEED_MOOD_BOOST, PET_MOOD_BOOST, INTIMACY_INCREMENT
        self.assertEqual(FEED_HUNGER_BOOST, 50)
        self.assertEqual(FEED_MOOD_BOOST, 10)
        self.assertEqual(PET_MOOD_BOOST, 20)
        self.assertEqual(INTIMACY_INCREMENT, 1)

    def test_click_thresholds(self):
        from src.utils.constants import CLICK_THRESHOLD_MS, CLICK_THRESHOLD_PX
        self.assertEqual(CLICK_THRESHOLD_MS, 200)
        self.assertEqual(CLICK_THRESHOLD_PX, 5)

    def test_bubble_duration(self):
        from src.utils.constants import BUBBLE_DURATION_MS
        self.assertEqual(BUBBLE_DURATION_MS, 3000)

    def test_default_text_pools_not_empty(self):
        from src.utils.constants import DEFAULT_TEXT_POOLS
        self.assertIsInstance(DEFAULT_TEXT_POOLS, dict)
        for pool_name in ["happy", "hungry", "sad", "normal", "feed", "pet"]:
            self.assertIn(pool_name, DEFAULT_TEXT_POOLS)
            self.assertTrue(len(DEFAULT_TEXT_POOLS[pool_name]) > 0)

    def test_settings_fields_match_defaults(self):
        from src.utils.constants import SETTINGS_FIELDS, DEFAULT_SCALE, DEFAULT_FPS
        self.assertEqual(SETTINGS_FIELDS["scale"], DEFAULT_SCALE)
        self.assertEqual(SETTINGS_FIELDS["fps"], DEFAULT_FPS)

    def test_pet_data_fields(self):
        from src.utils.constants import PET_DATA_FIELDS
        for field in ["id", "skin_name", "x", "y", "scale", "hunger", "mood", "intimacy", "is_visible"]:
            self.assertIn(field, PET_DATA_FIELDS)

    def test_get_config_dir(self):
        from src.utils.constants import get_config_dir
        config_dir = get_config_dir()
        self.assertIsInstance(config_dir, Path)
        self.assertIn("DesktopPet", str(config_dir))

    def test_get_skins_dir(self):
        from src.utils.constants import get_skins_dir
        skins_dir = get_skins_dir()
        self.assertIsInstance(skins_dir, Path)
        self.assertEqual(skins_dir.name, "skins")


# ============================================================
# 2. 配置加载器测试
# ============================================================
class TestConfigLoader(unittest.TestCase):
    """测试 ConfigLoader"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.settings_path = Path(self.temp_dir) / "settings.json"
        self.pets_path = Path(self.temp_dir) / "pets.json"

        patcher = patch("src.utils.config_loader.get_config_dir", return_value=Path(self.temp_dir))
        self.mock_get_config_dir = patcher.start()
        self.addCleanup(patcher.stop)

        from src.utils.config_loader import ConfigLoader
        self.loader = ConfigLoader()

    def test_load_json_not_exists(self):
        result = self.loader.load_json(Path(self.temp_dir) / "nonexistent.json")
        self.assertEqual(result, {})

    def test_load_json_valid(self):
        test_data = {"key": "value", "number": 42}
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)
        self.assertEqual(self.loader.load_json(self.settings_path), test_data)

    def test_load_json_corrupted(self):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            f.write("{invalid json!!!")
        self.assertEqual(self.loader.load_json(self.settings_path), {})
        backup_files = list(Path(self.temp_dir).glob("*.backup"))
        self.assertEqual(len(backup_files), 1)

    def test_save_and_load_json(self):
        test_data = {"pets": [{"id": "1"}], "scale": 1.5}
        self.assertTrue(self.loader.save_json(self.settings_path, test_data))
        self.assertEqual(self.loader.load_json(self.settings_path), test_data)

    def test_load_settings_default(self):
        result = self.loader.load_settings()
        from src.utils.constants import DEFAULT_SCALE
        self.assertEqual(result["scale"], DEFAULT_SCALE)
        self.assertEqual(result["fps"], 10)

    def test_load_settings_valid(self):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump({"scale": 1.5, "fps": 20, "opacity": 0.8}, f)
        result = self.loader.load_settings()
        self.assertEqual(result["scale"], 1.5)
        self.assertEqual(result["fps"], 20)
        self.assertEqual(result["opacity"], 0.8)
        self.assertIn("hunger_decay_rate", result)

    def test_load_settings_wrong_type(self):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump({"scale": "not_a_number", "fps": "bad"}, f)
        result = self.loader.load_settings()
        from src.utils.constants import DEFAULT_SCALE
        self.assertEqual(result["scale"], DEFAULT_SCALE)
        self.assertEqual(result["fps"], 10)

    def test_save_settings(self):
        self.assertTrue(self.loader.save_settings({"scale": 1.8, "fps": 15}))
        loaded = self.loader.load_settings()
        self.assertEqual(loaded["scale"], 1.8)
        self.assertEqual(loaded["fps"], 15)

    def test_load_pets_empty(self):
        self.assertEqual(self.loader.load_pets(), {"pets": []})

    def test_load_pets_valid(self):
        with open(self.pets_path, "w", encoding="utf-8") as f:
            json.dump({"pets": [{"id": "pet1", "skin_name": "default"}]}, f)
        result = self.loader.load_pets()
        self.assertEqual(len(result["pets"]), 1)
        self.assertEqual(result["pets"][0]["id"], "pet1")

    def test_load_pets_invalid_format(self):
        with open(self.pets_path, "w", encoding="utf-8") as f:
            json.dump({"not_pets": "value"}, f)
        self.assertEqual(self.loader.load_pets(), {"pets": []})

    def test_save_pets(self):
        data = {"pets": [{"id": "pet1"}]}
        self.assertTrue(self.loader.save_pets(data))
        self.assertEqual(self.loader.load_pets(), data)

    def test_backup_corrupted_file(self):
        with open(self.settings_path, "w", encoding="utf-8") as f:
            f.write("corrupted")
        self.loader._backup_corrupted_file(self.settings_path)
        self.assertFalse(self.settings_path.exists())
        self.assertEqual(len(list(Path(self.temp_dir).glob("*.backup"))), 1)

    def test_backup_existing_backup(self):
        (self.settings_path.with_suffix(".backup")).write_text("old backup")
        with open(self.settings_path, "w", encoding="utf-8") as f:
            f.write("corrupted")
        self.loader._backup_corrupted_file(self.settings_path)
        self.assertGreaterEqual(len(list(Path(self.temp_dir).glob("*backup*"))), 2)

    def test_reset_to_default(self):
        """重置所有配置为默认值"""
        self.settings_path.write_text('{"scale": 2.0}')
        self.pets_path.write_text('{"pets": []}')
        from src.utils.config_loader import ConfigLoader
        ConfigLoader.reset_to_default()
        self.assertFalse(self.settings_path.exists())
        self.assertFalse(self.pets_path.exists())


# ============================================================
# 3. 数据持久化测试
# ============================================================
class TestDataPersistence(unittest.TestCase):
    """测试 DataPersistence、Settings、PetData"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_patcher = patch("src.utils.config_loader.get_config_dir", return_value=Path(self.temp_dir))
        self.config_patcher.start()
        self.const_patcher = patch("src.utils.constants.get_config_dir", return_value=Path(self.temp_dir))
        self.const_patcher.start()
        self.addCleanup(self.config_patcher.stop)
        self.addCleanup(self.const_patcher.stop)

        from src.system.data_persistence import DataPersistence
        self.dp = DataPersistence()

    def test_settings_defaults(self):
        from src.system.data_persistence import Settings
        from src.utils.constants import DEFAULT_SCALE, DEFAULT_GOLD
        s = Settings()
        self.assertEqual(s.scale, DEFAULT_SCALE)
        self.assertEqual(s.fps, 10)
        self.assertEqual(s.opacity, 1.0)
        self.assertEqual(s.hunger_decay_rate, 50.0)
        self.assertEqual(s.mood_decay_rate, 25.0)
        self.assertEqual(s.intimacy_threshold, 10)
        self.assertEqual(s.max_pets, 5)
        self.assertFalse(s.auto_run_enabled)
        self.assertTrue(s.auto_walk_enabled)
        self.assertEqual(s.default_skin, "default")
        from src.utils.constants import DEFAULT_GOLD
        self.assertEqual(s.gold, DEFAULT_GOLD)
        self.assertEqual(s.inventory, {})
        self.assertIsInstance(s.text_pools, dict)

    def test_settings_to_dict(self):
        from src.system.data_persistence import Settings
        d = Settings(scale=1.5, fps=20).to_dict()
        self.assertEqual(d["scale"], 1.5)
        self.assertEqual(d["fps"], 20)

    def test_settings_from_dict(self):
        from src.system.data_persistence import Settings
        s = Settings.from_dict({"scale": 1.5, "fps": 20, "opacity": 0.8})
        self.assertEqual(s.scale, 1.5)
        self.assertEqual(s.fps, 20)
        self.assertEqual(s.opacity, 0.8)
        self.assertEqual(s.hunger_decay_rate, 50.0)

    def test_settings_from_dict_filters_unknown_keys(self):
        from src.system.data_persistence import Settings
        s = Settings.from_dict({"scale": 1.5, "unknown_key": "value"})
        self.assertEqual(s.scale, 1.5)
        self.assertFalse(hasattr(s, "unknown_key"))

    def test_pet_data_defaults(self):
        from src.system.data_persistence import PetData
        p = PetData()
        self.assertNotEqual(p.id, "")
        self.assertEqual(p.skin_name, "default")
        self.assertEqual(p.hunger, 100)
        self.assertEqual(p.mood, 100)
        self.assertEqual(p.intimacy, 0)
        self.assertTrue(p.is_visible)

    def test_pet_data_auto_id(self):
        from src.system.data_persistence import PetData
        self.assertNotEqual(PetData().id, PetData().id)

    def test_pet_data_explicit_id(self):
        from src.system.data_persistence import PetData
        self.assertEqual(PetData(id="test-id-123").id, "test-id-123")

    def test_pet_data_to_dict(self):
        from src.system.data_persistence import PetData
        d = PetData(id="my-pet", skin_name="cat", x=100, y=200).to_dict()
        self.assertEqual(d["id"], "my-pet")
        self.assertEqual(d["skin_name"], "cat")

    def test_pet_data_from_dict(self):
        from src.system.data_persistence import PetData
        p = PetData.from_dict({"id": "test", "skin_name": "dog", "hunger": 50, "mood": 80})
        self.assertEqual(p.id, "test")
        self.assertEqual(p.hunger, 50)

    def test_load_settings_returns_settings(self):
        from src.utils.constants import DEFAULT_SCALE
        settings = self.dp.load_settings()
        self.assertEqual(settings.scale, DEFAULT_SCALE)
        self.assertEqual(settings.fps, 10)

    def test_save_and_load_settings(self):
        from src.system.data_persistence import Settings
        self.assertTrue(self.dp.save_settings(Settings(scale=1.8, fps=15, opacity=0.9)))
        loaded = self.dp.load_settings()
        self.assertEqual(loaded.scale, 1.8)
        self.assertEqual(loaded.fps, 15)

    def test_get_settings_auto_load(self):
        from src.utils.constants import DEFAULT_SCALE
        self.assertIsNotNone(self.dp.get_settings())
        self.assertEqual(self.dp.get_settings().scale, DEFAULT_SCALE)

    def test_update_settings(self):
        self.assertTrue(self.dp.update_settings(scale=1.5, fps=20))
        s = self.dp.get_settings()
        self.assertEqual(s.scale, 1.5)
        self.assertEqual(s.fps, 20)

    def test_update_settings_unknown_field(self):
        self.assertTrue(self.dp.update_settings(unknown_field="value"))

    def test_load_pets_empty(self):
        self.assertEqual(self.dp.load_pets(), [])

    def test_save_and_load_pets(self):
        from src.system.data_persistence import PetData
        pet1 = PetData(id="p1", skin_name="default", x=100, y=200)
        pet2 = PetData(id="p2", skin_name="cat", x=300, y=400)
        self.assertTrue(self.dp.save_pets([pet1, pet2]))
        loaded = self.dp.load_pets()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].id, "p1")
        self.assertEqual(loaded[1].skin_name, "cat")

    def test_save_pets_accepts_dict_snapshots(self):
        from src.system.data_persistence import PetData
        snapshot = {
            "id": "snap-1",
            "skin_name": "default",
            "x": 10,
            "y": 20,
            "scale": 0.5,
            "hunger": 66,
            "mood": 55,
            "intimacy": 23,
            "is_visible": True,
        }
        self.assertTrue(self.dp.save_pets([snapshot]))
        loaded = self.dp.load_pets()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].intimacy, 23)
        self.assertEqual(loaded[0].hunger, 66)
        self.assertGreater(loaded[0].last_saved_at, 0)

    def test_apply_offline_stat_decay(self):
        import time
        from src.system.data_persistence import PetData, Settings, apply_offline_stat_decay

        pet = PetData(
            id="offline-1",
            hunger=100,
            mood=100,
            intimacy=12,
            last_saved_at=time.time() - 60,
        )
        settings = Settings(hunger_decay_rate=50, mood_decay_rate=25)
        apply_offline_stat_decay(pet, settings)
        self.assertEqual(pet.intimacy, 12)
        self.assertEqual(pet.hunger, 50)
        self.assertEqual(pet.mood, 75)

    def test_intimacy_persists_across_save_load(self):
        from src.system.data_persistence import PetData

        pet = PetData(id="love-1", intimacy=37, hunger=80, mood=70)
        self.assertTrue(self.dp.save_pets([pet]))
        loaded = self.dp.load_pets()[0]
        self.assertEqual(loaded.intimacy, 37)
        self.assertEqual(loaded.hunger, 80)
        self.assertEqual(loaded.mood, 70)

    def test_save_pets_empty_list(self):
        self.assertFalse(self.dp.save_pets([]))

    def test_add_pet(self):
        from src.system.data_persistence import PetData
        self.assertTrue(self.dp.add_pet(PetData(id="new-pet")))
        self.assertEqual(len(self.dp.load_pets()), 1)

    def test_remove_pet(self):
        from src.system.data_persistence import PetData
        self.dp.add_pet(PetData(id="p1"))
        self.dp.add_pet(PetData(id="p2"))
        self.assertTrue(self.dp.remove_pet("p1"))
        self.assertEqual(len(self.dp.load_pets()), 1)
        self.assertEqual(self.dp.load_pets()[0].id, "p2")

    def test_update_pet(self):
        from src.system.data_persistence import PetData
        self.dp.add_pet(PetData(id="p1", hunger=100))
        self.assertTrue(self.dp.update_pet(PetData(id="p1", hunger=50, mood=80)))
        pets = self.dp.load_pets()
        self.assertEqual(pets[0].hunger, 50)

    def test_update_pet_not_found(self):
        from src.system.data_persistence import PetData
        self.assertFalse(self.dp.update_pet(PetData(id="nonexistent")))

    def test_load_pets_corrupted_data_skipped(self):
        pets_path = Path(self.temp_dir) / "pets.json"
        with open(pets_path, "w", encoding="utf-8") as f:
            json.dump({"pets": [{"id": "good_pet"}, "not_a_dict"]}, f)
        self.assertGreaterEqual(len(self.dp.load_pets()), 1)

    def test_save_settings_none_returns_false(self):
        dp2 = type(self.dp).__new__(type(self.dp))
        dp2.config_loader = self.dp.config_loader
        dp2._settings = None
        dp2._pets = []
        self.assertFalse(dp2.save_settings(None))


class TestIntimacyLevels(unittest.TestCase):
    """好感等级曲线"""

    def test_starts_at_level_one(self):
        from src.core.intimacy_levels import intimacy_level

        self.assertEqual(intimacy_level(0), 1)
        self.assertEqual(intimacy_level(3), 1)

    def test_early_levels_fast(self):
        from src.core.intimacy_levels import intimacy_level, xp_to_reach_level

        self.assertEqual(xp_to_reach_level(2), 4)
        self.assertEqual(intimacy_level(4), 2)
        self.assertEqual(intimacy_level(11), 3)

    def test_later_levels_slower(self):
        from src.core.intimacy_levels import xp_for_next_level

        self.assertEqual(xp_for_next_level(1), 4)
        self.assertEqual(xp_for_next_level(2), 7)
        self.assertEqual(xp_for_next_level(5), 16)
        self.assertLess(xp_for_next_level(2), xp_for_next_level(5))

    def test_level_progress(self):
        from src.core.intimacy_levels import intimacy_level_progress

        self.assertEqual(intimacy_level_progress(6), (2, 2, 7))
        self.assertEqual(intimacy_level_progress(11), (3, 0, 10))


@skip_no_pyqt6
class TestInventoryManager(unittest.TestCase):
    """商店 / 背包逻辑"""

    def setUp(self):
        _get_qapp()
        self.temp_dir = tempfile.mkdtemp()
        self.config_patcher = patch(
            "src.utils.config_loader.get_config_dir",
            return_value=Path(self.temp_dir),
        )
        self.config_patcher.start()
        self.const_patcher = patch(
            "src.utils.constants.get_config_dir",
            return_value=Path(self.temp_dir),
        )
        self.const_patcher.start()
        self.addCleanup(self.config_patcher.stop)
        self.addCleanup(self.const_patcher.stop)

        from src.system.data_persistence import DataPersistence
        from src.core.inventory_manager import InventoryManager

        self.dp = DataPersistence()
        self.dp.load_settings()
        self.inv = InventoryManager(self.dp)

    def test_default_gold(self):
        from src.utils.constants import DEFAULT_GOLD

        self.assertEqual(self.inv.gold, DEFAULT_GOLD)

    def test_buy_burger(self):
        from src.utils.constants import DEFAULT_GOLD, FEED_ITEM_ID

        self.assertTrue(self.inv.buy(FEED_ITEM_ID, 2))
        self.assertEqual(self.inv.get_count(FEED_ITEM_ID), 2)
        self.assertEqual(self.inv.gold, DEFAULT_GOLD - 10)

    def test_buy_insufficient_gold(self):
        settings = self.dp.get_settings()
        settings.gold = 3
        self.dp.save_settings(settings)
        self.assertFalse(self.inv.buy("burger", 1))

    def test_consume_feed_item(self):
        self.inv.buy("burger", 1)
        self.assertTrue(self.inv.consume_feed_item())
        self.assertEqual(self.inv.feed_item_count(), 0)
        self.assertFalse(self.inv.consume_feed_item())

    def test_feed_food_count_only_consumables(self):
        settings = self.dp.get_settings()
        settings.inventory = {"burger": 2, "unknown_item": 5}
        self.dp.save_settings(settings)
        self.assertEqual(self.inv.feed_food_count(), 2)


@skip_no_pyqt6
class TestEconomyManager(unittest.TestCase):
    """打工小游戏金币逻辑"""

    def setUp(self):
        _get_qapp()
        self.temp_dir = tempfile.mkdtemp()
        self.config_patcher = patch(
            "src.utils.config_loader.get_config_dir",
            return_value=Path(self.temp_dir),
        )
        self.config_patcher.start()
        self.const_patcher = patch(
            "src.utils.constants.get_config_dir",
            return_value=Path(self.temp_dir),
        )
        self.const_patcher.start()
        self.addCleanup(self.config_patcher.stop)
        self.addCleanup(self.const_patcher.stop)

        from src.system.data_persistence import DataPersistence
        from src.core.inventory_manager import InventoryManager
        from src.core.economy_manager import EconomyManager

        self.dp = DataPersistence()
        self.dp.load_settings()
        self.inv = InventoryManager(self.dp)
        self.econ = EconomyManager(self.dp, inventory_mgr=self.inv)

    def test_snake_reward_formula(self):
        from src.utils.constants import GAME_SNAKE_ID

        # base 5 + 3*2 = 11
        self.assertEqual(self.econ.calc_game_reward(GAME_SNAKE_ID, 3), 11)
        self.assertEqual(self.econ.calc_game_reward(GAME_SNAKE_ID, 0), 0)

    def test_award_increases_gold_and_daily(self):
        from src.utils.constants import GAME_SNAKE_ID, DAILY_GOLD_CAP

        before = self.inv.gold
        award, hit_cap = self.econ.award_game_reward(GAME_SNAKE_ID, 4)
        self.assertEqual(award, 13)  # 5 + 4*2
        self.assertFalse(hit_cap)
        self.assertEqual(self.inv.gold, before + 13)
        self.assertEqual(self.econ.daily_earned(), 13)
        stats = self.econ.get_game_stats(GAME_SNAKE_ID)
        self.assertEqual(stats["best_score"], 4)
        self.assertEqual(stats["plays"], 1)

    def test_daily_cap_limits_award(self):
        from src.utils.constants import GAME_SNAKE_ID, DAILY_GOLD_CAP

        settings = self.dp.get_settings()
        settings.daily_gold_earned = DAILY_GOLD_CAP - 5
        settings.daily_reset_date = self.econ._today()
        self.dp.save_settings(settings)

        award, hit_cap = self.econ.award_game_reward(GAME_SNAKE_ID, 10)
        self.assertEqual(award, 5)
        self.assertTrue(hit_cap)
        self.assertEqual(self.econ.daily_remaining(), 0)

    def test_richman_win_reward(self):
        from src.utils.constants import GAME_RICHMAN_ID, RICHMAN_FEATURE

        score = int(RICHMAN_FEATURE["reward_win_score"])
        expected = int(RICHMAN_FEATURE["reward_base"]) + score * int(RICHMAN_FEATURE["reward_per_food"])
        self.assertEqual(self.econ.calc_game_reward(GAME_RICHMAN_ID, score), expected)
        award, _ = self.econ.award_game_reward(GAME_RICHMAN_ID, score)
        self.assertEqual(award, expected)
        stats = self.econ.get_game_stats(GAME_RICHMAN_ID)
        self.assertEqual(stats.get("wins"), 1)


class TestRichmanEngine(unittest.TestCase):
    """大富翁规则引擎（无需完整 UI）"""

    def setUp(self):
        _get_qapp()
        from src.games.richman.game_engine import RichmanEngine, GamePhase
        from src.games.richman.board_data import tile_count
        from src.games.richman.board_layout import _PATH_GRID

        self.engine = RichmanEngine()
        self.GamePhase = GamePhase
        self.tile_count = tile_count()
        self.path_len = len(_PATH_GRID)

    def test_board_size(self):
        self.assertEqual(self.tile_count, 24)
        self.assertEqual(self.path_len, 24)

    def test_path_grid_adjacent(self):
        from src.games.richman.board_layout import path_grid

        grid = path_grid()
        n = len(grid)

        def neighbors(x: int, z: int) -> set[tuple[int, int]]:
            return {(x + 1, z), (x - 1, z), (x, z + 1), (x, z - 1)}

        for i in range(n):
            a = grid[i]
            b = grid[(i + 1) % n]
            self.assertIn(b, neighbors(*a), f"path {i}->{(i + 1) % n} not adjacent: {a} -> {b}")

    def test_move_back_updates_position(self):
        from src.games.richman.cards import CardDef
        from src.games.richman.player_setup import PlayerSlot

        self.engine.new_game(players=[PlayerSlot("甲", True), PlayerSlot("乙", True)])
        p = self.engine.current_player
        p.position = 6
        self.engine._apply_card(CardDef("后退 3 格", "move_back"))
        self.assertEqual(p.position, 3)

    def test_jail_skip_turn_passes_to_next_player(self):
        from src.games.richman.player_setup import PlayerSlot

        self.engine.new_game(
            players=[PlayerSlot("甲", True), PlayerSlot("乙", True)]
        )
        p0 = self.engine.players()[0]
        p0.in_jail = True
        p0.pending_jail_skip = True
        self.engine._phase = self.GamePhase.WAIT_ROLL
        self.assertTrue(self.engine.can_skip_jail_turn())
        self.assertFalse(self.engine.can_roll())
        self.engine.skip_jail_turn()
        self.engine.complete_turn()
        self.assertEqual(self.engine.current_player.id, 1)
        self.assertFalse(p0.pending_jail_skip)
        self.assertTrue(p0.in_jail)

    def test_go_to_jail_tile_sends_player_to_jail(self):
        from src.games.richman.board_data import TileKind, all_tiles

        self.engine.new_game("测试")
        go_idx = next(t.index for t in all_tiles() if t.kind == TileKind.GO_TO_JAIL)
        jail_idx = next(t.index for t in all_tiles() if t.kind == TileKind.JAIL)
        p = self.engine.current_player
        p.position = go_idx
        self.engine._resolve_tile()
        self.assertEqual(p.position, jail_idx)
        self.assertTrue(p.in_jail)
        self.assertTrue(p.pending_jail_skip)

    def test_new_game_players(self):
        self.engine.new_game("测试")
        self.assertEqual(len(self.engine.players()), 4)
        self.assertTrue(self.engine.current_player.is_human)
        self.assertEqual(self.engine.phase, self.GamePhase.WAIT_ROLL)
        self.assertEqual(self.engine.players()[0].money, 5000)

    def test_new_game_custom_roster(self):
        from src.games.richman.player_setup import PlayerSlot

        self.engine.new_game(
            players=[
                PlayerSlot("甲", True, "preset_2"),
                PlayerSlot("乙", True, "preset_5"),
                PlayerSlot("电脑", False, "preset_1"),
            ]
        )
        self.assertEqual(len(self.engine.players()), 3)
        self.assertEqual(sum(1 for p in self.engine.players() if p.is_human), 2)
        self.assertEqual(self.engine.players()[0].avatar_id, "preset_2")
        self.assertEqual(self.engine.players()[1].avatar_id, "preset_5")

    def test_buy_property(self):
        self.engine.new_game()
        p = self.engine.current_player
        p.position = 1
        tile = __import__("src.games.richman.board_data", fromlist=["get_tile"]).get_tile(1)
        before = p.money
        self.engine._phase = self.GamePhase.ACTION
        self.assertTrue(self.engine.buy_current_property())
        self.assertEqual(self.engine.property_at(1).owner_id, p.id)
        self.assertEqual(p.money, before - tile.price)

    def test_action_phase_allows_skip_without_money(self):
        self.engine.new_game()
        p = self.engine.current_player
        p.position = 22  # 香港 ¥280
        p.money = 100
        self.engine._phase = self.GamePhase.ACTION
        self.assertFalse(self.engine.can_buy_current())
        self.assertTrue(self.engine.can_skip_current())
        self.engine.skip_action()
        self.assertEqual(self.engine.phase, self.GamePhase.WAIT_ROLL)
        self.assertEqual(self.engine.current_player.id, 1)

    def test_resolve_enters_resolving_before_next_player(self):
        self.engine.new_game()
        p = self.engine.current_player
        p.position = 4  # 所得税
        self.engine._phase = self.GamePhase.MOVING
        self.engine._resolve_tile()
        self.assertEqual(self.engine.phase, self.GamePhase.RESOLVING)
        self.engine.complete_turn()
        self.assertEqual(self.engine.phase, self.GamePhase.WAIT_ROLL)
        self.assertEqual(self.engine.current_player.id, 1)

    def test_monopoly_doubles_rent(self):
        from src.games.richman.property_rules import compute_rent

        self.engine.new_game()
        p = self.engine.current_player
        # 蓝色组：天津(1) + 重庆(3)
        self.engine._properties[1].owner_id = p.id
        self.engine._properties[3].owner_id = p.id
        tile = __import__("src.games.richman.board_data", fromlist=["get_tile"]).get_tile(1)
        rent = compute_rent(tile, self.engine.property_at(1), self.engine._properties)
        self.assertEqual(rent, tile.rent * 2)

    def test_build_house(self):
        self.engine.new_game()
        p = self.engine.current_player
        self.engine._properties[1].owner_id = p.id
        self.engine._properties[3].owner_id = p.id
        p.position = 1
        before = p.money
        self.assertTrue(self.engine.build_house())
        self.assertEqual(self.engine.property_at(1).level, 1)
        self.assertLess(p.money, before)

    def test_card_deck_draw(self):
        from src.games.richman.cards import new_decks

        chance, fate = new_decks()
        c = chance.draw()
        self.assertTrue(c.text)
        f = fate.draw()
        self.assertTrue(f.text)


@skip_no_pyqt6
class TestChessEngine(unittest.TestCase):
  def setUp(self):
    from src.games.chess.game_engine import ChessEngine
    from src.games.chess.player_setup import ChessSetup

    self.engine = ChessEngine()
    self.ChessSetup = ChessSetup

  def test_new_game_and_legal_move(self):
    import chess

    setup = self.ChessSetup.vs_ai("测试", True, "easy")
    self.engine.new_game(setup)
    self.assertTrue(self.engine.make_move("e2e4"))
    self.assertEqual(self.engine.board.piece_at(chess.parse_square("e4")).symbol(), "P")

  def test_resign_awards_side(self):
    setup = self.ChessSetup.vs_ai("人", True, "easy")
    self.engine.new_game(setup)
    self.engine.resign()
    self.assertEqual(self.engine.phase.value, "game_over")


# ============================================================
# 4. 皮肤管理器测试
# ============================================================
@skip_no_pyqt6
class TestSkinManager(unittest.TestCase):
    """测试 SkinManager"""

    def setUp(self):
        _get_qapp()
        self.temp_dir = tempfile.mkdtemp()
        self.skins_dir = Path(self.temp_dir) / "skins"
        self.skins_dir.mkdir(parents=True, exist_ok=True)

        from src.core.skin_manager import SkinManager
        # 直接传入 skins_base_path，避免 patch 问题
        self.skin_mgr = SkinManager(skins_base_path=self.skins_dir)

    def test_scan_empty_dir(self):
        """空目录扫描返回空列表"""
        skins = self.skin_mgr.scan_skins()
        self.assertEqual(skins, [])

    def test_scan_skins_with_animations(self):
        """扫描包含动画的皮肤"""
        _create_test_skin(self.skins_dir, "test_skin", {"idle": 3, "walk": 2})
        skins = self.skin_mgr.scan_skins()
        self.assertIn("test_skin", skins)

    def test_scan_skins_skip_non_dirs(self):
        """扫描跳过非目录文件"""
        (self.skins_dir / "not_a_skin.txt").touch()
        skins = self.skin_mgr.scan_skins()
        self.assertEqual(skins, [])

    def test_scan_skins_skip_empty_skin(self):
        """没有动画目录的皮肤被跳过"""
        skin_dir = self.skins_dir / "empty_skin"
        skin_dir.mkdir()
        (skin_dir / "info.txt").touch()
        skins = self.skin_mgr.scan_skins()
        self.assertNotIn("empty_skin", skins)

    def test_has_skin(self):
        """检查皮肤是否存在"""
        _create_test_skin(self.skins_dir, "my_skin", {"idle": 1})
        self.skin_mgr.scan_skins()
        self.assertTrue(self.skin_mgr.has_skin("my_skin"))
        self.assertFalse(self.skin_mgr.has_skin("nonexistent"))

    def test_has_animation(self):
        """检查动画是否存在"""
        _create_test_skin(self.skins_dir, "test", {"idle": 1, "walk": 2})
        self.skin_mgr.scan_skins()
        self.assertTrue(self.skin_mgr.has_animation("test", "idle"))
        self.assertTrue(self.skin_mgr.has_animation("test", "walk"))
        self.assertFalse(self.skin_mgr.has_animation("test", "nonexistent"))
        self.assertFalse(self.skin_mgr.has_animation("nonexistent", "idle"))

    def test_get_animation_frames(self):
        """获取动画帧列表"""
        _create_test_skin(self.skins_dir, "test", {"idle": 3})
        self.skin_mgr.scan_skins()
        frames = self.skin_mgr.get_animation_frames("test", "idle")
        self.assertEqual(len(frames), 3)

    def test_get_animation_frames_nonexistent(self):
        """获取不存在的动画帧返回空列表"""
        self.assertEqual(self.skin_mgr.get_animation_frames("no_skin", "no_anim"), [])

    def test_frames_sorted_by_number(self):
        """帧文件按数字顺序排序"""
        _create_test_skin(self.skins_dir, "test", {"idle": 5})
        self.skin_mgr.scan_skins()
        frames = self.skin_mgr.get_animation_frames("test", "idle")
        numbers = []
        for f in frames:
            nums = [int(x) for x in re.findall(r'\d+', Path(f).stem)]
            numbers.append(nums[-1] if nums else 0)
        self.assertEqual(numbers, sorted(numbers))

    def test_load_skin(self):
        """加载皮肤"""
        _create_test_skin(self.skins_dir, "test", {"idle": 1})
        self.skin_mgr.scan_skins()
        self.assertTrue(self.skin_mgr.load_skin("test"))

    def test_load_skin_nonexistent(self):
        """加载不存在的皮肤返回 False"""
        self.assertFalse(self.skin_mgr.load_skin("nonexistent"))

    def test_get_available_skins_returns_copy(self):
        """get_available_skins 返回副本"""
        _create_test_skin(self.skins_dir, "test", {"idle": 1})
        self.skin_mgr.scan_skins()
        s1 = self.skin_mgr.get_available_skins()
        s2 = self.skin_mgr.get_available_skins()
        self.assertEqual(s1, s2)
        self.assertIsNot(s1, s2)

    def test_load_frame_image(self):
        """加载帧图片为 QImage"""
        _create_test_skin(self.skins_dir, "test", {"idle": 1})
        self.skin_mgr.scan_skins()
        frames = self.skin_mgr.get_animation_frames("test", "idle")
        qimage = self.skin_mgr.load_frame_image(frames[0])
        self.assertIsNotNone(qimage)
        self.assertFalse(qimage.isNull())

    def test_load_frame_image_nonexistent(self):
        """加载不存在的帧图片返回 None"""
        self.assertIsNone(self.skin_mgr.load_frame_image("/nonexistent/path.png"))

    def test_load_animation_frames(self):
        """加载动画的所有帧为 QImage"""
        _create_test_skin(self.skins_dir, "test", {"idle": 3})
        self.skin_mgr.scan_skins()
        qimages = self.skin_mgr.load_animation_frames("test", "idle")
        self.assertEqual(len(qimages), 3)
        for img in qimages:
            self.assertFalse(img.isNull())

    def test_sleep_frames_filter_sprite_sheet(self):
        """睡眠动画应过滤未切分的精灵图脏帧"""
        project = Path(__file__).resolve().parent.parent
        sleep_dir = project / "skins" / "default" / "sleep"
        if not sleep_dir.is_dir():
            self.skipTest("default sleep skin not present")
        from src.core.skin_manager import SkinManager

        mgr = SkinManager(skins_base_path=project / "skins")
        raw_count = len(mgr.get_animation_frames("default", "sleep"))
        qimages = mgr.load_animation_frames("default", "sleep")
        self.assertLess(len(qimages), raw_count)
        self.assertGreaterEqual(len(qimages), 10)

    def test_extract_frame_number(self):
        """测试帧编号提取"""
        from src.core.skin_manager import SkinManager
        self.assertEqual(SkinManager._extract_frame_number("001.png"), 1)
        self.assertEqual(SkinManager._extract_frame_number("frame_010.png"), 10)
        self.assertEqual(SkinManager._extract_frame_number("a_b_005_c.png"), 5)
        self.assertEqual(SkinManager._extract_frame_number("no_numbers.png"), 0)

    def test_create_placeholder_skin(self):
        """创建占位皮肤"""
        result = self.skin_mgr.create_placeholder_skin("placeholder")
        self.assertTrue(result)
        idle_dir = self.skins_dir / "placeholder" / "idle"
        self.assertTrue(idle_dir.exists())
        self.assertEqual(len(list(idle_dir.glob("*.png"))), 3)

    def test_multiple_skins(self):
        """多个皮肤独立管理"""
        _create_test_skin(self.skins_dir, "skin_a", {"idle": 2})
        _create_test_skin(self.skins_dir, "skin_b", {"idle": 3, "walk": 2})
        self.skin_mgr.scan_skins()
        self.assertEqual(len(self.skin_mgr.get_available_skins()), 2)
        self.assertEqual(len(self.skin_mgr.get_animation_frames("skin_a", "idle")), 2)
        self.assertEqual(len(self.skin_mgr.get_animation_frames("skin_b", "walk")), 2)
        self.assertEqual(self.skin_mgr.get_animation_frames("skin_a", "walk"), [])


# ============================================================
# 5. 动画管理器测试
# ============================================================
@skip_no_pyqt6
class TestAnimationManager(unittest.TestCase):
    """测试 AnimationManager"""

    def setUp(self):
        _get_qapp()
        self.temp_dir = tempfile.mkdtemp()
        self.skins_dir = Path(self.temp_dir) / "skins"
        self.skins_dir.mkdir(parents=True, exist_ok=True)

        _create_test_skin(self.skins_dir, "default", {"idle": 3, "walk": 2, "click": 1, "fall": 1, "grabbed": 1})

        from src.core.skin_manager import SkinManager
        from src.core.animation_manager import AnimationManager
        self.skin_mgr = SkinManager(skins_base_path=self.skins_dir)
        self.anim_mgr = AnimationManager(self.skin_mgr)

    def test_initial_state(self):
        self.assertEqual(self.anim_mgr.current_frame_index, 0)
        self.assertEqual(self.anim_mgr.current_animation, "")
        self.assertFalse(self.anim_mgr.is_playing)
        self.assertEqual(self.anim_mgr.fps, 10)

    def test_load_animation(self):
        self.assertTrue(self.anim_mgr.load_animation("idle"))
        self.assertEqual(self.anim_mgr.current_animation, "idle")
        self.assertEqual(len(self.anim_mgr.frames), 3)

    def test_load_nonexistent_animation(self):
        self.assertFalse(self.anim_mgr.load_animation("nonexistent"))

    def test_play_animation(self):
        self.assertTrue(self.anim_mgr.play("idle", loop=True))
        self.assertTrue(self.anim_mgr.is_playing)
        self.assertEqual(self.anim_mgr.current_animation, "idle")

    def test_play_nonexistent_fallback_to_idle(self):
        """播放不存在的动画时回退到 idle"""
        result = self.anim_mgr.play("nonexistent", loop=True)
        self.assertTrue(result)
        self.assertEqual(self.anim_mgr.current_animation, "idle")

    def test_play_idle_when_idle_fails(self):
        """idle 也不存在时返回 False"""
        from src.core.skin_manager import SkinManager
        from src.core.animation_manager import AnimationManager
        empty_mgr = SkinManager(skins_base_path=self.skins_dir)
        anim = AnimationManager(empty_mgr)
        anim.skin_name = "nonexistent_skin"
        self.assertFalse(anim.play("idle", loop=True))

    def test_stop(self):
        self.anim_mgr.play("idle")
        self.assertTrue(self.anim_mgr.is_playing)
        self.anim_mgr.stop()
        self.assertFalse(self.anim_mgr.is_playing)

    def test_pause_and_resume(self):
        self.anim_mgr.play("idle")
        self.anim_mgr.pause()
        self.anim_mgr.resume()
        self.assertTrue(self.anim_mgr.is_playing)

    def test_set_fps(self):
        self.anim_mgr.set_fps(20)
        self.assertEqual(self.anim_mgr.fps, 20)
        self.assertEqual(self.anim_mgr.interval, 50)

    def test_set_fps_clamp_low(self):
        self.anim_mgr.set_fps(0)
        self.assertEqual(self.anim_mgr.fps, 1)

    def test_set_fps_clamp_high(self):
        self.anim_mgr.set_fps(100)
        self.assertEqual(self.anim_mgr.fps, 60)

    def test_set_fps_updates_interval(self):
        self.anim_mgr.set_fps(30)
        self.assertEqual(self.anim_mgr.interval, int(1000 / 30))

    def test_set_fps_while_playing(self):
        self.anim_mgr.play("idle")
        self.anim_mgr.set_fps(15)
        self.assertTrue(self.anim_mgr.is_playing)
        self.assertEqual(self.anim_mgr.fps, 15)

    def test_get_current_frame(self):
        self.anim_mgr.play("idle")
        self.assertIsNotNone(self.anim_mgr.get_current_frame())

    def test_get_current_frame_no_frames(self):
        self.assertIsNone(self.anim_mgr.get_current_frame())

    def test_get_frame_count(self):
        self.anim_mgr.load_animation("idle")
        self.assertEqual(self.anim_mgr.get_frame_count(), 3)

    def test_set_skin(self):
        self.anim_mgr.set_skin("test")
        self.assertEqual(self.anim_mgr.skin_name, "test")

    def test_has_animation(self):
        self.assertTrue(self.anim_mgr.has_animation("idle"))
        self.assertTrue(self.anim_mgr.has_animation("walk"))
        self.assertFalse(self.anim_mgr.has_animation("nonexistent"))

    def test_animation_finished_signal_non_loop(self):
        """非循环动画播放完发出信号"""
        from PyQt6.QtTest import QSignalSpy
        self.anim_mgr.play("click", loop=False)
        spy = QSignalSpy(self.anim_mgr.animation_finished)
        self.assertTrue(spy.isValid())
        for _ in range(10):
            self.anim_mgr._next_frame()
        self.assertGreaterEqual(len(spy), 1)
        self.assertEqual(spy[0][0], "click")

    def test_animation_loop(self):
        """循环动画播放完不停止"""
        self.anim_mgr.play("idle", loop=True)
        for _ in range(20):
            self.anim_mgr._next_frame()
        self.assertTrue(self.anim_mgr.is_playing)

    def test_switch_animation_while_playing(self):
        """播放中切换动画"""
        self.anim_mgr.play("idle", loop=True)
        self.assertTrue(self.anim_mgr.play("walk", loop=True))
        self.assertEqual(self.anim_mgr.current_animation, "walk")
        self.assertTrue(self.anim_mgr.is_playing)


# ============================================================
# 6. 状态管理器测试
# ============================================================
@skip_no_pyqt6
class TestStateManager(unittest.TestCase):
    """测试 StateManager"""

    def setUp(self):
        _get_qapp()
        from src.core.state_manager import StateManager
        self.sm = StateManager()

    def tearDown(self):
        self.sm.stop()

    def test_initial_state(self):
        self.assertEqual(self.sm.hunger, 100)
        self.assertEqual(self.sm.mood, 100)
        self.assertEqual(self.sm.intimacy, 0)

    def test_set_state(self):
        self.sm.set_state(50, 30, 5)
        self.assertEqual(self.sm.hunger, 50)
        self.assertEqual(self.sm.mood, 30)
        self.assertEqual(self.sm.intimacy, 5)

    def test_set_state_clamp(self):
        self.sm.set_state(200, -50, -10)
        self.assertEqual(self.sm.hunger, 100)
        self.assertEqual(self.sm.mood, 0)
        self.assertEqual(self.sm.intimacy, 0)

    def test_feed(self):
        self.sm.feed()
        self.assertEqual(self.sm.hunger, 100)  # clamped
        self.assertEqual(self.sm.mood, 100)    # clamped
        self.assertEqual(self.sm.intimacy, 1)

    def test_feed_from_low(self):
        self.sm.set_state(20, 50, 0)
        self.sm.feed()
        self.assertEqual(self.sm.hunger, 70)
        self.assertEqual(self.sm.mood, 60)
        self.assertEqual(self.sm.intimacy, 1)

    def test_pet_action(self):
        self.sm.set_state(50, 50, 0)
        self.sm.pet()
        self.assertEqual(self.sm.mood, 70)  # 50 + 20
        self.assertEqual(self.sm.intimacy, 1)

    def test_intimacy_cap_per_minute(self):
        self.sm.set_state(50, 50, 0)
        for _ in range(30):
            self.sm.pet()
        self.assertEqual(self.sm.intimacy, 5)

    def test_feed_spam_no_extra_intimacy(self):
        self.sm.set_state(20, 50, 0)
        self.sm.feed()
        self.sm.feed()
        self.assertEqual(self.sm.intimacy, 2)
        self.sm.feed()
        self.assertEqual(self.sm.intimacy, 2)

    def test_decay_hunger(self):
        for _ in range(60):
            self.sm._tick()
        self.assertEqual(self.sm.hunger, 50)

    def test_decay_mood(self):
        for _ in range(60):
            self.sm._tick()
        self.assertEqual(self.sm.mood, 75)

    def test_decay_not_below_zero(self):
        self.sm.set_state(0, 0, 0)
        self.sm._tick()
        self.assertEqual(self.sm.hunger, 0)
        self.assertEqual(self.sm.mood, 0)

    def test_multiple_decays(self):
        for _ in range(120):
            self.sm._tick()
        self.assertEqual(self.sm.hunger, 0)
        self.assertEqual(self.sm.mood, 50)

    def test_get_mood_text_happy(self):
        self.sm.set_state(90, 90, 0)
        self.assertEqual(self.sm.get_mood_text(), "happy")

    def test_get_mood_text_normal(self):
        self.sm.set_state(50, 50, 0)
        self.assertEqual(self.sm.get_mood_text(), "normal")

    def test_get_mood_text_hungry(self):
        self.sm.set_state(0, 50, 0)
        self.assertEqual(self.sm.get_mood_text(), "hungry")

    def test_get_mood_text_sad_hunger(self):
        self.sm.set_state(15, 50, 0)
        self.assertEqual(self.sm.get_mood_text(), "sad")

    def test_get_mood_text_sad_mood(self):
        self.sm.set_state(50, 10, 0)
        self.assertEqual(self.sm.get_mood_text(), "sad")

    def test_should_play_sad_animation(self):
        self.sm.set_state(90, 90, 0)
        self.assertFalse(self.sm.should_play_sad_animation())
        self.sm.set_state(15, 50, 0)
        self.assertTrue(self.sm.should_play_sad_animation())
        self.sm.set_state(50, 10, 0)
        self.assertTrue(self.sm.should_play_sad_animation())

    def test_should_show_hungry_bubble(self):
        self.sm.set_state(5, 50, 0)
        self.assertFalse(self.sm.should_show_hungry_bubble())
        self.sm.set_state(0, 50, 0)
        self.assertTrue(self.sm.should_show_hungry_bubble())

    def test_reset_state(self):
        self.sm.set_state(20, 30, 50)
        self.sm.reset_state()
        self.assertEqual(self.sm.hunger, 100)
        self.assertEqual(self.sm.mood, 100)
        self.assertEqual(self.sm.intimacy, 0)

    def test_get_state_dict(self):
        self.sm.set_state(50, 30, 5)
        state = self.sm.get_state_dict()
        self.assertEqual(state["hunger"], 50)
        self.assertEqual(state["mood"], 30)
        self.assertEqual(state["intimacy"], 5)

    def test_set_decay_rates(self):
        self.sm.set_decay_rates(30.0, 15.0)
        self.assertEqual(self.sm.hunger_decay_per_minute, 30.0)
        self.assertEqual(self.sm.mood_decay_per_minute, 15.0)

    def test_set_decay_rates_clamp(self):
        self.sm.set_decay_rates(0.0, -1.0)
        self.assertEqual(self.sm.hunger_decay_per_minute, 0.0)
        self.assertEqual(self.sm.mood_decay_per_minute, 0.0)

    def test_signals_emitted_on_feed(self):
        from PyQt6.QtTest import QSignalSpy
        hunger_spy = QSignalSpy(self.sm.hunger_changed)
        mood_spy = QSignalSpy(self.sm.mood_changed)
        intimacy_spy = QSignalSpy(self.sm.intimacy_changed)

        self.sm.set_state(50, 50, 0)
        self.sm.feed()

        self.assertGreaterEqual(len(hunger_spy), 1)
        self.assertGreaterEqual(len(mood_spy), 1)
        self.assertGreaterEqual(len(intimacy_spy), 1)

    def test_state_critical_signal_hunger(self):
        from PyQt6.QtTest import QSignalSpy
        spy = QSignalSpy(self.sm.state_critical)
        self.sm.set_state(1, 100, 0)
        for _ in range(3):
            self.sm._tick()
        self.assertGreaterEqual(len(spy), 1)
        self.assertEqual(spy[0][0], "hunger")

    def test_state_critical_signal_mood(self):
        from PyQt6.QtTest import QSignalSpy
        spy = QSignalSpy(self.sm.state_critical)
        self.sm.set_state(100, 21, 0)
        for _ in range(3):
            self.sm._tick()
        self.assertGreaterEqual(len(spy), 1)
        self.assertEqual(spy[0][0], "mood")

    def test_feed_does_not_exceed_100(self):
        self.sm.set_state(80, 90, 0)
        self.sm.feed()
        self.assertEqual(self.sm.hunger, 100)
        self.assertEqual(self.sm.mood, 100)

    def test_pet_does_not_exceed_100(self):
        self.sm.set_state(80, 90, 0)
        self.sm.pet()
        self.assertEqual(self.sm.mood, 100)


# ============================================================
# 7. 对话气泡测试
# ============================================================
@skip_no_pyqt6
class TestSpeechBubble(unittest.TestCase):
    """测试 SpeechBubble"""

    def setUp(self):
        _get_qapp()
        from src.ui.speech_bubble import SpeechBubble
        self.bubble = SpeechBubble()

    def test_initial_hidden(self):
        self.assertFalse(self.bubble.isVisible())
        self.assertFalse(self.bubble.is_showing)

    def test_show_text(self):
        self.bubble.show_text("hello")
        self.assertTrue(self.bubble.is_showing)

    def test_show_empty_text_ignored(self):
        self.bubble.show_text("")
        self.assertFalse(self.bubble.is_showing)

    def test_show_none_text_ignored(self):
        self.bubble.show_text(None)
        self.assertFalse(self.bubble.is_showing)

    def test_set_duration(self):
        self.bubble.set_duration(5000)
        self.assertEqual(self.bubble.duration_ms, 5000)

    def test_set_duration_clamp(self):
        self.bubble.set_duration(100)
        self.assertEqual(self.bubble.duration_ms, 500)

    def test_move_above(self):
        """气泡位于宠物头顶居中"""
        self.bubble.show_text("test")
        self.bubble.resize(100, 30)
        self.bubble.move_above(100, 200, 150)
        self.assertEqual(self.bubble.x(), 125)  # 100 + (150 - 100) // 2
        self.assertEqual(self.bubble.y(), 160)  # 200 - 30 - 10

    def test_opacity_effect(self):
        self.assertIsNotNone(self.bubble.opacity_effect)
        self.assertAlmostEqual(self.bubble.opacity_effect.opacity(), 1.0, places=1)


# ============================================================
# 8. 右键菜单测试
# ============================================================
@skip_no_pyqt6
class TestContextMenu(unittest.TestCase):
    """测试 ContextMenu"""

    def setUp(self):
        _get_qapp()
        self.temp_dir = tempfile.mkdtemp()
        self.skins_dir = Path(self.temp_dir) / "skins"
        self.skins_dir.mkdir(parents=True, exist_ok=True)

        from src.ui.context_menu import ContextMenu
        from src.core.skin_manager import SkinManager
        from src.i18n import init_language

        init_language("zh_CN")

        # 创建测试皮肤
        _create_test_skin(self.skins_dir, "test_skin", {"idle": 1})
        skin_mgr = SkinManager(skins_base_path=self.skins_dir)

        self.menu = ContextMenu.__new__(ContextMenu)
        # 手动调用 QMenu.__init__ via super()
        from PyQt6.QtWidgets import QMenu
        QMenu.__init__(self.menu)
        # 设置需要的属性
        self.menu.pet_window = None
        self.menu.skin_mgr = skin_mgr
        self.menu._create_actions()
        self.menu._create_menu()

    def test_menu_has_required_actions(self):
        actions = [a.text() for a in self.menu.actions()]
        self.assertIn("喂食", actions)
        self.assertIn("抚摸", actions)
        self.assertIn("隐藏", actions)
        self.assertIn("退出程序", actions)
        self.assertIn("添加新宠物", actions)
        self.assertIn("设置", actions)

    def test_on_quit_does_not_crash(self):
        """退出动作不会崩溃"""
        self.menu._on_quit()  # QApplication.quit() 在测试环境中会被调用但不会真正退出


# ============================================================
# 9. 模块导入测试
# ============================================================
class TestModuleImports(unittest.TestCase):
    """测试所有模块可以正常导入"""

    def test_import_constants(self):
        from src.utils.constants import ANIMATION_IDLE, DEFAULT_FPS, DEFAULT_TEXT_POOLS

    def test_import_config_loader(self):
        from src.utils.config_loader import ConfigLoader

    @skip_no_pyqt6
    def test_import_data_persistence(self):
        from src.system.data_persistence import DataPersistence, Settings, PetData

    @skip_no_pyqt6
    def test_import_skin_manager(self):
        from src.core.skin_manager import SkinManager

    @skip_no_pyqt6
    def test_import_animation_manager(self):
        from src.core.animation_manager import AnimationManager

    @skip_no_pyqt6
    def test_import_state_manager(self):
        from src.core.state_manager import StateManager

    @skip_no_pyqt6
    def test_import_speech_bubble(self):
        from src.ui.speech_bubble import SpeechBubble

    @skip_no_pyqt6
    def test_import_context_menu(self):
        from src.ui.context_menu import ContextMenu

    @skip_no_pyqt6
    def test_import_tray_manager(self):
        from src.system.tray_manager import TrayManager

    @skip_no_pyqt6
    def test_import_pet_window(self):
        from src.ui.pet_window import PetWindow

    @skip_no_pyqt6
    def test_import_main(self):
        from src.main import DesktopPetApp, main


# ============================================================
# 10. 集成测试
# ============================================================
@skip_no_pyqt6
class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        _get_qapp()
        self.temp_dir = tempfile.mkdtemp()
        self.skins_dir = Path(self.temp_dir) / "skins"
        self.skins_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_patcher = patch("src.utils.config_loader.get_config_dir", return_value=self.config_dir)
        self.config_patcher.start()
        self.const_patcher = patch("src.utils.constants.get_config_dir", return_value=self.config_dir)
        self.const_patcher.start()

        _create_test_skin(self.skins_dir, "default", {"idle": 3, "click": 1, "sad": 1, "eat": 1, "happy": 1})

        self.addCleanup(self.config_patcher.stop)
        self.addCleanup(self.const_patcher.stop)

    def test_full_save_load_cycle(self):
        """完整的保存-加载周期"""
        from src.system.data_persistence import DataPersistence, PetData, Settings

        dp = DataPersistence()
        self.assertTrue(dp.save_settings(Settings(scale=1.5, fps=15)))

        pet = PetData(id="test-pet-1", skin_name="default", x=200, y=300, hunger=80, mood=60)
        self.assertTrue(dp.save_pets([pet]))

        dp2 = DataPersistence()
        loaded_s = dp2.load_settings()
        loaded_p = dp2.load_pets()
        self.assertEqual(loaded_s.scale, 1.5)
        self.assertEqual(len(loaded_p), 1)
        self.assertEqual(loaded_p[0].id, "test-pet-1")
        self.assertEqual(loaded_p[0].hunger, 80)

    def test_skin_manager_and_animation_manager_integration(self):
        """皮肤管理和动画管理器的集成"""
        from src.core.skin_manager import SkinManager
        from src.core.animation_manager import AnimationManager

        skin_mgr = SkinManager(skins_base_path=self.skins_dir)
        self.assertIn("default", skin_mgr.get_available_skins())

        anim_mgr = AnimationManager(skin_mgr)
        self.assertTrue(anim_mgr.play("idle"))
        self.assertEqual(anim_mgr.get_frame_count(), 3)
        self.assertTrue(anim_mgr.play("click", loop=False))

    def test_state_and_animation_interaction(self):
        """状态管理器与动画管理器的交互"""
        from src.core.state_manager import StateManager
        from src.core.skin_manager import SkinManager
        from src.core.animation_manager import AnimationManager

        state_mgr = StateManager()
        skin_mgr = SkinManager(skins_base_path=self.skins_dir)
        anim_mgr = AnimationManager(skin_mgr)

        state_mgr.set_state(10, 50, 0)
        self.assertTrue(state_mgr.should_play_sad_animation())
        self.assertTrue(anim_mgr.has_animation("sad"))

        state_mgr.feed()
        self.assertEqual(state_mgr.hunger, 60)
        self.assertFalse(state_mgr.should_play_sad_animation())
        state_mgr.stop()

    def test_data_corruption_recovery(self):
        """数据损坏恢复"""
        from src.system.data_persistence import DataPersistence

        settings_file = self.config_dir / "settings.json"
        settings_file.write_text("{invalid json content", encoding="utf-8")

        dp = DataPersistence()
        settings = dp.load_settings()
        self.assertIsNotNone(settings)
        from src.utils.constants import DEFAULT_SCALE
        self.assertEqual(settings.scale, DEFAULT_SCALE)

    def test_multiple_pets_data_management(self):
        """多宠物数据管理"""
        from src.system.data_persistence import DataPersistence, PetData

        dp = DataPersistence()
        pets = [PetData(id="p1", x=100, y=100), PetData(id="p2", x=200, y=200)]
        dp.save_pets(pets)

        loaded = dp.load_pets()
        self.assertEqual(len(loaded), 2)

        dp.remove_pet("p1")
        loaded = dp.load_pets()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].id, "p2")

    def test_placeholder_skin_creation_and_use(self):
        """创建占位皮肤并使用"""
        from src.core.skin_manager import SkinManager
        from src.core.animation_manager import AnimationManager

        skin_mgr = SkinManager(skins_base_path=self.skins_dir)
        self.assertNotIn("placeholder", skin_mgr.get_available_skins())

        skin_mgr.create_placeholder_skin("placeholder")
        skin_mgr.scan_skins()
        self.assertIn("placeholder", skin_mgr.get_available_skins())

        anim_mgr = AnimationManager(skin_mgr)
        self.assertTrue(anim_mgr.play("idle"))


# ============================================================
# 11. 静态代码分析
# ============================================================
class TestStaticCodeAnalysis(unittest.TestCase):
    """静态代码分析"""

    def test_all_source_files_exist(self):
        base = PROJECT_ROOT / "src"
        required = [
            "main.py", "__init__.py",
            "core/__init__.py", "core/animation_manager.py",
            "core/skin_manager.py", "core/state_manager.py",
            "ui/__init__.py", "ui/pet_window.py",
            "ui/speech_bubble.py", "ui/context_menu.py",
            "system/__init__.py", "system/data_persistence.py",
            "system/tray_manager.py",
            "utils/__init__.py", "utils/constants.py",
            "utils/config_loader.py",
        ]
        for f in required:
            self.assertTrue((base / f).exists(), f"Missing: {f}")

    def test_all_py_files_syntax_valid(self):
        import ast
        src_dir = PROJECT_ROOT / "src"
        for py_file in list(src_dir.glob("*.py")) + list(src_dir.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue
            with open(py_file, "r", encoding="utf-8") as f:
                try:
                    ast.parse(f.read())
                except SyntaxError as e:
                    self.fail(f"Syntax error in {py_file}: {e}")

    def test_encoding_utf8(self):
        for py_file in (PROJECT_ROOT / "src").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            with open(py_file, "r", encoding="utf-8") as f:
                f.read()  # Will raise UnicodeDecodeError if not UTF-8

    def test_no_hardcoded_secrets(self):
        for py_file in (PROJECT_ROOT / "src").rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            content = py_file.read_text(encoding="utf-8")
            for pattern in ["password =", "api_key =", "secret =", "token ="]:
                self.assertNotIn(pattern, content)


class TestI18n(unittest.TestCase):
    def test_default_english(self):
        from src.i18n import init_language, t, get_language, text_pool

        init_language("en")
        self.assertEqual(get_language(), "en")
        self.assertEqual(t("menu.feed"), "Feed")
        self.assertIn("Hi there!", text_pool("happy"))

    def test_chinese_locale(self):
        from src.i18n import init_language, t, text_pool

        init_language("zh_CN")
        self.assertEqual(t("menu.feed"), "喂食")
        self.assertIn("你好呀！", text_pool("happy"))

    def test_settings_language_field(self):
        from src.system.data_persistence import Settings

        s = Settings.from_dict({})
        self.assertEqual(s.language, "en")

    def test_all_locales_load(self):
        import json
        from pathlib import Path
        from src.i18n import SUPPORTED_LANGUAGES, init_language, t

        locales_dir = Path(__file__).resolve().parent.parent / "src" / "i18n" / "locales"
        self.assertEqual(len(SUPPORTED_LANGUAGES), 18)
        required_keys = (
            "menu.feed",
            "menu.settings",
            "settings.title",
            "game_hub.title",
            "store.title",
        )
        for code in SUPPORTED_LANGUAGES:
            path = locales_dir / f"{code}.json"
            self.assertTrue(path.exists(), f"missing locale file: {code}")
            json.loads(path.read_text(encoding="utf-8"))
            init_language(code)
            for key in required_keys:
                val = t(key)
                self.assertNotEqual(val, key, f"{code}: missing {key}")
                self.assertTrue(len(val) > 0)

    def test_settings_dialog_import(self):
        from src.ui.settings_dialog import SettingsDialog
        self.assertTrue(SettingsDialog)


class TestReleaseSmoke(unittest.TestCase):
    """Fast import / wiring checks before release."""

    def test_core_modules_import(self):
        import src.main  # noqa: F401
        import src.ui.pet_window  # noqa: F401
        import src.ui.settings_dialog  # noqa: F401
        import src.ui.game_hub_window  # noqa: F401
        import src.ui.store_window  # noqa: F401
        import src.i18n.translator  # noqa: F401

    def test_starting_gold_release_value(self):
        from src.utils.constants import DEV_MODE, DEFAULT_GOLD, STARTING_GOLD

        self.assertFalse(DEV_MODE)
        self.assertEqual(DEFAULT_GOLD, STARTING_GOLD)
        self.assertEqual(STARTING_GOLD, 80)

    def test_dutch_store_strings(self):
        from src.i18n import init_language, shop_item, t, text_pool

        init_language("nl")
        self.assertEqual(t("store.header_title"), "Winkel")
        self.assertEqual(shop_item("burger")["name"], "Hamburger")
        self.assertIn("Voeren", t("store.shop_hint"))
        self.assertNotEqual(text_pool("happy")[0], "Hi there!")

    def test_pet_window_text_pool(self):
        from src.i18n import init_language, text_pool

        init_language("en")
        self.assertGreater(len(text_pool("happy")), 0)
        init_language("zh_CN")
        self.assertIn("你好", text_pool("happy")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
