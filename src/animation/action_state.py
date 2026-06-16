"""动作状态与优先级定义"""


class ActionState:
    IDLE = "idle"
    BLINK = "blink"
    WALK = "walk"
    SIT = "sit"
    EAT = "eat"
    SLEEP = "sleep"
    SAD = "sad"
    HAPPY = "happy"
    CLICK = "click"
    GRABBED = "grabbed"
    FALL = "fall"
    SPECIAL = "special"


class ActionPriority:
    """数值越小优先级越高"""

    DRAG = 1
    INTERACTION = 2
    WALK = 4
    BLINK = 5
    MOOD = 6
    IDLE = 9

    _MAP = {
        ActionState.GRABBED: DRAG,
        ActionState.EAT: INTERACTION,
        ActionState.CLICK: INTERACTION,
        ActionState.FALL: INTERACTION,
        ActionState.SPECIAL: INTERACTION,
        ActionState.WALK: WALK,
        ActionState.BLINK: BLINK,
        ActionState.SAD: MOOD,
        ActionState.HAPPY: MOOD,
        ActionState.SIT: MOOD,
        ActionState.SLEEP: MOOD,
        ActionState.IDLE: IDLE,
    }

    @classmethod
    def level(cls, state: str) -> int:
        return cls._MAP.get(state, cls.IDLE)

    @classmethod
    def can_interrupt(cls, current: str, requested: str) -> bool:
        if current == requested:
            return False
        if requested == ActionState.IDLE:
            return True
        # 拖拽释放后的 fall / 短按 click 必须能从 grabbed 切出
        if current == ActionState.GRABBED and requested in (
            ActionState.FALL,
            ActionState.CLICK,
            ActionState.IDLE,
        ):
            return True
        cur = cls.level(current)
        req = cls.level(requested)
        if req < cur:
            return True
        return False
