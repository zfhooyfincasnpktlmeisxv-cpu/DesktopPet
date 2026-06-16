"""机会 / 命运卡（参考开源 Monopoly 卡池结构，中文本地化）"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Literal, Optional

from .game_balance import PASS_START_SALARY

CardKind = Literal[
    "earn",
    "pay",
    "move_back",
    "goto",
    "goto_jail",
    "get_out_jail",
    "pay_everyone",
    "repairs",
]


@dataclass(frozen=True)
class CardDef:
    text: str
    kind: CardKind
    amount: int = 0
    position: int = -1
    house_repair: int = 0
    hotel_repair: int = 0


# 金额与 5000 起始资金匹配的快节奏卡池
CHANCE_CARDS: List[CardDef] = [
    CardDef("银行分红，获得 ¥300", "earn", 300),
    CardDef("房产出售获利，获得 ¥800", "earn", 800),
    CardDef("超速罚单，支付 ¥200", "pay", 200),
    CardDef("后退 3 格", "move_back"),
    CardDef(f"直达【上海】，路过起点领 ¥{PASS_START_SALARY}", "goto", position=5),
    CardDef("直达【北京】", "goto", position=20),
    CardDef(f"直达起点，领取 ¥{PASS_START_SALARY}", "goto", position=0),
    CardDef("进监狱！不得经过起点", "goto_jail"),
    CardDef("出狱许可（可保留至使用）", "get_out_jail"),
    CardDef("向每位玩家支付 ¥300", "pay_everyone", 300),
    CardDef("房屋维修：每栋 ¥150，每间酒店 ¥600", "repairs", house_repair=150, hotel_repair=600),
    CardDef("意外之财 ¥500", "earn", 500),
    CardDef("慈善捐款 ¥400", "pay", 400),
    CardDef(f"直达【成都】，路过起点领 ¥{PASS_START_SALARY}", "goto", position=14),
    CardDef("银行错误，获得 ¥250", "earn", 250),
    CardDef("医疗账单，支付 ¥450", "pay", 450),
]

FATE_CARDS: List[CardDef] = [
    CardDef("生日红包，获得 ¥600", "earn", 600),
    CardDef("继承遗产，获得 ¥1000", "earn", 1000),
    CardDef("缴纳所得税 ¥800", "pay", 800),
    CardDef("出狱许可（可保留至使用）", "get_out_jail"),
    CardDef("进监狱！不得经过起点", "goto_jail"),
    CardDef("直达【香港】", "goto", position=22),
    CardDef("银行利息，获得 ¥350", "earn", 350),
    CardDef("学校捐款 ¥300", "pay", 300),
    CardDef("房屋维修：每栋 ¥120，每间酒店 ¥500", "repairs", house_repair=120, hotel_repair=500),
    CardDef("旅游奖励，获得 ¥700", "earn", 700),
    CardDef("车辆维修，支付 ¥250", "pay", 250),
    CardDef("向每位玩家支付 ¥200", "pay_everyone", 200),
    CardDef("彩票中奖 ¥900", "earn", 900),
    CardDef("医院费用，支付 ¥500", "pay", 500),
    CardDef("社区奖励，获得 ¥400", "earn", 400),
    CardDef("奢侈税补征 ¥600", "pay", 600),
]


class CardDeck:
    def __init__(self, cards: List[CardDef]):
        self._cards = list(cards)
        self._discard: List[CardDef] = []
        self.shuffle()

    def shuffle(self) -> None:
        random.shuffle(self._cards)

    def draw(self) -> CardDef:
        if not self._cards:
            self._cards = self._discard
            self._discard = []
            self.shuffle()
        card = self._cards.pop()
        if card.kind != "get_out_jail":
            self._discard.append(card)
        return card


def new_decks() -> tuple[CardDeck, CardDeck]:
    return CardDeck(list(CHANCE_CARDS)), CardDeck(list(FATE_CARDS))
