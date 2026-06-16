"""大富翁经济平衡 — 快节奏对局（约 15～25 分钟）"""

# 起始资金：约为最贵地产 2 圈租金之和，购地后仍有压力
INITIAL_MONEY = 5000

# 经过 / 停在起点
PASS_START_SALARY = 500
START_BONUS = 500

# 税款
TAX_AMOUNT = 800

# 监狱保释（可选，交后立即掷骰，否则本回合跳过）
JAIL_BAIL = 400

# 盖房等级 0=空地 1-3=房屋 4=酒店
MAX_BUILD_LEVEL = 4
RENT_MULTIPLIERS = (1, 4, 12, 35, 70)
