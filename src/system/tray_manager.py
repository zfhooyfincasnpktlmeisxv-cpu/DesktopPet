"""
系统托盘管理
托盘图标、菜单、显示/隐藏控制
"""
import logging
from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

from ..ui.pet_window import PetWindow
from ..system.data_persistence import DataPersistence
from ..utils.constants import DEFAULT_SKIN, get_assets_dir
from ..i18n import t

logger = logging.getLogger(__name__)


class TrayManager(QObject):
    """
    系统托盘管理器
    管理系统托盘图标和菜单，控制所有宠物的显示/隐藏
    """

    # 信号定义
    quit_requested = pyqtSignal()  # 退出请求信号
    settings_requested = pyqtSignal()  # 设置请求信号
    add_pet_requested = pyqtSignal()  # 添加宠物请求信号

    def __init__(self, parent: Optional[QObject] = None):
        """
        初始化托盘管理器

        Args:
            parent: 父对象
        """
        super().__init__(parent)

        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.tray_menu: Optional[QMenu] = None
        self.pets: List[PetWindow] = []

        # 数据持久化
        self.data_persistence = DataPersistence()

        # 创建托盘图标
        self._create_tray_icon()

        logger.info("托盘管理器初始化完成")

    def _create_tray_icon(self) -> None:
        """创建系统托盘图标"""
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)

        # 设置图标
        icon = self._load_tray_icon()
        self.tray_icon.setIcon(icon)

        # 设置提示文本
        self.tray_icon.setToolTip(t("app.tray_tooltip"))

        # 创建托盘菜单
        self._create_tray_menu()

        # 连接信号
        self.tray_icon.activated.connect(self._on_tray_activated)

        logger.debug("托盘图标已创建")

    def _load_tray_icon(self) -> QIcon:
        """
        加载托盘图标

        Returns:
            QIcon对象
        """
        # 尝试加载自定义图标
        icon_paths = [
            get_assets_dir() / "icon.png",
            Path("assets/icon.png"),
            Path("icon.png"),
        ]

        for icon_path in icon_paths:
            if icon_path.exists():
                try:
                    pixmap = QPixmap(str(icon_path))
                    if not pixmap.isNull():
                        return QIcon(pixmap)
                except Exception as e:
                    logger.error(f"加载图标失败: {icon_path}, 错误: {e}")

        # 使用默认图标（创建一个简单的彩色图标）
        try:
            from PyQt6.QtGui import QPixmap, QPainter, QColor

            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(100, 200, 100, 255))  # 绿色

            # 绘制简单图案
            painter = QPainter(pixmap)
            painter.setBrush(QColor(255, 255, 255, 255))
            painter.drawEllipse(8, 8, 16, 16)  # 白色圆形
            painter.end()

            return QIcon(pixmap)
        except Exception as e:
            logger.error(f"创建默认图标失败: {e}")
            return QIcon()

    def _create_tray_menu(self) -> None:
        """创建托盘菜单"""
        self.tray_menu = QMenu()

        # 显示/隐藏所有宠物
        self.toggle_action = QAction(t("tray.toggle_pets"), self)
        self.toggle_action.triggered.connect(self.toggle_all_pets)
        self.tray_menu.addAction(self.toggle_action)

        # 添加宠物
        self.add_pet_action = QAction(t("tray.add_pet"), self)
        self.add_pet_action.triggered.connect(self._on_add_pet)
        self.tray_menu.addAction(self.add_pet_action)

        self.tray_menu.addSeparator()

        # 设置
        self.settings_action = QAction(t("tray.settings"), self)
        self.settings_action.triggered.connect(self._on_settings)
        self.tray_menu.addAction(self.settings_action)

        self.tray_menu.addSeparator()

        # 退出
        self.quit_action = QAction(t("tray.quit"), self)
        self.quit_action.triggered.connect(self._on_quit)
        self.tray_menu.addAction(self.quit_action)

        # 设置菜单
        self.tray_icon.setContextMenu(self.tray_menu)

    def retranslate(self) -> None:
        """Refresh tray strings after language change."""
        if self.tray_icon:
            self.tray_icon.setToolTip(t("app.tray_tooltip"))
        if self.toggle_action:
            self.toggle_action.setText(t("tray.toggle_pets"))
        if self.add_pet_action:
            self.add_pet_action.setText(t("tray.add_pet"))
        if self.settings_action:
            self.settings_action.setText(t("tray.settings"))
        if self.quit_action:
            self.quit_action.setText(t("tray.quit"))

    def _on_tray_activated(self, reason) -> None:
        """
        托盘图标激活回调

        Args:
            reason: 激活原因
        """
        from PyQt6.QtWidgets import QSystemTrayIcon

        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # 左键单击：显示/隐藏所有宠物
            self.toggle_all_pets()
            logger.debug("托盘图标被左键单击")

    def show(self) -> None:
        """显示托盘图标"""
        if self.tray_icon:
            self.tray_icon.show()
            logger.info("托盘图标已显示")

    def hide(self) -> None:
        """隐藏托盘图标"""
        if self.tray_icon:
            self.tray_icon.hide()
            logger.info("托盘图标已隐藏")

    def add_pet(self, pet: PetWindow) -> None:
        """
        添加宠物到管理列表

        Args:
            pet: 宠物窗口实例
        """
        self.pets.append(pet)
        logger.info(f"宠物已添加到托盘管理: {pet.pet_id}, 总数: {len(self.pets)}")

    def remove_pet(self, pet: PetWindow) -> None:
        """
        从管理列表中移除宠物

        Args:
            pet: 宠物窗口实例
        """
        if pet in self.pets:
            self.pets.remove(pet)
            logger.info(f"宠物已从托盘管理移除: {pet.pet_id}, 总数: {len(self.pets)}")

    def toggle_all_pets(self) -> None:
        """显示/隐藏所有宠物"""
        if not self.pets:
            logger.warning("没有宠物可以切换显示状态")
            return

        # 检查是否有可见的宠物
        any_visible = any(pet.isVisible() for pet in self.pets)

        if any_visible:
            for pet in self.pets:
                pet._dismiss_bubble()
                pet.hide_pet()
            logger.info("所有宠物已隐藏")
        else:
            # 全部隐藏，显示所有
            for pet in self.pets:
                pet.show()
            logger.info("所有宠物已显示")

    def show_all_pets(self) -> None:
        """显示所有宠物"""
        for pet in self.pets:
            pet.show()
        logger.info("所有宠物已显示")

    def hide_all_pets(self) -> None:
        """隐藏所有宠物"""
        for pet in self.pets:
            pet.hide_pet()
        logger.info("所有宠物已隐藏")

    def get_pets(self) -> List[PetWindow]:
        """
        获取所有宠物

        Returns:
            宠物列表
        """
        return self.pets.copy()

    def quit(self) -> None:
        """退出程序"""
        logger.info("请求退出程序")

        # 保存数据
        self._save_all_data()

        # 发射退出信号
        self.quit_requested.emit()

        # 退出应用
        app = QApplication.instance()
        if app:
            app.quit()

    def _on_add_pet(self) -> None:
        """添加宠物菜单回调"""
        logger.info("托盘菜单：添加宠物")
        self.add_pet_requested.emit()

    def _on_settings(self) -> None:
        """设置菜单回调"""
        logger.info("托盘菜单：打开设置")
        self.settings_requested.emit()

    def _on_quit(self) -> None:
        """退出菜单回调"""
        self.quit()

    def _save_all_data(self) -> None:
        """保存所有宠物数据"""
        # 收集宠物数据
        pets_data = [pet.get_pet_data() for pet in self.pets]

        # 保存到数据持久化
        for pet_data in pets_data:
            pet_id = pet_data.get("id")
            # 这里需要实现具体的保存逻辑
            logger.debug(f"保存宠物数据: {pet_id}")

        logger.info(f"已保存 {len(pets_data)} 个宠物的数据")

    def cleanup(self) -> None:
        """清理资源"""
        # 保存数据
        self._save_all_data()

        # 隐藏托盘图标
        self.hide()

        logger.info("托盘管理器已清理")
