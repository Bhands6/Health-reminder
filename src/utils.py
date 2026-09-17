# -*- coding: utf-8 -*-
"""工具函数：配置读写、统计记录、自启动、提示音、勿扰判断"""

import copy
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Dict

from constants import (
    CONFIG_FILE, DATA_DIR, DEFAULT_CONFIG, PROJECT_ROOT, STATS_FILE,
    IS_WINDOWS, SOUND_PROFILES,
)

logger = logging.getLogger(__name__)

# Windows 提示音
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

if IS_WINDOWS:
    import winreg


# ==================== 图标生成 ====================

def create_checkmark_icon() -> None:
    """创建勾选图标（如果文件不存在）"""
    from constants import CHECK_ICON
    if os.path.exists(CHECK_ICON):
        return
    try:
        from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
        from PyQt5.QtCore import Qt
        pixmap = QPixmap(20, 20)
        pixmap.fill(QColor(0, 0, 0, 0))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(255, 255, 255), 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        from PyQt5.QtGui import QPainterPath
        path = QPainterPath()
        path.moveTo(5, 11)
        path.lineTo(9, 15)
        path.lineTo(16, 5)
        painter.drawPath(path)
        painter.end()
        pixmap.save(CHECK_ICON, "PNG")
        logger.debug("Created checkmark icon: %s", CHECK_ICON)
    except Exception as e:
        logger.warning("Failed to create checkmark icon: %s", e)


# 箭头图标内容模板。Qt 的 QPixmap.save 不支持写 SVG（可写格式只有 png/bmp/jpg 等位图），
# 所以这里直接写 SVG 文本，内容与 assets/ 中已有文件一致。
_ARROW_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6" viewBox="0 0 8 6">'
    '<polygon points="{points}" fill="#c8b4ff" fill-opacity="0.85"/></svg>'
)


def create_arrow_icons() -> None:
    """创建箭头图标（如果文件不存在）"""
    from constants import ARROW_UP_ICON, ARROW_DOWN_ICON
    icons = [
        (ARROW_UP_ICON, "4,0 0,6 8,6"),
        (ARROW_DOWN_ICON, "4,6 0,0 8,0"),
    ]
    for path, points in icons:
        if os.path.exists(path):
            continue
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(_ARROW_SVG.format(points=points))
            logger.debug("Created arrow icon: %s", path)
        except IOError as e:
            logger.warning("Failed to create arrow icon %s: %s", path, e)


# ==================== 配置读写 ====================

def _validate_config(config: dict) -> dict:
    """验证并修复配置数据，确保类型和范围正确"""
    # 必须深拷贝：浅拷贝会让嵌套 dict/list 与 DEFAULT_CONFIG 共享引用，
    # 后续任何就地修改都会污染全局默认值
    validated = copy.deepcopy(DEFAULT_CONFIG)

    for key in ("eye_care", "rest", "water"):
        if key in config and isinstance(config[key], dict):
            validated[key] = {
                "enabled": bool(config[key].get("enabled", DEFAULT_CONFIG[key]["enabled"])),
                "interval": max(1, min(480, int(config[key].get("interval", DEFAULT_CONFIG[key]["interval"])))),
            }

    validated["sound"] = bool(config.get("sound", True))
    validated["auto_start"] = bool(config.get("auto_start", False))
    validated["dnd_enabled"] = bool(config.get("dnd_enabled", False))
    validated["mini_mode"] = bool(config.get("mini_mode", False))
    validated["theme"] = config.get("theme", "dark") if config.get("theme") in ("light", "dark") else "dark"
    validated["popup_position"] = config.get("popup_position", "center")
    validated["warm_tip_count"] = max(10, min(500, int(config.get("warm_tip_count", 100))))
    validated["widget_size"] = max(60, min(200, int(config.get("widget_size", 100))))

    # 时间格式验证
    for tkey in ("dnd_start", "dnd_end"):
        val = config.get(tkey, DEFAULT_CONFIG[tkey])
        try:
            datetime.strptime(val, "%H:%M")
            validated[tkey] = val
        except (ValueError, TypeError):
            validated[tkey] = DEFAULT_CONFIG[tkey]

    # 渐变颜色
    for ckey in ("gradient_start", "gradient_end"):
        val = config.get(ckey)
        if val and isinstance(val, list) and len(val) == 3:
            validated[ckey] = [max(0, min(255, int(c))) for c in val]
        else:
            validated[ckey] = None

    # 自定义提醒
    if isinstance(config.get("custom"), list):
        validated["custom"] = []
        for item in config["custom"]:
            if isinstance(item, dict) and "name" in item and "icon" in item:
                validated["custom"].append({
                    "name": str(item["name"]),
                    "icon": str(item["icon"]),
                    "message": str(item.get("message", item["name"])),
                    "interval": max(1, min(480, int(item.get("interval", 30)))),
                    "enabled": bool(item.get("enabled", True)),
                })

    return validated


def load_config() -> dict:
    """加载配置文件，不存在或损坏则创建默认配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            # utf-8-sig：兼容带 BOM 的文件（记事本「另存为 UTF-8」会写入 BOM）。
            # 用 utf-8 读取带 BOM 的文件会直接抛 JSONDecodeError，导致配置永远读不进来。
            with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                config = json.load(f)
            config = _validate_config(config)
            logger.info("Config loaded from %s", CONFIG_FILE)
            return config
        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            logger.error("Failed to load config: %s, using defaults", e)
            # 解析失败先把原文件备份下来，避免用户配置被默认值直接覆盖且无从追溯
            try:
                backup = CONFIG_FILE + ".bak"
                shutil.copyfile(CONFIG_FILE, backup)
                logger.warning("Broken config backed up to %s", backup)
            except IOError as be:
                logger.warning("Failed to back up config: %s", be)

    # 创建默认配置
    config = copy.deepcopy(DEFAULT_CONFIG)
    save_config(config)
    logger.info("Created default config at %s", CONFIG_FILE)
    return config


def save_config(config: dict) -> None:
    """保存配置到文件"""
    try:
        # 写入前验证
        config = _validate_config(config)
        # data 目录可能不存在（首次运行 / 打包后首次启动），必须确保存在
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.debug("Config saved")
    except IOError as e:
        logger.error("Failed to save config: %s", e)


# ==================== 统计 ====================

def load_stats() -> dict:
    """加载统计数据"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("Failed to load stats: %s", e)
    return {}


def save_stats(stats: dict) -> None:
    """保存统计数据"""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error("Failed to save stats: %s", e)


def record_stat(key: str, action: str = "triggered") -> None:
    """记录一次统计（触发或完成）"""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = load_stats()
    if today not in stats:
        stats[today] = {}
    if key not in stats[today]:
        stats[today][key] = {"triggered": 0, "completed": 0}
    if action not in stats[today][key]:
        stats[today][key][action] = 0
    stats[today][key][action] += 1
    save_stats(stats)
    logger.debug("Recorded stat: %s/%s/%s +1", today, key, action)


def get_today_stats() -> Dict[str, Dict[str, int]]:
    """获取今日统计数据"""
    today = datetime.now().strftime("%Y-%m-%d")
    stats = load_stats()
    return stats.get(today, {})


# ==================== 自启动 ====================

def _autostart_command() -> str:
    """构造开机自启要执行的命令行

    打包后 sys.executable 就是 exe 本身；
    源码运行时必须带上解释器（"python.exe" "main.py"），
    只写 sys.argv[0] 会得到一行裸的 .py 路径，开机根本起不来。
    """
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'
    script = os.path.abspath(os.path.join(PROJECT_ROOT, "main.py"))
    return f'"{os.path.abspath(sys.executable)}" "{script}"'


def set_autostart(enable: bool) -> None:
    """设置开机自启动（仅 Windows）"""
    if not IS_WINDOWS:
        return

    app_name = "HealthReminder"
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    command = _autostart_command()

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
            logger.info("Autostart enabled: %s", command)
        else:
            try:
                winreg.DeleteValue(key, app_name)
                logger.info("Autostart disabled")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except OSError as e:
        logger.error("Failed to set autostart: %s", e)


# ==================== 提示音 ====================

def play_reminder_sound(key: str) -> None:
    """播放提醒提示音"""
    profile = SOUND_PROFILES.get(key, SOUND_PROFILES["custom"])
    if HAS_WINSOUND:
        import threading
        def _play():
            for freq, duration in profile:
                try:
                    winsound.Beep(freq, duration)
                except Exception:
                    pass
        threading.Thread(target=_play, daemon=True).start()
    else:
        logger.debug("Sound not available on this platform")


# ==================== 勿扰 ====================

def is_dnd_active(config: dict) -> bool:
    """判断当前是否在勿扰时段"""
    if not config.get("dnd_enabled", False):
        return False
    try:
        now = datetime.now().time()
        start = datetime.strptime(config.get("dnd_start", "22:00"), "%H:%M").time()
        end = datetime.strptime(config.get("dnd_end", "08:00"), "%H:%M").time()

        if start <= end:
            # 同一天（如 09:00 - 17:00）
            return start <= now <= end
        else:
            # 跨天（如 22:00 - 08:00）
            return now >= start or now <= end
    except (ValueError, TypeError) as e:
        logger.error("DND time parse error: %s", e)
        return False

