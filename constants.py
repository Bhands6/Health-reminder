# -*- coding: utf-8 -*-
"""常量定义：主题、颜色、声音、内置提醒配置等"""

import platform
import os

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"

# 跨平台字体
FONT_EMOJI = "Apple Color Emoji" if IS_MAC else "Segoe UI Emoji"
FONT_UI = "PingFang SC" if IS_MAC else "Microsoft YaHei"

# 文件路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CHECK_ICON = os.path.join(BASE_DIR, "checkmark.png")
ARROW_UP_ICON = os.path.join(BASE_DIR, "arrow_up.svg")
ARROW_DOWN_ICON = os.path.join(BASE_DIR, "arrow_down.svg")
STATS_FILE = os.path.join(BASE_DIR, "stats.json")

# 默认配置
DEFAULT_CONFIG = {
    "eye_care": {"enabled": True, "interval": 20},
    "rest": {"enabled": True, "interval": 45},
    "water": {"enabled": True, "interval": 30},
    "sound": True,
    "auto_start": False,
    "custom": [],
    "dnd_enabled": False,
    "dnd_start": "22:00",
    "dnd_end": "08:00",
    "mini_mode": False,
    "widget_size": 100,
    "theme": "light",
    "gradient_start": None,
    "gradient_end": None,
    "popup_position": "center",
}

# 内置提醒配置
BUILTIN_REMINDERS = {
    "eye_care": ("👀", "护眼提醒", "让眼睛休息一下，远眺20秒吧！", (102, 126, 234)),
    "rest": ("🧘", "休息提醒", "站起来活动一下，伸个懒腰吧！", (118, 75, 162)),
    "water": ("💧", "喝水提醒", "记得喝水哦，保持身体水分！", (72, 209, 204)),
}

# 自定义提醒颜色
CUSTOM_COLORS = [
    (255, 152, 0), (233, 30, 99), (0, 150, 136), (63, 81, 181),
    (156, 39, 176), (244, 67, 54), (33, 150, 243), (139, 195, 74),
]

# 图标选择列表
ICON_CHOICES = [
    "☕", "🍎", "🎵", "💪", "🏃", "🙏", "💊", "🌸",
    "⭐", "🎯", "📝", "🕐", "🌿", "🥤", "🧘", "🔔",
    "⏰", "📌", "💡", "🎉", "❤️",
]

ICON_NAMES = {
    "☕": "咖啡", "🍎": "苹果", "🎵": "音乐", "💪": "健身",
    "🏃": "跑步", "🙏": "祈祷", "💊": "吃药",
    "🌸": "花", "⭐": "星星", "🎯": "目标",
    "📝": "笔记", "🕐": "时钟", "🌿": "绿叶",
    "🥤": "喝水", "🧘": "冥想", "🔔": "铃声",
    "⏰": "闹钟", "📌": "固定", "💡": "灯泡",
    "🎉": "庆祝", "❤️": "爱心",
}

# 主题色彩
THEME_PRESETS = {
    "light": {
        "primary": (102, 126, 234),
        "secondary": (118, 75, 162),
        "accent": (72, 209, 204),
        "bg_start": (102, 126, 234),
        "bg_end": (118, 75, 162),
        "card_bg": (255, 255, 255, 30),
        "text": (255, 255, 255),
        "text_secondary": (255, 255, 255, 180),
        "success": (76, 175, 80),
        "warning": (255, 152, 0),
        "danger": (244, 67, 54),
    },
    "dark": {
        "primary": (80, 90, 160),
        "secondary": (60, 60, 90),
        "accent": (50, 140, 135),
        "bg_start": (15, 15, 25),
        "bg_end": (20, 20, 35),
        "card_bg": (255, 255, 255, 15),
        "text": (200, 200, 220),
        "text_secondary": (150, 150, 170),
        "success": (76, 175, 80),
        "warning": (255, 152, 0),
        "danger": (244, 67, 54),
    },
}

# 当前主题（可变全局状态）
THEME = dict(THEME_PRESETS["dark"])


def apply_theme(theme_name: str) -> None:
    """切换全局主题（就地更新，确保所有 from-import 引用同步）"""
    THEME.clear()
    THEME.update(THEME_PRESETS.get(theme_name, THEME_PRESETS["dark"]))


def apply_gradient_colors(config: dict) -> None:
    """将自定义渐变颜色覆盖到全局 THEME（就地更新）"""
    gs = config.get("gradient_start")
    ge = config.get("gradient_end")
    if gs and isinstance(gs, (list, tuple)) and len(gs) == 3:
        THEME["primary"] = tuple(gs)
    if ge and isinstance(ge, (list, tuple)) and len(ge) == 3:
        THEME["secondary"] = tuple(ge)


# 提示音频率 (Hz) 和持续时间 (ms)
SOUND_PROFILES = {
    "eye_care": [(800, 100), (1000, 100), (1200, 150)],
    "rest": [(600, 150), (800, 100), (1000, 150)],
    "water": [(1000, 100), (1200, 100), (1400, 100)],
    "custom": [(900, 100), (1100, 100), (900, 150)],
}

# 弹窗位置映射
POPUP_POSITION_MAP = {
    "center": "居中",
    "top_left": "左上",
    "top_right": "右上",
    "bottom_left": "左下",
    "bottom_right": "右下",
    "top_center": "中上",
    "bottom_center": "中下",
}

