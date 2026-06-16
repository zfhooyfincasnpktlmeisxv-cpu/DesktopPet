"""
主入口
完整的启动逻辑，加载配置、创建托盘、恢复宠物实例
"""
import logging
import sys
from pathlib import Path
from typing import List, Optional

# 确保项目根目录在 import 路径中（支持 python src/main.py 启动）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class DesktopPetApp(QObject):
    """
    Desktop Pet 主应用类
    管理整个应用程序的生命周期
    """

    def __init__(self, argv: List[str]):
        """
        初始化应用

        Args:
            argv: 命令行参数
        """
        super().__init__()

        # 创建QApplication
        self.app = QApplication(argv)
        self.app.setApplicationName("DesktopPet")
        self.app.setQuitOnLastWindowClosed(False)  # 最后一个窗口关闭时不退出
        self.app.setProperty("desktop_pet_quit", self.quit)
        self.app.setProperty("desktop_pet_app", self)

        # 应用组件
        self.tray_manager: Optional["TrayManager"] = None
        self.pets: List["PetWindow"] = []

        # 数据持久化
        self.data_persistence = None
        self.inventory_mgr = None
        self.economy_mgr = None
        self._store_window = None
        self._game_hub_window = None
        self._save_timer: Optional[QTimer] = None
        self._save_debounce_ms = 3000

        # 初始化
        self._init_app()

        logger.info("Desktop Pet 应用初始化完成")

    def _init_app(self) -> None:
        """初始化应用组件"""
        try:
            # 导入模块（延迟导入以避免循环导入）
            from src.system.data_persistence import DataPersistence
            from src.core.inventory_manager import InventoryManager
            from src.core.economy_manager import EconomyManager
            from src.system.tray_manager import TrayManager
            from src.ui.pet_window import PetWindow
            from src.utils.constants import DEFAULT_SCALE

            # 初始化数据持久化
            self.data_persistence = DataPersistence()
            self.inventory_mgr = InventoryManager(self.data_persistence, parent=self)
            self.inventory_mgr.inventory_changed.connect(self._on_inventory_changed)
            self.economy_mgr = EconomyManager(
                self.data_persistence,
                inventory_mgr=self.inventory_mgr,
                parent=self,
            )
            self.economy_mgr.gold_changed.connect(self._on_economy_changed)
            self._save_timer = QTimer(self)
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self._save_all_pets)

            # 加载设置
            settings = self.data_persistence.load_settings()
            logger.info(f"设置已加载: {settings}")

            from src.i18n import init_language
            init_language(getattr(settings, "language", "en") or "en")

            # 创建托盘管理器
            self.tray_manager = TrayManager()

            # 连接信号
            self.tray_manager.quit_requested.connect(self.quit)
            self.tray_manager.settings_requested.connect(self._show_settings)
            self.tray_manager.add_pet_requested.connect(self._add_new_pet)

            from src.core.skin_manager import SkinManager
            from src.utils.constants import ANIMATION_IDLE
            from src.i18n import t

            skin_mgr = SkinManager()
            if (
                "default" not in skin_mgr.available_skins
                or not skin_mgr.has_animation("default", ANIMATION_IDLE)
            ):
                from PyQt6.QtWidgets import QMessageBox

                QMessageBox.critical(
                    None,
                    t("messages.missing_skin_title"),
                    t("messages.missing_skin_body"),
                )
                logger.error("皮肤资源缺失，已提示用户")

            # 加载宠物数据
            pets_data = self.data_persistence.load_pets()

            if not pets_data:
                # 没有保存的宠物数据，创建默认宠物
                logger.info("没有保存的宠物数据，创建默认宠物")
                default_pet_data = self.data_persistence.create_default_pet()
                pets_data = [default_pet_data]
                self.data_persistence.save_pets([default_pet_data])

            # 恢复宠物实例
            for pet_data in pets_data:
                self._create_pet(pet_data)

            # 显示托盘图标
            self.tray_manager.show()
            if self.tray_manager.tray_icon:
                from src.i18n import t

                any_visible = any(p.isVisible() for p in self.pets)
                tip = t(
                    "tray.startup_visible" if any_visible else "tray.startup_hidden"
                )
                self.tray_manager.tray_icon.showMessage(
                    t("app.name"),
                    tip,
                    self.tray_manager.tray_icon.MessageIcon.Information,
                    8000,
                )
                self.tray_manager.retranslate()

            logger.info(f"应用启动完成，共 {len(self.pets)} 个宠物")

        except Exception as e:
            logger.error(f"应用初始化失败: {e}", exc_info=True)
            raise

    def _create_pet(self, pet_data) -> "PetWindow":
        """
        创建宠物实例

        Args:
            pet_data: 宠物数据（PetData对象或字典）

        Returns:
            创建的宠物窗口实例
        """
        from src.ui.pet_window import PetWindow
        from src.system.data_persistence import PetData, apply_offline_stat_decay

        # 如果是字典，转换为PetData对象
        if isinstance(pet_data, dict):
            pet_obj = PetData.from_dict(pet_data)
        else:
            pet_obj = pet_data

        settings = self.data_persistence.get_settings() if self.data_persistence else None
        if settings:
            pet_obj = apply_offline_stat_decay(pet_obj, settings)
        auto_walk = bool(settings.auto_walk_enabled) if settings else True
        show_hud = bool(settings.show_stat_hud) if settings else False

        pet = PetWindow(
            pet_id=getattr(pet_obj, 'id', 'default-id'),
            skin_name=getattr(pet_obj, 'skin_name', 'default'),
            auto_walk_enabled=auto_walk,
            show_stat_hud=show_hud,
        )

        # 恢复状态
        pet.restore_state({
            "x": pet_obj.x,
            "y": pet_obj.y,
            "skin_name": pet_obj.skin_name,
            "scale": pet_obj.scale,
            "hunger": pet_obj.hunger,
            "mood": pet_obj.mood,
            "intimacy": pet_obj.intimacy,
            "is_visible": pet_obj.is_visible,
        })

        # 连接信号
        pet.closed.connect(lambda: self._on_pet_closed(pet))
        pet.position_changed.connect(lambda x, y: self._on_pet_moved(pet))
        pet.stat_hud_changed.connect(self._on_stat_hud_changed)
        self._connect_pet_autosave(pet)

        # 添加到管理列表
        self.pets.append(pet)
        if self.tray_manager:
            self.tray_manager.add_pet(pet)

        # 显示宠物
        if pet_obj.is_visible:
            pet.show()

        logger.info(f"宠物已创建: {pet_obj.id}")
        return pet

    def _add_new_pet(self) -> None:
        """添加新宠物"""
        # 检查是否达到上限
        settings = self.data_persistence.get_settings()
        max_pets = settings.max_pets if settings else 5

        if len(self.pets) >= max_pets:
            logger.warning(f"已达到宠物数量上限: {max_pets}")
            return

        # 创建新宠物数据
        from src.system.data_persistence import PetData
        import uuid

        # 计算位置（错开显示）
        base_x = 100 + len(self.pets) * 50
        base_y = 100 + len(self.pets) * 50

        new_pet_data = PetData(
            id=str(uuid.uuid4()),
            skin_name="default",
            x=base_x,
            y=base_y,
            scale=DEFAULT_SCALE,
            hunger=100,
            mood=100,
            intimacy=0,
            is_visible=True,
        )

        # 创建宠物实例
        self._create_pet(new_pet_data)

        # 保存数据
        self._save_all_pets()

        logger.info(f"新宠物已添加，总数: {len(self.pets)}")

    def _on_pet_closed(self, pet: "PetWindow") -> None:
        """宠物窗口关闭 = 隐藏到托盘，保留实例"""
        logger.info(f"宠物窗口隐藏: {pet.pet_id}")
        self._save_all_pets()

    def _on_pet_moved(self, pet: "PetWindow") -> None:
        """
        宠物移动回调

        Args:
            pet: 移动的宠物窗口
        """
        # 保存位置（debounce 写入 pets.json）
        self._schedule_save()

    def show_store(self, tab: str = "shop") -> None:
        """打开小商店 / 背包窗口。"""
        from src.ui.store_window import StoreWindow

        if self._store_window is None:
            self._store_window = StoreWindow(self.inventory_mgr)
        self._store_window.show_store_tab(tab)
        self._store_window.show()
        self._store_window.raise_()
        self._store_window.activateWindow()

    def begin_game_session(self) -> None:
        """单局小游戏开始：宠物移到屏幕右侧固定旁观。"""
        for pet in self.pets:
            if pet.isVisible():
                pet.enter_game_spectator_mode()

    def end_game_session(self) -> None:
        """单局小游戏结束：恢复宠物位置与交互。"""
        for pet in self.pets:
            pet.leave_game_spectator_mode()

    def on_richman_finished(self, human_won: bool) -> None:
        """大富翁对局结束奖励。"""
        if not self.pets:
            return
        pet = self.pets[0]
        gold = 0
        hit_cap = False
        if human_won and self.economy_mgr:
            from src.utils.constants import GAME_RICHMAN_ID, RICHMAN_FEATURE

            score = int(RICHMAN_FEATURE["reward_win_score"])
            gold, hit_cap = self.economy_mgr.award_game_reward(GAME_RICHMAN_ID, score)
        if gold > 0:
            pet.show_bubble_pool("game_win")
            pet.action_mgr.on_user_interaction()
            pet.action_mgr.trigger_happy()
        elif hit_cap:
            pet.show_bubble_pool("game_daily_cap")
        logger.info("大富翁结束 human_won=%s gold=%s", human_won, gold)

    def on_chess_finished(self, human_won: bool) -> None:
        """国际象棋对局结束奖励。"""
        if not self.pets:
            return
        pet = self.pets[0]
        gold = 0
        hit_cap = False
        if human_won and self.economy_mgr:
            from src.utils.constants import GAME_CHESS_ID, CHESS_FEATURE

            score = int(CHESS_FEATURE["reward_win_score"])
            gold, hit_cap = self.economy_mgr.award_game_reward(GAME_CHESS_ID, score)
        if gold > 0:
            pet.show_bubble_pool("game_win")
            pet.action_mgr.on_user_interaction()
            pet.action_mgr.trigger_happy()
        elif hit_cap:
            pet.show_bubble_pool("game_daily_cap")
        logger.info("国际象棋结束 human_won=%s gold=%s", human_won, gold)

    def show_game_hub(self, game_id: str | None = None) -> None:
        """打开陪玩打工小游戏中心；可指定直接开始某游戏。"""
        from src.ui.game_hub_window import GameHubWindow

        if self.economy_mgr is None:
            return

        if self._game_hub_window is None:
            self._game_hub_window = GameHubWindow(
                self.economy_mgr,
                on_reward=self._on_game_reward,
            )
        self._game_hub_window.refresh()
        self._game_hub_window.show()
        self._game_hub_window.raise_()
        self._game_hub_window.activateWindow()

        if game_id == "snake":
            self._game_hub_window.play_snake()

    def _on_game_reward(self, score: int, gold: int, hit_cap: bool) -> None:
        """小游戏结算：宠物气泡 + 少量心情。"""
        if not self.pets:
            return
        pet = self.pets[0]
        if gold > 0:
            pet.show_bubble_pool("game_win")
            pet.action_mgr.on_user_interaction()
            pet.action_mgr.trigger_happy()
        elif hit_cap:
            pet.show_bubble_pool("game_daily_cap")
        logger.info("小游戏结算 score=%s gold=%s cap=%s", score, gold, hit_cap)

    def _on_inventory_changed(self) -> None:
        if self._store_window is not None and self._store_window.isVisible():
            self._store_window.refresh()

    def _on_economy_changed(self) -> None:
        if self._store_window is not None and self._store_window.isVisible():
            self._store_window.refresh()
        if self._game_hub_window is not None and self._game_hub_window.isVisible():
            self._game_hub_window.refresh()

    def _connect_pet_autosave(self, pet: "PetWindow") -> None:
        """数值、位置变化时延迟写入存档。"""
        pet.state_mgr.hunger_changed.connect(lambda _: self._schedule_save())
        pet.state_mgr.mood_changed.connect(lambda _: self._schedule_save())
        pet.state_mgr.intimacy_changed.connect(lambda _: self._schedule_save())
        pet.position_changed.connect(lambda _x, _y: self._schedule_save())

    def _schedule_save(self) -> None:
        if self._save_timer is not None:
            self._save_timer.start(self._save_debounce_ms)

    def _on_stat_hud_changed(self, visible: bool) -> None:
        if self.data_persistence:
            self.data_persistence.update_settings(show_stat_hud=visible)
            logger.info("状态栏显示: %s", visible)

    def _show_settings(self) -> None:
        """显示设置面板"""
        from src.ui.settings_dialog import SettingsDialog
        from src.i18n import set_language

        settings = self.data_persistence.get_settings()
        if settings is None:
            return

        dialog = SettingsDialog(settings, on_save=self._on_settings_saved, parent=None)
        dialog.exec()

    def _on_settings_saved(self, settings) -> None:
        from src.i18n import set_language

        self.data_persistence.save_settings(settings)
        set_language(settings.language)
        if self.tray_manager:
            self.tray_manager.retranslate()
        for pet in self.pets:
            pet.apply_settings(settings)
        if self._game_hub_window is not None:
            self._game_hub_window.retranslate_ui()
        if self._store_window is not None:
            self._store_window.retranslate_ui()
        logger.info("Settings saved (language=%s)", settings.language)

    def _save_all_pets(self) -> None:
        """保存所有宠物数据"""
        if not self.data_persistence:
            return

        # 收集宠物数据
        pets_data = []
        for pet in self.pets:
            pet_data = pet.get_pet_data()
            pets_data.append(pet_data)

        # 保存
        self.data_persistence.save_pets(pets_data)
        logger.debug(f"已保存 {len(pets_data)} 个宠物的数据（含好感/饱食/心情）")

    def run(self) -> int:
        """
        运行应用

        Returns:
            退出代码
        """
        logger.info("应用开始运行")
        return self.app.exec()

    def quit(self) -> None:
        """退出应用"""
        logger.info("应用正在退出...")

        # 保存所有数据
        self._save_all_pets()

        if self.data_persistence:
            settings = self.data_persistence.get_settings()
            if settings:
                self.data_persistence.save_settings(settings)

        # 清理资源
        if self.tray_manager:
            self.tray_manager.cleanup()

        # 关闭所有宠物窗口与气泡
        for pet in self.pets:
            pet.shutdown()
        self.pets.clear()

        # 退出应用
        self.app.quit()
        logger.info("应用已退出")


def main() -> int:
    """
    主函数

    Returns:
        退出代码
    """
    try:
        # 创建应用实例
        app = DesktopPetApp(sys.argv)

        # 运行应用
        return app.run()

    except Exception as e:
        logger.error(f"应用运行失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
