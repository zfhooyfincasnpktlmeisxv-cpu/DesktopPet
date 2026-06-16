"""
右键菜单
喂食、抚摸、添加宠物、切换皮肤、设置、隐藏、退出
"""
import logging
from typing import Optional, List

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QWidget

from ..core.skin_manager import SkinManager
from ..i18n import t
from ..utils.constants import (
    ANIMATIONS,
    DEV_MODE,
)

logger = logging.getLogger(__name__)


class ContextMenu(QMenu):
    """
    右键菜单
    提供喂食、抚摸、添加宠物、切换皮肤、设置、隐藏、退出等功能
    """

    def __init__(self, parent: Optional[QWidget] = None, pet_window=None):
        """
        初始化右键菜单

        Args:
            parent: 父窗口
            pet_window: 宠物窗口实例（用于调用其方法）
        """
        super().__init__(parent)

        self.pet_window = pet_window
        self.skin_mgr = SkinManager()

        # 设置菜单样式（白色文字，透明背景）
        self.setStyleSheet("""
            QMenu {
                background-color: rgba(30, 30, 30, 220);
                color: white;
                border: 1px solid rgba(100, 100, 100, 150);
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 3px;
            }
            QMenu::item:selected {
                background-color: rgba(70, 130, 180, 180);
            }
            QMenu::separator {
                height: 1px;
                background-color: rgba(100, 100, 100, 100);
                margin: 4px 8px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
            }
        """)

        # 创建菜单项
        self._create_actions()
        self._create_menu()

        logger.info("右键菜单初始化完成")

    def _create_actions(self) -> None:
        """创建菜单动作"""
        # 喂食
        self.feed_action = QAction(t("menu.feed"), self)
        self.feed_action.triggered.connect(self._on_feed)

        # 抚摸
        self.pet_action = QAction(t("menu.pet"), self)
        self.pet_action.triggered.connect(self._on_pet)

        # 唤醒
        self.wake_action = QAction(t("menu.wake"), self)
        self.wake_action.triggered.connect(self._on_wake)
        self.wake_action.setVisible(False)

        # 添加新宠物
        self.add_pet_action = QAction(t("menu.add_pet"), self)
        self.add_pet_action.triggered.connect(self._on_add_pet)

        # 切换皮肤（子菜单）
        self.skin_menu = QMenu(t("menu.switch_skin"), self)

        # 状态栏显示
        self.stat_hud_action = QAction(t("menu.show_stat_hud"), self)
        self.stat_hud_action.setCheckable(True)
        self.stat_hud_action.triggered.connect(self._on_toggle_stat_hud)

        # 小商店 / 背包
        self.shop_action = QAction(t("menu.shop"), self)
        self.shop_action.triggered.connect(self._on_shop)
        self.backpack_action = QAction(t("menu.backpack"), self)
        self.backpack_action.triggered.connect(self._on_backpack)

        # 陪玩打工（小游戏）
        self.game_hub_action = QAction(t("menu.game_hub"), self)
        self.game_hub_action.triggered.connect(self._on_game_hub)

        # 设置
        self.settings_action = QAction(t("menu.settings"), self)
        self.settings_action.triggered.connect(self._on_settings)

        # 隐藏
        self.hide_action = QAction(t("menu.hide"), self)
        self.hide_action.triggered.connect(self._on_hide)

        # 退出程序
        self.quit_action = QAction(t("menu.quit"), self)
        self.quit_action.triggered.connect(self._on_quit)

        # 开发者：滑翔动作调试
        self.dev_glide_forward_action = QAction(t("menu.dev_glide_forward"), self)
        self.dev_glide_forward_action.triggered.connect(self._on_dev_glide_forward)
        self.dev_glide_backward_action = QAction(t("menu.dev_glide_backward"), self)
        self.dev_glide_backward_action.triggered.connect(self._on_dev_glide_backward)
        self.dev_glide_stop_action = QAction(t("menu.dev_glide_stop"), self)
        self.dev_glide_stop_action.triggered.connect(self._on_dev_glide_stop)

        self.dev_menu = QMenu(t("menu.dev"), self)
        self.dev_menu.addAction(self.dev_glide_forward_action)
        self.dev_menu.addAction(self.dev_glide_backward_action)
        self.dev_menu.addSeparator()
        self.dev_menu.addAction(self.dev_glide_stop_action)

    def _create_menu(self) -> None:
        """创建菜单结构"""
        # 添加动作
        self.addAction(self.feed_action)
        self.addAction(self.pet_action)
        self.addAction(self.wake_action)
        self.addSeparator()

        # 添加宠物菜单
        self.addAction(self.add_pet_action)

        # 添加皮肤子菜单
        self._populate_skin_menu()
        self.addMenu(self.skin_menu)
        self.addSeparator()

        self.addAction(self.stat_hud_action)
        self.addSeparator()

        self.addAction(self.shop_action)
        self.addAction(self.backpack_action)
        self.addAction(self.game_hub_action)
        self.addSeparator()

        # 设置
        self.addAction(self.settings_action)
        self.addSeparator()

        if DEV_MODE:
            self.addMenu(self.dev_menu)
            self.addSeparator()

        # 隐藏和退出
        self.addAction(self.hide_action)
        self.addAction(self.quit_action)

    def _populate_skin_menu(self) -> None:
        """填充皮肤子菜单"""
        self.skin_menu.clear()

        # 获取可用皮肤
        skins = self.skin_mgr.get_available_skins()

        if not skins:
            # 没有皮肤
            no_skin_action = QAction("（无可用皮肤）", self)
            no_skin_action.setEnabled(False)
            self.skin_menu.addAction(no_skin_action)
        else:
            # 添加每个皮肤选项
            for skin_name in skins:
                action = QAction(skin_name, self)
                action.triggered.connect(
                    lambda checked, name=skin_name: self._on_switch_skin(name)
                )
                self.skin_menu.addAction(action)

    def _on_feed(self) -> None:
        """喂食"""
        if self.pet_window:
            self.pet_window.feed()
            logger.info("菜单：喂食")

    def _on_pet(self) -> None:
        """抚摸"""
        if self.pet_window:
            self.pet_window.pet()
            logger.info("菜单：抚摸")

    def _on_wake(self) -> None:
        if self.pet_window and hasattr(self.pet_window, "action_mgr"):
            self.pet_window.action_mgr.wake_from_sleep()

    def _on_add_pet(self) -> None:
        """添加新宠物"""
        # 这里需要通知主程序添加新宠物
        # 通过信号或回调实现
        logger.info("菜单：添加新宠物")
        # TODO: 实现添加宠物的逻辑

    def _on_switch_skin(self, skin_name: str) -> None:
        """
        切换皮肤

        Args:
            skin_name: 皮肤名称
        """
        if self.pet_window:
            self.pet_window.set_skin(skin_name)
            logger.info(f"菜单：切换皮肤到 {skin_name}")

    def _on_shop(self) -> None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        pet_app = app.property("desktop_pet_app") if app else None
        if pet_app and hasattr(pet_app, "show_store"):
            pet_app.show_store(tab="shop")
            logger.info("菜单：小商店")

    def _on_backpack(self) -> None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        pet_app = app.property("desktop_pet_app") if app else None
        if pet_app and hasattr(pet_app, "show_store"):
            pet_app.show_store(tab="bag")
            logger.info("菜单：背包")

    def _on_game_hub(self) -> None:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        pet_app = app.property("desktop_pet_app") if app else None
        if pet_app and hasattr(pet_app, "show_game_hub"):
            pet_app.show_game_hub()
            logger.info("菜单：陪玩打工")

    def _on_settings(self) -> None:
        """打开设置"""
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        pet_app = app.property("desktop_pet_app") if app else None
        if pet_app and hasattr(pet_app, "_show_settings"):
            pet_app._show_settings()
            logger.info("Menu: settings")

    def _on_hide(self) -> None:
        """隐藏宠物"""
        if self.pet_window:
            self.pet_window.hide_pet()
            logger.info("菜单：隐藏宠物")

    def _on_quit(self) -> None:
        """退出程序"""
        logger.info("菜单：退出程序")
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        quit_fn = app.property("desktop_pet_quit") if app else None
        if callable(quit_fn):
            quit_fn()
        elif app:
            app.quit()

    def _on_dev_glide_forward(self) -> None:
        if self.pet_window:
            self.pet_window.debug_glide_forward()
            logger.info("开发者：正着飞")

    def _on_dev_glide_backward(self) -> None:
        if self.pet_window:
            self.pet_window.debug_glide_backward()
            logger.info("开发者：倒着飞")

    def _on_dev_glide_stop(self) -> None:
        if self.pet_window:
            self.pet_window.debug_stop_glide()
            logger.info("开发者：停止移动")

    def update_skin_menu(self) -> None:
        self._populate_skin_menu()

    def update_sleep_state(self, is_sleeping: bool) -> None:
        self.wake_action.setVisible(is_sleeping)
        self.pet_action.setEnabled(not is_sleeping)
        self._sleeping = is_sleeping
        self._apply_feed_state()

    def update_inventory_state(self, food_count: int, is_sleeping: bool | None = None) -> None:
        if is_sleeping is not None:
            self._sleeping = is_sleeping
        self._food_count = food_count
        self._apply_feed_state()

    def _apply_feed_state(self) -> None:
        sleeping = getattr(self, "_sleeping", False)
        count = getattr(self, "_food_count", 0)
        if count > 0:
            self.feed_action.setText(t("menu.feed_count", count=count))
        else:
            self.feed_action.setText(t("menu.feed"))
        self.feed_action.setEnabled(not sleeping)

    def update_stat_hud_state(self, visible: bool) -> None:
        self.stat_hud_action.blockSignals(True)
        self.stat_hud_action.setChecked(visible)
        self.stat_hud_action.blockSignals(False)

    def _on_toggle_stat_hud(self, checked: bool) -> None:
        if self.pet_window:
            self.pet_window.set_stat_hud_visible(checked)
            logger.info("菜单：状态栏 %s", "显示" if checked else "隐藏")

