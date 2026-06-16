"""
常量定义文件
定义动画名称、默认配置值、文本池等常量
"""
import os
from pathlib import Path

# ============== 动画名称常量 ==============
# 必需的动画（必须有）
ANIMATION_IDLE = "idle"           # 待机动画
ANIMATION_WALK = "walk"           # 行走动画
ANIMATION_GRABBED = "grabbed"     # 被抓起动画
ANIMATION_FALL = "fall"           # 掉落动画
ANIMATION_CLICK = "click"         # 点击动画
ANIMATION_SAD = "sad"            # 伤心动画
ANIMATION_EAT = "eat"            # 进食动画
ANIMATION_HAPPY = "happy"        # 开心动画
ANIMATION_HOVER = "hover"        # 悬停动画
ANIMATION_SLEEP = "sleep"         # 睡眠动画

# 特殊动画（可选）
ANIMATION_SPECIAL1 = "special1"   # 特殊动画1
ANIMATION_SPECIAL2 = "special2"   # 特殊动画2

# 所有动画名称列表
ANIMATIONS = [
    ANIMATION_IDLE,
    ANIMATION_WALK,
    ANIMATION_GRABBED,
    ANIMATION_FALL,
    ANIMATION_CLICK,
    ANIMATION_SAD,
    ANIMATION_EAT,
    ANIMATION_HAPPY,
    ANIMATION_HOVER,
    ANIMATION_SLEEP,
    ANIMATION_SPECIAL1,
    ANIMATION_SPECIAL2,
]

# ============== 默认配置值 ==============
# 动画帧率（FPS）
DEFAULT_FPS = 10

# 宠物缩放范围
DEFAULT_SCALE = 0.5   # 默认缩放到50%，原素材256x426太大
MIN_SCALE = 0.3
MAX_SCALE = 1.5

# 透明度范围
DEFAULT_OPACITY = 1.0
MIN_OPACITY = 0.3
MAX_OPACITY = 1.0

# 状态衰减（每分钟掉多少点，量表 0~100）
HUNGER_DECAY_PER_MINUTE = 50   # 约 2 分钟从满到空
MOOD_DECAY_PER_MINUTE = 25     # 约 4 分钟从满到空
# 兼容 settings 字段名（语义：每分钟）
HUNGER_DECAY_RATE = HUNGER_DECAY_PER_MINUTE
MOOD_DECAY_RATE = MOOD_DECAY_PER_MINUTE
INTIMACY_THRESHOLD = 10        # 兼容旧设置项；解锁逻辑请用 intimacy_level
# 好感等级曲线：每升一级所需经验 = BASE + STEP * (当前等级 - 1)
INTIMACY_LEVEL_BASE = 4          # Lv.1 → Lv.2 需 4 点
INTIMACY_LEVEL_STEP = 3          # 每级再 +3（Lv.2→3 需 7，Lv.3→4 需 10…）

# 互动限速（滚动窗口，防刷好感）
INTERACTION_WINDOW_SEC = 60
FEED_MAX_PER_MINUTE = 2        # 每分钟最多 2 次「完整喂食」
PET_MAX_PER_MINUTE = 8         # 每分钟最多 8 次「完整抚摸」（含点击）
INTIMACY_MAX_GAIN_PER_MINUTE = 5  # 每分钟好感度最多 +5
INTERACTION_DIMINISH_RATIO = 0.25  # 超限后属性恢复倍率

# 开发者模式：右键菜单显示动作调试项（发布时可改为 False）
DEV_MODE = False

# 商店与背包
STARTING_GOLD = 80
DEFAULT_GOLD = 9999 if DEV_MODE else STARTING_GOLD
DAILY_GOLD_CAP = 250
FEED_ITEM_ID = "burger"
# 可用于喂食的食物 ID（按顺序消耗，方便以后加新食物）
FEED_FOOD_ITEM_IDS = ("burger",)
SHOP_CATALOG = {
    "burger": {
        "name": "汉堡",
        "emoji": "🍔",
        "price": 5,
        "description": "喂食时消耗，恢复饱食与少量心情",
        "feed_consumable": True,
    },
}

# 小游戏（第三阶段：打工挣钱）
GAME_SNAKE_ID = "snake"
GAME_CATCH_ID = "catch"
GAME_DODGE_ID = "dodge"
GAME_MEMORY_ID = "memory"
GAME_RICHMAN_ID = "richman"
GAME_CHESS_ID = "chess"

GAME_CATALOG = {
    GAME_SNAKE_ID: {
        "name": "贪吃蛇",
        "emoji": "🐍",
        "description": "方向键或 WASD 控制，陪宠物吃小汉堡赚金币",
        "reward_base": 5,
        "reward_per_food": 2,
    },
    GAME_CATCH_ID: {
        "name": "接汉堡",
        "emoji": "🍔",
        "description": "← → 移动接盘，接住汉堡躲开炸弹，坚持 60 秒",
        "reward_base": 4,
        "reward_per_food": 2,
    },
    GAME_DODGE_ID: {
        "name": "流星躲避",
        "emoji": "☄️",
        "description": "方向键躲避流星，存活越久金币越多",
        "reward_base": 3,
        "reward_per_food": 1,
    },
    GAME_MEMORY_ID: {
        "name": "美食记忆",
        "emoji": "🧠",
        "description": "点击翻牌配对美食，90 秒内全部配对",
        "reward_base": 5,
        "reward_per_food": 3,
    },
}

# 旗舰：大富翁（独立会话窗口，非轻量 widget）
RICHMAN_FEATURE = {
    "id": GAME_RICHMAN_ID,
    "name": "大富翁",
    "emoji": "🎲",
    "description": "3D 棋盘旗舰对局 · 购地收租成为首富",
    "reward_base": 30,
    "reward_win_score": 8,
    "reward_per_food": 5,
}

# 旗舰：国际象棋
CHESS_FEATURE = {
    "id": GAME_CHESS_ID,
    "name": "国际象棋",
    "emoji": "♟",
    "description": "经典 8×8 对局 · 人机或双人同屏",
    "reward_base": 20,
    "reward_win_score": 6,
    "reward_per_food": 4,
}

# 大富翁节奏：AI 每步 3–5 秒；人类回合无自动推进（上限 10 秒供后续扩展）
RICHMAN_PACE = {
    "bot_delay_min_ms": 3000,
    "bot_delay_max_ms": 5000,
    "human_max_buffer_ms": 10000,
    "human_resolve_ms": 2500,
    "bot_resolve_ms": 2000,
    "step_hop_ms": 480,
    "step_gap_ms": 140,
}

# 小游戏窗口 — 深色科技风
GAME_THEME = {
    "font_family": "Microsoft YaHei UI",
    "radius": 10,
    "background": (14, 18, 28),
    "surface": (22, 28, 42),
    "surface_border": (48, 64, 96),
    "accent": (0, 200, 255),
    "accent_hover": (80, 220, 255),
    "accent_glow": (0, 200, 255),
    "text": (218, 228, 242),
    "text_muted": (110, 128, 158),
    "text_accent": (0, 210, 255),
    "gold_text": (255, 198, 120),
    "danger": (255, 88, 108),
    "success": (72, 220, 160),
    "grid_bg": (16, 22, 34),
    "grid_line": (36, 48, 72),
    "snake_head": (0, 230, 190),
    "snake_body": (0, 150, 210),
    "food": (255, 150, 70),
    "panel_glow": (0, 180, 255),
}

# 贪吃蛇局内桌宠台词（显示在顶部反馈框）
SNAKE_FEEDBACK = {
    "start": [
        "一起冲！我会盯着汉堡的～",
        "加油！方向键或 WASD，我们配合！",
        "准备好啦？第一个汉堡在等你！",
    ],
    "food": [
        "好吃！再来一个！",
        "耶！又吃到啦～",
        "这方向感，绝了！",
        "汉堡 +1，金币在涨！",
    ],
    "milestone_3": ["三连击！手感火热！"],
    "milestone_5": ["五分餐！你是高手！"],
    "milestone_10": ["十个！太强了，我眼睛都花了！"],
    "danger": [
        "小心！要撞上了！",
        "快转弯！危险危险！",
        "别贴边！我在替你捏汗～",
    ],
    "long": [
        "蛇蛇好长！好厉害～",
        "这么长还能躲，佩服！",
    ],
    "death": [
        "呜呜撞到了…再来一局？",
        "差一点点！下次一定行！",
        "没关系，我陪你再战！",
    ],
}

CATCH_FEEDBACK = {
    "start": [
        "汉堡雨来啦！左右移动接盘～",
        "接住好吃的，躲开炸弹！",
        "我负责喊加油，你负责接！",
    ],
    "catch": [
        "接住了！好稳！",
        "完美接盘！再来！",
        "汉堡入袋，金币+！",
    ],
    "milestone_5": ["五个！手速起飞！"],
    "milestone_10": ["十个！你是接盘侠！"],
    "milestone_15": ["十五个！无敌了！"],
    "danger": [
        "炸弹！快躲开！",
        "啊啊别接那个！",
        "小心炸弹，心好痛…",
    ],
    "complete": [
        "60 秒挑战成功！打工达人！",
        "时间到！今天伙食有着落了～",
    ],
    "death": [
        "炸弹太多了…下次小心！",
        "没关系，再练一局！",
    ],
}

DODGE_FEEDBACK = {
    "start": [
        "流星来了！灵活走位！",
        "躲过去！我在给你加油！",
        "深空冒险开始～",
    ],
    "near_miss": [
        "好险！差点撞上！",
        "擦边而过！帅！",
        "这反应速度绝了！",
    ],
    "milestone_30": ["三十秒！你已经很强了！"],
    "milestone_60": ["一分钟！星际老司机！"],
    "death": [
        "被流星击中了…再来！",
        "差一点点，再试一次！",
        "星星太调皮了呜呜",
    ],
}

MEMORY_FEEDBACK = {
    "start": [
        "翻牌配对！我相信你的记忆力～",
        "美食都在下面，找出来！",
        "90 秒，全部配对有奖励！",
    ],
    "match": [
        "配对成功！脑子好快！",
        "一对！继续继续！",
        "记住了！好厉害！",
    ],
    "mismatch": [
        "不对不对，再想想～",
        "这对不是一家人哦",
        "没关系，再试一次！",
    ],
    "milestone_4": ["一半了！过半啦！"],
    "milestone_6": ["只剩两对了！冲刺！"],
    "milestone_8": ["最后一个对！加油！"],
    "complete": [
        "全部配对！记忆大师！",
        "完美通关！太聪明了！",
    ],
    "death": [
        "时间到了…下次更快！",
        "差一点就全配对了！",
    ],
}

GAME_FEEDBACK = {
    GAME_SNAKE_ID: SNAKE_FEEDBACK,
    GAME_CATCH_ID: CATCH_FEEDBACK,
    GAME_DODGE_ID: DODGE_FEEDBACK,
    GAME_MEMORY_ID: MEMORY_FEEDBACK,
}

MAX_PETS = 5               # 默认最大宠物数量
MIN_PETS = 1
MAX_PETS_LIMIT = 20        # 设置中允许的最大数量

# 点击判定阈值
CLICK_THRESHOLD_MS = 200   # 单击判定时间阈值（毫秒）
CLICK_THRESHOLD_PX = 5     # 单击判定移动距离阈值（像素）

# 气泡显示时长（毫秒）
BUBBLE_DURATION_MS = 3000

# 滑翔/月球漫步绘制：仅镜像+微倾，不放大（与待机同体型）
GLIDE_MIRROR_X = -1.0
GLIDE_BODY_SCALE = 0.97
MOONWALK_LEAN_DEG = -12
FORWARD_LEAN_DEG = 8

# 对话气泡主题（自绘，不依赖 CSS 背景）
BUBBLE_THEME = {
    "max_text_width": 210,
    "padding_h": 14,
    "padding_v": 10,
    "radius": 14,
    "tail_width": 14,
    "tail_height": 9,
    "gap_above_pet": 10,
    "shadow_pad": 4,
    "font_family": "Microsoft YaHei UI",
    "font_size": 13,
    "background": (255, 252, 248),
    "background_alpha": 248,
    "border": (255, 183, 197),
    "text": (61, 61, 61),
    "shadow": (200, 170, 190, 55),
}

# 不同互动类型的描边色 (R, G, B)
BUBBLE_ACCENT = {
    "feed": (255, 179, 102),
    "pet": (255, 183, 197),
    "happy": (255, 183, 197),
    "hungry": (255, 200, 120),
    "sad": (168, 212, 255),
    "normal": (255, 183, 197),
    "no_food": (255, 200, 120),
    "game_win": (255, 183, 197),
    "game_daily_cap": (255, 200, 120),
}

# 脚边状态条主题（与气泡同色系，玻璃质感）
STAT_HUD_THEME = {
    "font_family": "Microsoft YaHei UI",
    "radius": 12,
    "shadow_offset": (1.2, 2.0),
    "shadow": (200, 170, 190, 58),
    "background": (255, 252, 248),
    "background_alpha": 238,
    "border": (255, 183, 197),
    "border_width": 1.4,
    "highlight_top": (255, 255, 255, 72),
    "highlight_bottom": (255, 255, 255, 0),
    "text": (58, 58, 58),
    "text_muted": (128, 118, 124),
    "track": (220, 210, 215, 95),
    "track_inset": (180, 165, 175, 40),
    "hunger_grad": {
        "low": ((232, 108, 98), (245, 168, 98)),
        "mid": ((245, 178, 66), (255, 208, 128)),
        "high": ((108, 196, 148), (168, 230, 188)),
    },
    "mood_grad": {
        "low": ((196, 118, 142), (232, 160, 178)),
        "mid": ((232, 160, 178), (255, 183, 197)),
        "high": ((255, 158, 181), (255, 196, 214)),
    },
    "badge_bg": ((248, 242, 255), (255, 244, 248)),
    "badge_border": (212, 175, 255),
    "badge_text": (92, 78, 118),
    "badge_accent": (255, 198, 120),
}

# 小商店 / 背包窗口主题
STORE_THEME = {
    "font_family": "Microsoft YaHei UI",
    "width": 400,
    "min_height": 440,
    "radius": 12,
    "background": (255, 252, 248),
    "card_bg": (255, 248, 252),
    "border": (255, 183, 197),
    "border_soft": (255, 210, 218),
    "text": (58, 58, 58),
    "text_muted": (130, 120, 125),
    "gold_text": (140, 105, 45),
    "gold_bg": (255, 248, 230),
    "gold_border": (255, 210, 140),
    "accent": (255, 183, 197),
    "accent_hover": (255, 200, 210),
    "success": (108, 170, 120),
    "error": (220, 110, 100),
    "shadow": (200, 170, 190, 40),
}

# 饥饿/心情阈值
HUNGER_LOW_THRESHOLD = 30  # 饥饿度低阈值
MOOD_LOW_THRESHOLD = 20    # 心情值低阈值
HUNGER_CRITICAL = 0        # 饥饿度临界值

# 互动恢复值
FEED_HUNGER_BOOST = 50     # 喂食恢复的饥饿度
FEED_MOOD_BOOST = 10       # 喂食恢复的心情值
PET_MOOD_BOOST = 20        # 抚摸恢复的心情值
INTIMACY_INCREMENT = 1     # 每次互动增加的亲密度

# ============== 路径配置 ==============
# 配置文件目录名
CONFIG_DIR_NAME = "DesktopPet"

# 配置文件名
SETTINGS_FILE = "settings.json"
PETS_FILE = "pets.json"
BACKUP_SUFFIX = ".backup"

# 皮肤目录名
SKINS_DIR = "skins"

# 默认皮肤名
DEFAULT_SKIN = "default"

# ============== 默认文本池 ==============
DEFAULT_TEXT_POOLS = {
    "happy": [
        "你好呀！",
        "今天真开心~",
        "主人来陪我玩吧！",
        "嘿嘿～",
        "☀️",
    ],
    "hungry": [
        "我饿了...",
        "想吃好吃的！",
        "🍖",
    ],
    "sad": [
        "心情不好...",
        "摸摸我好不好？",
        "😢",
    ],
    "normal": [
        "喵～",
        "我在哦～",
        "有什么事吗？",
        "✨",
    ],
    "feed": [
        "好吃！",
        "谢谢主人！",
        "饱饱的～",
        "🍪",
        "❤️",
    ],
    "pet": [
        "舒服～",
        "再摸摸～",
        "❤️",
        "开心！",
    ],
    "no_food": [
        "没有食物了…去商店买点吧！",
        "背包里没有吃的，先去小商店看看～",
    ],
    "game_win": [
        "打工辛苦啦！赚了不少金币～",
        "一起玩真开心！💰",
        "下次再陪我玩嘛！",
    ],
    "game_daily_cap": [
        "今天打工够啦，休息一下吧～",
        "明日再来陪我玩！",
    ],
}

# ============== 配置文件字段 ==============
# Settings 数据结构的字段
SETTINGS_FIELDS = {
    "scale": DEFAULT_SCALE,
    "fps": DEFAULT_FPS,
    "opacity": DEFAULT_OPACITY,
    "hunger_decay_rate": HUNGER_DECAY_RATE,
    "mood_decay_rate": MOOD_DECAY_RATE,
    "intimacy_threshold": INTIMACY_THRESHOLD,
    "max_pets": MAX_PETS,
    "auto_run_enabled": False,
    "auto_walk_enabled": True,
    "show_stat_hud": False,
    "language": "en",
    "gold": DEFAULT_GOLD,
    "inventory": {},
    "daily_gold_earned": 0,
    "daily_reset_date": "",
    "game_stats": {},
    "default_skin": DEFAULT_SKIN,
    "text_pools": DEFAULT_TEXT_POOLS,
}

# PetData 数据结构的字段
PET_DATA_FIELDS = {
    "id": "",
    "skin_name": DEFAULT_SKIN,
    "x": 0,
    "y": 0,
    "scale": DEFAULT_SCALE,
    "hunger": 100,
    "mood": 100,
    "intimacy": 0,
    "is_visible": True,
    "last_saved_at": 0.0,
}

# ============== 获取配置目录路径 ==============
def get_config_dir() -> Path:
    r"""
    获取配置文件目录路径
    Windows: %APPDATA%/DesktopPet/
    Linux/macOS: ~/.config/DesktopPet/
    """
    if os.name == "nt":  # Windows
        config_dir = Path(os.environ.get("APPDATA", "")) / CONFIG_DIR_NAME
    else:  # Linux/macOS
        config_dir = Path.home() / ".config" / CONFIG_DIR_NAME

    # 确保目录存在
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def get_skins_dir() -> Path:
    """
    获取皮肤目录路径
    打包后使用 sys._MEIPASS（PyInstaller 临时目录）
    """
    import sys
    
    # PyInstaller 单文件模式
    if getattr(sys, 'frozen', False):
        # 使用 PyInstaller 临时解压目录
        base_dir = Path(sys._MEIPASS)
    else:
        # 开发模式下使用代码目录
        base_dir = Path(__file__).resolve().parent.parent.parent
    
    return base_dir / SKINS_DIR
