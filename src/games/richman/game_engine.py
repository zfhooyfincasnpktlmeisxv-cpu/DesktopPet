"""大富翁规则引擎（M2：经典玩法 — 卡池 / 监狱 / 盖房 / 垄断）"""
from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ...utils.constants import RICHMAN_PACE
from .board_data import (
    INITIAL_MONEY,
    TAX_AMOUNT,
    TileKind,
    all_tiles,
    get_tile,
    tile_count,
)
from .cards import CardDef, new_decks
from .game_balance import JAIL_BAIL, PASS_START_SALARY, START_BONUS
from .property_rules import build_house as apply_build, can_build_on, compute_rent
from .player_avatars import default_avatar_id
from .player_setup import PlayerSlot


class GamePhase(str, Enum):
    WAIT_ROLL = "wait_roll"
    MOVING = "moving"
    ACTION = "action"
    RESOLVING = "resolving"
    GAME_OVER = "game_over"


@dataclass
class PlayerState:
    id: int
    name: str
    is_human: bool
    money: int = INITIAL_MONEY
    position: int = 0
    bankrupt: bool = False
    in_jail: bool = False
    pending_jail_skip: bool = False
    jail_free_cards: int = 0
    avatar_id: str = "preset_0"
    avatar_path: Optional[str] = None


@dataclass
class PropertyState:
    owner_id: Optional[int] = None
    level: int = 0


def _jail_tile_index() -> int:
    for tile in all_tiles():
        if tile.kind == TileKind.JAIL:
            return tile.index
    return 9


class RichmanEngine(QObject):
    """可绑定 UI 的规则状态机。"""

    state_changed = pyqtSignal()
    log_message = pyqtSignal(str)
    dice_rolled = pyqtSignal(int, int)
    card_drawn = pyqtSignal(str, str)
    player_stepped = pyqtSignal(int, int)
    player_moved = pyqtSignal(int, int)
    movement_finished = pyqtSignal(int)
    phase_changed = pyqtSignal(str)
    game_over = pyqtSignal(int)
    game_event = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._players: List[PlayerState] = []
        self._properties: Dict[int, PropertyState] = {
            i: PropertyState() for i in range(tile_count())
        }
        self._chance_deck, self._fate_deck = new_decks()
        self._current = 0
        self._phase = GamePhase.WAIT_ROLL
        self._last_dice = (0, 0)
        self._winner_id: Optional[int] = None
        self._turn_number = 1
        self._steps_remaining = 0
        self._move_passed_start = False
        self._move_start_pos = 0
        self._move_total_steps = 0
        self._pending_finish = False
        self._step_timer = QTimer(self)
        self._step_timer.setSingleShot(True)
        self._step_timer.timeout.connect(self._on_step_timer)

    @property
    def phase(self) -> GamePhase:
        return self._phase

    @property
    def current_player(self) -> PlayerState:
        return self._players[self._current]

    @property
    def turn_number(self) -> int:
        return self._turn_number

    @property
    def is_moving(self) -> bool:
        return self._phase == GamePhase.MOVING

    def players(self) -> List[PlayerState]:
        return list(self._players)

    def property_at(self, index: int) -> PropertyState:
        return self._properties[index]

    def winner_id(self) -> Optional[int]:
        return self._winner_id

    def is_human_turn(self) -> bool:
        p = self.current_player
        return (
            p.is_human
            and not p.bankrupt
            and self._phase not in (GamePhase.GAME_OVER, GamePhase.MOVING)
        )

    def new_game(
        self,
        human_name: str = "主人",
        roster: Optional[List[tuple[str, bool]]] = None,
        players: Optional[List[PlayerSlot]] = None,
    ) -> None:
        if players is not None:
            if not 2 <= len(players) <= 4:
                raise ValueError("玩家数量需为 2～4 人")
            if not any(s.is_human for s in players):
                raise ValueError("至少需要一名本地玩家")
            self._players = [
                PlayerState(
                    i,
                    s.name.strip() or f"玩家{i + 1}",
                    s.is_human,
                    avatar_id=s.avatar_id,
                    avatar_path=s.avatar_path,
                )
                for i, s in enumerate(players)
            ]
        else:
            if roster is None:
                roster = [
                    (human_name, True),
                    ("小蓝", False),
                    ("小粉", False),
                    ("小橙", False),
                ]
            if not 2 <= len(roster) <= 4:
                raise ValueError("玩家数量需为 2～4 人")
            if not any(is_human for _, is_human in roster):
                raise ValueError("至少需要一名本地玩家")
            self._players = [
                PlayerState(
                    i,
                    name.strip() or f"玩家{i + 1}",
                    is_human,
                    avatar_id=default_avatar_id(i),
                )
                for i, (name, is_human) in enumerate(roster)
            ]
        self._properties = {i: PropertyState() for i in range(tile_count())}
        self._chance_deck, self._fate_deck = new_decks()
        self._current = 0
        self._phase = GamePhase.WAIT_ROLL
        self._winner_id = None
        self._turn_number = 1
        humans = sum(1 for p in self._players if p.is_human)
        bots = len(self._players) - humans
        self.log_message.emit("新对局开始！快节奏：高租金 · 购地盖房 · 监狱停一回合")
        self.log_message.emit(
            f"{len(self._players)} 人对战 · 本地 {humans} 人 · 电脑 {bots} 人"
        )
        self.log_message.emit(f"第 {self._turn_number} 轮 · 轮到 {self._players[0].name}")
        self._emit_all()

    def can_roll(self) -> bool:
        p = self.current_player
        return (
            self._phase == GamePhase.WAIT_ROLL
            and not p.bankrupt
            and not p.pending_jail_skip
        )

    def can_pay_jail_bail(self) -> bool:
        p = self.current_player
        return (
            self._phase == GamePhase.WAIT_ROLL
            and p.pending_jail_skip
            and p.money >= JAIL_BAIL
        )

    def can_use_jail_free(self) -> bool:
        p = self.current_player
        return (
            self._phase == GamePhase.WAIT_ROLL
            and p.pending_jail_skip
            and p.jail_free_cards > 0
        )

    def use_jail_free_card(self) -> bool:
        if not self.can_use_jail_free():
            return False
        p = self.current_player
        p.jail_free_cards -= 1
        p.pending_jail_skip = False
        p.in_jail = False
        self.log_message.emit(f"{p.name} 使用出狱许可，本回合可掷骰")
        self.state_changed.emit()
        return True

    def pay_jail_bail(self) -> bool:
        if not self.can_pay_jail_bail():
            return False
        p = self.current_player
        p.money -= JAIL_BAIL
        p.pending_jail_skip = False
        p.in_jail = False
        self.log_message.emit(f"{p.name} 交 ¥{JAIL_BAIL} 保释，本回合可掷骰")
        self.state_changed.emit()
        return True

    def can_skip_jail_turn(self) -> bool:
        p = self.current_player
        return self._phase == GamePhase.WAIT_ROLL and p.pending_jail_skip and not p.bankrupt

    def skip_jail_turn(self) -> bool:
        if not self.can_skip_jail_turn():
            return False
        p = self.current_player
        p.pending_jail_skip = False
        self.log_message.emit(f"{p.name} 在监狱中停一回合，跳过掷骰")
        self._request_turn_end()
        return True

    def roll_dice(self) -> bool:
        if not self.can_roll():
            return False
        p = self.current_player
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        self._last_dice = (d1, d2)
        self.dice_rolled.emit(d1, d2)
        self.log_message.emit(f"{p.name} 掷出 {d1}+{d2}={d1 + d2} 点")

        self._phase = GamePhase.MOVING
        self.phase_changed.emit(self._phase.value)
        self._advance_steps(d1 + d2)
        return True

    def _advance_steps(self, steps: int) -> None:
        if steps <= 0:
            self._finish_movement()
            return
        p = self.current_player
        self._move_start_pos = p.position
        self._move_passed_start = False
        self._move_total_steps = steps
        self._steps_remaining = steps
        self._pending_finish = False
        self._do_step()

    def _step_delay_ms(self) -> int:
        pace = RICHMAN_PACE
        return int(pace["step_hop_ms"]) + int(pace["step_gap_ms"])

    def _hop_delay_ms(self) -> int:
        return int(RICHMAN_PACE["step_hop_ms"])

    def _do_step(self) -> None:
        p = self.current_player
        jail_idx = _jail_tile_index()
        if p.in_jail and p.position == jail_idx:
            p.in_jail = False
        nxt = (p.position + 1) % tile_count()
        if nxt == 0 and p.position != 0:
            self._move_passed_start = True
        p.position = nxt
        self._steps_remaining -= 1
        self.player_stepped.emit(p.id, p.position)
        self.state_changed.emit()
        if self._steps_remaining > 0:
            self._pending_finish = False
            self._step_timer.start(self._step_delay_ms())
        else:
            self._pending_finish = True
            self._step_timer.start(self._step_delay_ms())

    def _on_step_timer(self) -> None:
        if self._pending_finish:
            self._pending_finish = False
            self._finish_movement()
        else:
            self._do_step()

    def _finish_movement(self) -> None:
        p = self.current_player
        old_pos = self._move_start_pos
        steps = self._move_total_steps
        if self._move_passed_start:
            p.money += PASS_START_SALARY
            self.log_message.emit(f"{p.name} 经过起点，领取 ¥{PASS_START_SALARY}")
            self.game_event.emit("pass_start")
        if p.position == 0 and steps > 0 and old_pos == 0:
            p.money += START_BONUS
        self._resolve_tile()
        self.movement_finished.emit(p.id)
        self.state_changed.emit()

    def _resolve_tile(self) -> None:
        p = self.current_player
        tile = get_tile(p.position)
        if tile.kind == TileKind.PROPERTY:
            prop = self._properties[p.position]
            if prop.owner_id is None:
                self._phase = GamePhase.ACTION
                self.log_message.emit(f"抵达【{tile.name}】，可购买 ¥{tile.price}")
            elif prop.owner_id != p.id:
                rent = compute_rent(tile, prop, self._properties)
                self._pay_player(p.id, prop.owner_id, rent, f"租金【{tile.name}】")
                self.game_event.emit("rent")
                self._request_turn_end()
            else:
                lvl = prop.level
                hint = f"（{lvl} 级建筑）" if lvl else ""
                self.log_message.emit(f"{p.name} 在自己的【{tile.name}】{hint}")
                self._request_turn_end()
        elif tile.kind == TileKind.TAX:
            p.money = max(0, p.money - TAX_AMOUNT)
            self.log_message.emit(f"{p.name} 缴纳税款 ¥{TAX_AMOUNT}")
            self.game_event.emit("tax")
            self._check_bankrupt(p)
            self._request_turn_end()
        elif tile.kind == TileKind.CHANCE:
            self.game_event.emit("card")
            self._draw_card("chance")
        elif tile.kind == TileKind.FATE:
            self.game_event.emit("card")
            self._draw_card("fate")
        elif tile.kind == TileKind.GO_TO_JAIL:
            self._send_to_jail(p)
            self._request_turn_end()
        elif tile.kind == TileKind.JAIL:
            if p.in_jail or p.pending_jail_skip:
                self.log_message.emit(f"{p.name} 在监狱中服刑")
            else:
                self.log_message.emit(f"{p.name} 只是路过监狱格（未入狱）")
            self._request_turn_end()
        elif tile.kind == TileKind.PARKING:
            self.log_message.emit(f"{p.name} 在免费停车区歇脚")
            self._request_turn_end()
        elif tile.kind == TileKind.START:
            self.log_message.emit(f"{p.name} 停在起点")
            self._request_turn_end()
        else:
            self._request_turn_end()
        self.phase_changed.emit(self._phase.value)

    def _draw_card(self, deck_name: str) -> None:
        deck = self._chance_deck if deck_name == "chance" else self._fate_deck
        card = deck.draw()
        label = "机会" if deck_name == "chance" else "命运"
        self.log_message.emit(f"{label}：{card.text}")
        self.card_drawn.emit(deck_name, card.text)
        self._apply_card(card)

    def _apply_card(self, card: CardDef) -> None:
        p = self.current_player
        if card.kind == "earn":
            p.money += card.amount
            self._request_turn_end()
        elif card.kind == "pay":
            p.money = max(0, p.money - card.amount)
            self._check_bankrupt(p)
            self._request_turn_end()
        elif card.kind == "move_back":
            for _ in range(3):
                p.position = (p.position - 1) % tile_count()
                self.player_stepped.emit(p.id, p.position)
            self.state_changed.emit()
            self.log_message.emit(f"{p.name} 后退 3 格")
            self._resolve_tile()
        elif card.kind == "goto":
            self._move_to_tile(card.position)
        elif card.kind == "goto_jail":
            self._send_to_jail(p)
            self._request_turn_end()
        elif card.kind == "get_out_jail":
            p.jail_free_cards += 1
            self.log_message.emit(f"{p.name} 获得出狱许可（持有 {p.jail_free_cards} 张）")
            self._request_turn_end()
        elif card.kind == "pay_everyone":
            for other in self._players:
                if other.id == p.id or other.bankrupt:
                    continue
                self._pay_player(p.id, other.id, card.amount, "机会卡分摊")
            self._request_turn_end()
        elif card.kind == "repairs":
            total = 0
            for idx, prop in self._properties.items():
                if prop.owner_id != p.id:
                    continue
                if prop.level >= 4:
                    total += card.hotel_repair
                elif prop.level > 0:
                    total += card.house_repair * prop.level
            p.money = max(0, p.money - total)
            self.log_message.emit(f"{p.name} 维修费 ¥{total}")
            self._check_bankrupt(p)
            self._request_turn_end()

    def _move_to_tile(self, target: int) -> None:
        p = self.current_player
        if target < 0:
            self._request_turn_end()
            return
        steps = (target - p.position) % tile_count()
        if steps == 0 and target == 0 and p.position != 0:
            steps = tile_count()
        self._phase = GamePhase.MOVING
        self.phase_changed.emit(self._phase.value)
        self._advance_steps(steps if steps > 0 else tile_count())

    def _send_to_jail(self, p: PlayerState) -> None:
        jail = _jail_tile_index()
        p.position = jail
        p.in_jail = True
        p.pending_jail_skip = True
        self.player_moved.emit(p.id, jail)
        self.log_message.emit(f"{p.name} 被送进监狱！下回合须停骰（可交保释金 ¥{JAIL_BAIL}）")
        self.game_event.emit("jail")

    def _pay_player(self, from_id: int, to_id: int, amount: int, reason: str) -> None:
        debtor = self._players[from_id]
        creditor = self._players[to_id]
        if amount <= 0:
            return
        if debtor.money < amount:
            pay = debtor.money
            debtor.money = 0
            creditor.money += pay
            self.log_message.emit(
                f"{debtor.name} 无力支付 ¥{amount}，实付 ¥{pay} 后破产（{reason}）"
            )
            self._check_bankrupt(debtor)
            return
        debtor.money -= amount
        creditor.money += amount
        self.log_message.emit(
            f"{debtor.name} 向 {creditor.name} 支付 ¥{amount}（{reason}）"
        )

    def _check_bankrupt(self, p: PlayerState) -> None:
        if p.money <= 0 and not p.bankrupt:
            p.bankrupt = True
            p.in_jail = False
            p.pending_jail_skip = False
            self.log_message.emit(f"{p.name} 破产出局！")
            for idx, prop in self._properties.items():
                if prop.owner_id == p.id:
                    prop.owner_id = None
                    prop.level = 0
            self._check_winner()

    def _check_winner(self) -> None:
        alive = [pl for pl in self._players if not pl.bankrupt]
        if len(alive) <= 1:
            self._phase = GamePhase.GAME_OVER
            self._winner_id = alive[0].id if alive else None
            if self._winner_id is not None:
                self.log_message.emit(f"🎉 {alive[0].name} 获胜！")
                self.game_event.emit("win")
                self.game_over.emit(self._winner_id)
            self.phase_changed.emit(self._phase.value)

    def can_buy_current(self) -> bool:
        if self._phase != GamePhase.ACTION:
            return False
        p = self.current_player
        tile = get_tile(p.position)
        if tile.kind != TileKind.PROPERTY:
            return False
        prop = self._properties[p.position]
        return prop.owner_id is None and p.money >= tile.price

    def can_skip_current(self) -> bool:
        if self.can_skip_jail_turn():
            return True
        if self._phase != GamePhase.ACTION:
            return False
        tile = get_tile(self.current_player.position)
        if tile.kind != TileKind.PROPERTY:
            return False
        return self._properties[self.current_player.position].owner_id is None

    def can_build_house(self) -> bool:
        if self._phase not in (GamePhase.WAIT_ROLL, GamePhase.ACTION):
            return False
        p = self.current_player
        if p.pending_jail_skip:
            return False
        return can_build_on(p.position, p.id, p.money, self._properties)

    def build_house(self) -> bool:
        p = self.current_player
        if not can_build_on(p.position, p.id, p.money, self._properties):
            return False
        cost = apply_build(p.position, p.id, self._properties)
        p.money -= cost
        tile = get_tile(p.position)
        lvl = self._properties[p.position].level
        self.log_message.emit(f"{p.name} 在【{tile.name}】盖房 ¥{cost} → {lvl} 级")
        self.game_event.emit("build")
        self.state_changed.emit()
        return True

    def buy_current_property(self) -> bool:
        if not self.can_buy_current():
            return False
        p = self.current_player
        tile = get_tile(p.position)
        p.money -= tile.price
        self._properties[p.position].owner_id = p.id
        self.log_message.emit(f"{p.name} 购入【{tile.name}】¥{tile.price}")
        self.game_event.emit("buy")
        self._end_turn()
        return True

    def skip_action(self) -> None:
        if self.can_skip_jail_turn():
            self.skip_jail_turn()
            return
        if not self.can_skip_current():
            return
        self.log_message.emit(f"{self.current_player.name} 放弃购买")
        self._end_turn()

    def _request_turn_end(self) -> None:
        if self._phase == GamePhase.GAME_OVER:
            return
        self._phase = GamePhase.RESOLVING
        self.phase_changed.emit(self._phase.value)
        self.state_changed.emit()

    def complete_turn(self) -> None:
        if self._phase != GamePhase.RESOLVING:
            return
        self._end_turn()

    def _end_turn(self) -> None:
        if self._phase == GamePhase.GAME_OVER:
            return
        self._phase = GamePhase.WAIT_ROLL
        self._current = (self._current + 1) % len(self._players)
        while self._players[self._current].bankrupt:
            self._current = (self._current + 1) % len(self._players)
            if self._phase == GamePhase.GAME_OVER:
                return
        if self._current == 0:
            self._turn_number += 1
        self.phase_changed.emit(self._phase.value)
        self.state_changed.emit()
        cp = self.current_player
        self.log_message.emit(f"第 {self._turn_number} 轮 · 轮到 {cp.name}")

    def bot_take_turn(self) -> None:
        p = self.current_player
        if p.bankrupt or p.is_human or self._phase == GamePhase.GAME_OVER:
            return
        if self._phase == GamePhase.WAIT_ROLL:
            if p.pending_jail_skip:
                if p.jail_free_cards > 0 and random.random() < 0.55:
                    self.use_jail_free_card()
                    return
                if p.money >= JAIL_BAIL and random.random() < 0.35:
                    self.pay_jail_bail()
                    return
                self.skip_jail_turn()
                return
            if self.can_build_house() and random.random() < 0.35:
                self.build_house()
                return
            self.roll_dice()
        elif self._phase == GamePhase.ACTION:
            if self.can_buy_current() and random.random() < 0.7:
                self.buy_current_property()
            elif self.can_build_house() and random.random() < 0.5:
                self.build_house()
            elif self.can_skip_current():
                self.skip_action()
        elif self._phase == GamePhase.RESOLVING:
            self.complete_turn()

    def _emit_all(self) -> None:
        self.state_changed.emit()
        self.phase_changed.emit(self._phase.value)
