"""
系统层初始化文件
导入数据持久化和托盘管理模块
"""

from .data_persistence import DataPersistence
from .tray_manager import TrayManager

__all__ = [
    'DataPersistence',
    'TrayManager',
]
