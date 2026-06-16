"""小商店 + 背包窗口（与桌宠同套奶油粉主题）"""
from __future__ import annotations

import logging
from typing import Dict, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..i18n import shop_item, t
from ..utils.constants import FEED_FOOD_ITEM_IDS, SHOP_CATALOG, STORE_THEME

if TYPE_CHECKING:
    from ..core.inventory_manager import InventoryManager

logger = logging.getLogger(__name__)


def _rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]}, {c[1]}, {c[2]})"


def _stylesheet(theme: dict) -> str:
    bg = _rgb(theme["background"])
    border = _rgb(theme["border"])
    accent = _rgb(theme["accent"])
    accent_hover = _rgb(theme["accent_hover"])
    text = _rgb(theme["text"])
    return f"""
QDialog {{
    background-color: {bg};
}}
QLabel {{
    color: {text};
    background: transparent;
}}
QTabWidget::pane {{
    border: 1px solid {border};
    border-radius: {theme["radius"]}px;
    background: white;
    top: -1px;
}}
QTabBar::tab {{
    background: rgb(255, 244, 248);
    color: rgb(120, 110, 115);
    padding: 9px 22px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background: white;
    color: {text};
    font-weight: 700;
}}
QPushButton#primary {{
    background-color: {accent};
    color: {text};
    border: none;
    border-radius: 9px;
    padding: 9px 18px;
    font-weight: 600;
    min-width: 72px;
}}
QPushButton#primary:hover {{
    background-color: {accent_hover};
}}
QPushButton#primary:disabled {{
    background-color: rgb(235, 225, 230);
    color: rgb(160, 155, 158);
}}
QPushButton#ghost {{
    background-color: transparent;
    color: rgb(120, 110, 115);
    border: 1px solid {border};
    border-radius: 9px;
    padding: 8px 16px;
}}
QPushButton#ghost:hover {{
    background-color: rgb(255, 244, 248);
}}
QSpinBox {{
    border: 1px solid {border};
    border-radius: 8px;
    padding: 5px 8px;
    background: white;
    min-height: 28px;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
"""


class StoreWindow(QDialog):
    """小商店与背包。"""

    def __init__(
        self,
        inventory_mgr: "InventoryManager",
        *,
        initial_tab: str = "shop",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._inv = inventory_mgr
        self._theme = STORE_THEME
        self._buy_buttons: Dict[str, QPushButton] = {}
        self._qty_spinboxes: Dict[str, QSpinBox] = {}
        self._header_title: Optional[QLabel] = None

        self.setWindowTitle(t("store.title"))
        self.setModal(False)
        self.setMinimumSize(self._theme["width"], self._theme["min_height"])
        self.resize(self._theme["width"], self._theme["min_height"])
        self.setStyleSheet(_stylesheet(self._theme))

        font = QFont(self._theme["font_family"], 10)
        self.setFont(font)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 14)
        root.setSpacing(12)

        root.addWidget(self._build_header())

        self._tabs = QTabWidget()
        self._shop_scroll = QScrollArea()
        self._shop_scroll.setWidgetResizable(True)
        self._shop_inner = QWidget()
        self._shop_layout = QVBoxLayout(self._shop_inner)
        self._shop_layout.setContentsMargins(4, 4, 4, 4)
        self._shop_layout.setSpacing(10)
        self._shop_scroll.setWidget(self._shop_inner)

        self._bag_scroll = QScrollArea()
        self._bag_scroll.setWidgetResizable(True)
        self._bag_inner = QWidget()
        self._bag_layout = QVBoxLayout(self._bag_inner)
        self._bag_layout.setContentsMargins(4, 4, 4, 4)
        self._bag_layout.setSpacing(8)
        self._bag_scroll.setWidget(self._bag_inner)

        self._tabs.addTab(self._shop_scroll, f"🛒 {t('store.shop_tab')}")
        self._tabs.addTab(self._bag_scroll, f"🎒 {t('store.bag_tab')}")
        root.addWidget(self._tabs, stretch=1)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setMinimumHeight(22)
        root.addWidget(self._status_label)

        self._close_btn = QPushButton(t("store.close"))
        self._close_btn.setObjectName("ghost")
        self._close_btn.clicked.connect(self.close)
        root.addWidget(self._close_btn)

        self._build_shop_items()
        self.show_store_tab(initial_tab)

    def show_store_tab(self, tab: str) -> None:
        self._tabs.setCurrentIndex(1 if tab == "bag" else 0)
        self.refresh()

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {_rgb(self._theme['gold_bg'])};"
            f" border: 1px solid {_rgb(self._theme['gold_border'])};"
            f" border-radius: {self._theme['radius']}px; }}"
        )
        row = QHBoxLayout(frame)
        row.setContentsMargins(14, 12, 14, 12)

        self._header_title = QLabel(t("store.header_title"))
        self._header_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        row.addWidget(self._header_title)

        row.addStretch(1)

        self._gold_label = QLabel()
        self._gold_label.setStyleSheet(
            f"color: {_rgb(self._theme['gold_text'])}; font-size: 14px; font-weight: 700;"
        )
        row.addWidget(self._gold_label)

        return frame

    def _clear_shop_layout(self) -> None:
        while self._shop_layout.count() > 0:
            item = self._shop_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._buy_buttons.clear()
        self._qty_spinboxes.clear()

    def _build_shop_items(self) -> None:
        hint = QLabel(t("store.shop_hint"))
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px; padding: 2px 4px 6px 4px;"
        )
        self._shop_layout.addWidget(hint)

        for item_id, meta in SHOP_CATALOG.items():
            self._shop_layout.addWidget(self._make_shop_card(item_id, meta))

        self._shop_layout.addStretch(1)

    def _make_shop_card(self, item_id: str, meta: dict) -> QFrame:
        i18n = shop_item(item_id)
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {_rgb(self._theme['card_bg'])};"
            f" border: 1px solid {_rgb(self._theme['border_soft'])};"
            f" border-radius: {self._theme['radius']}px; }}"
        )
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(12)

        icon = QLabel(str(meta.get("emoji", "📦")))
        icon.setFixedSize(44, 44)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "font-size: 22px; background: white; border-radius: 22px;"
            f" border: 1px solid {_rgb(self._theme['border_soft'])};"
        )
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(i18n.get("name", item_id))
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        price = QLabel(t("store.price_each", price=meta["price"]))
        price.setStyleSheet(f"color: {_rgb(self._theme['gold_text'])}; font-size: 12px;")
        desc = QLabel(i18n.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        info.addWidget(title)
        info.addWidget(price)
        info.addWidget(desc)
        row.addLayout(info, stretch=1)

        controls = QVBoxLayout()
        controls.setSpacing(6)
        qty_row = QHBoxLayout()
        qty_label = QLabel(t("store.quantity"))
        qty_label.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        qty = QSpinBox()
        qty.setRange(1, 99)
        qty.setValue(1)
        qty.setFixedWidth(68)
        qty.valueChanged.connect(lambda _v: self._update_buy_buttons())
        qty_row.addWidget(qty_label)
        qty_row.addWidget(qty)
        controls.addLayout(qty_row)

        buy_btn = QPushButton(t("store.buy"))
        buy_btn.setObjectName("primary")
        buy_btn.clicked.connect(lambda _c=False, iid=item_id: self._on_buy(iid))
        controls.addWidget(buy_btn)

        self._buy_buttons[item_id] = buy_btn
        self._qty_spinboxes[item_id] = qty
        row.addLayout(controls)
        return card

    def _make_bag_row(self, item_id: str, count: int) -> QFrame:
        meta = SHOP_CATALOG.get(item_id, {})
        i18n = shop_item(item_id)
        name = i18n.get("name", meta.get("name", item_id))
        emoji = meta.get("emoji", "📦")
        is_food = item_id in FEED_FOOD_ITEM_IDS

        row = QFrame()
        row.setStyleSheet(
            f"QFrame {{ background: white; border: 1px solid {_rgb(self._theme['border_soft'])};"
            f" border-radius: 10px; }}"
        )
        h = QHBoxLayout(row)
        h.setContentsMargins(12, 10, 12, 10)

        icon = QLabel(str(emoji))
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"font-size: 18px; background: {_rgb(self._theme['card_bg'])}; border-radius: 18px;"
        )
        h.addWidget(icon)

        texts = QVBoxLayout()
        texts.setSpacing(0)
        name_lbl = QLabel(str(name))
        name_lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        tag = t("store.tag_food") if is_food else t("store.tag_item")
        sub = QLabel(tag)
        sub.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 10px;")
        texts.addWidget(name_lbl)
        texts.addWidget(sub)
        h.addLayout(texts, stretch=1)

        count_lbl = QLabel(f"× {count}")
        count_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        h.addWidget(count_lbl)
        return row

    def _qty(self, item_id: str) -> int:
        spin = self._qty_spinboxes.get(item_id)
        return spin.value() if spin else 1

    def _on_buy(self, item_id: str) -> None:
        qty = self._qty(item_id)
        meta = SHOP_CATALOG.get(item_id, {})
        price = int(meta.get("price", 0)) * qty

        if not self._inv.can_afford(item_id, qty):
            need = price - self._inv.gold
            self._set_status(t("store.not_enough_gold", need=need), error=True)
            return

        if self._inv.buy(item_id, qty):
            i18n = shop_item(item_id)
            name = i18n.get("name", item_id)
            emoji = meta.get("emoji", "")
            self._set_status(
                t("store.buy_success", emoji=emoji, name=name, qty=qty)
            )
            self.refresh()
        else:
            self._set_status(t("store.buy_fail"), error=True)

    def _set_status(self, text: str, *, error: bool = False) -> None:
        color = _rgb(self._theme["error"] if error else self._theme["success"])
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _update_buy_buttons(self) -> None:
        for item_id, btn in self._buy_buttons.items():
            qty = self._qty(item_id)
            btn.setEnabled(self._inv.can_afford(item_id, qty))

    def retranslate_ui(self) -> None:
        self.setWindowTitle(t("store.title"))
        if self._header_title:
            self._header_title.setText(t("store.header_title"))
        self._tabs.setTabText(0, f"🛒 {t('store.shop_tab')}")
        self._tabs.setTabText(1, f"🎒 {t('store.bag_tab')}")
        self._close_btn.setText(t("store.close"))
        self._clear_shop_layout()
        self._build_shop_items()
        self.refresh()

    def refresh(self) -> None:
        self._gold_label.setText(t("store.gold", amount=self._inv.gold))
        self._update_buy_buttons()

        while self._bag_layout.count() > 0:
            item = self._bag_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        inv = self._inv.inventory
        food_count = self._inv.feed_food_count()

        summary = QFrame()
        summary.setStyleSheet(
            f"QFrame {{ background: {_rgb(self._theme['card_bg'])};"
            f" border: 1px solid {_rgb(self._theme['border_soft'])}; border-radius: 10px; }}"
        )
        s_layout = QHBoxLayout(summary)
        s_layout.setContentsMargins(12, 8, 12, 8)
        s1 = QLabel(t("store.bag_item_kinds", count=len(inv)))
        s1.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        s2 = QLabel(t("store.bag_feedable", count=food_count))
        s2.setStyleSheet(f"color: {_rgb(self._theme['text_muted'])}; font-size: 11px;")
        s_layout.addWidget(s1)
        s_layout.addStretch(1)
        s_layout.addWidget(s2)
        self._bag_layout.addWidget(summary)

        if not inv:
            empty = QLabel(t("store.empty_bag_hint"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(
                f"color: {_rgb(self._theme['text_muted'])}; padding: 32px 16px; font-size: 12px;"
            )
            self._bag_layout.addWidget(empty)
        else:
            for item_id, count in sorted(inv.items()):
                self._bag_layout.addWidget(self._make_bag_row(item_id, count))

        self._bag_layout.addStretch(1)
        logger.debug("商店窗口已刷新")
