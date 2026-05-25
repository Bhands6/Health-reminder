# -*- coding: utf-8 -*-
"""
桌面健康提醒应用 v2.0
功能：护眼提醒、休息提醒、喝水提醒、自定义提醒、贪睡、勿扰、统计
技术栈：Python + PyQt5 + plyer + winsound
"""

import sys
import json
import os
import math
import time
import winreg
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QMenu, QAction, QSystemTrayIcon, QDialog, QFormLayout,
    QSpinBox, QCheckBox, QPushButton, QMessageBox, QLineEdit,
    QInputDialog, QScrollArea, QGroupBox, QGraphicsDropShadowEffect,
    QDesktopWidget, QShortcut, QWidgetAction, QSlider, QColorDialog
)
from PyQt5.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve,
    QRect, pyqtSignal, QThread, QSize, QObject, QEvent,
    pyqtProperty
)
from PyQt5.QtGui import (
    QColor, QPainter, QFont, QIcon, QLinearGradient, QBrush,
    QPen, QPainterPath, QPixmap, QRadialGradient, QConicalGradient,
    QFontMetrics, QKeySequence
)
from plyer import notification

# Windows 提示音
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# ==================== 配置常量 ====================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
CHECK_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkmark.png")
ARROW_UP_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arrow_up.svg")
ARROW_DOWN_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arrow_down.svg")
STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stats.json")

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
    "widget_size": 80,
    "theme": "light",
    "gradient_start": None,
    "gradient_end": None,
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
THEME = dict(THEME_PRESETS["dark"])


def apply_theme(theme_name):
    """切换全局主题"""
    global THEME
    THEME = dict(THEME_PRESETS.get(theme_name, THEME_PRESETS["dark"]))


def apply_gradient_colors(config):
    """将自定义渐变颜色覆盖到全局 THEME"""
    gs = config.get("gradient_start")
    ge = config.get("gradient_end")
    if gs and len(gs) == 3:
        THEME["primary"] = tuple(gs)
    if ge and len(ge) == 3:
        THEME["secondary"] = tuple(ge)

# 提示音频率 (Hz) 和持续时间 (ms)
SOUND_PROFILES = {
    "eye_care": [(800, 100), (1000, 100), (1200, 150)],
    "rest": [(600, 150), (800, 100), (1000, 150)],
    "water": [(1000, 100), (1200, 100), (1400, 100)],
    "custom": [(900, 100), (1100, 100), (900, 150)],
}


# ==================== 工具函数 ====================

def create_checkmark_icon():
    """生成复选框对勾图标"""
    if os.path.exists(CHECK_ICON):
        return
    size = 18
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.moveTo(4, 9)
    path.lineTo(7, 13)
    path.lineTo(14, 5)
    pen = QPen(QColor(*THEME["primary"]))
    pen.setWidth(2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawPath(path)
    painter.end()
    pixmap.save(CHECK_ICON)


def create_arrow_icons():
    """生成上下箭头 SVG 图标"""
    svg_up = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6" viewBox="0 0 8 6">'
        '<polygon points="4,0 0,6 8,6" fill="#c8b4ff" fill-opacity="0.85"/>'
        '</svg>'
    )
    svg_down = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="6" viewBox="0 0 8 6">'
        '<polygon points="4,6 0,0 8,0" fill="#c8b4ff" fill-opacity="0.85"/>'
        '</svg>'
    )
    for path, content in [(ARROW_UP_ICON, svg_up), (ARROW_DOWN_ICON, svg_down)]:
        if os.path.exists(path):
            os.remove(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            merged = DEFAULT_CONFIG.copy()
            for key in DEFAULT_CONFIG:
                if key in cfg:
                    if isinstance(DEFAULT_CONFIG[key], dict):
                        merged[key] = {**DEFAULT_CONFIG[key], **cfg[key]}
                    elif isinstance(DEFAULT_CONFIG[key], list):
                        merged[key] = cfg[key]
                    else:
                        merged[key] = cfg[key]
            return merged
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """保存配置"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_stats():
    """加载统计数据"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_stats(stats):
    """保存统计数据"""
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def record_stat(key, action="triggered"):
    """记录统计：triggered(触发) / completed(完成/关闭)"""
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in stats:
        stats[today] = {}
    if key not in stats[today]:
        stats[today][key] = {"triggered": 0, "completed": 0}
    stats[today][key][action] = stats[today][key].get(action, 0) + 1
    save_stats(stats)


def get_today_stats():
    """获取今日统计"""
    stats = load_stats()
    today = datetime.now().strftime("%Y-%m-%d")
    return stats.get(today, {})


def set_autostart(enable):
    """设置开机自启动（写入/删除注册表）"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "HealthReminder"
    script = os.path.abspath(sys.argv[0])
    if script.endswith(".py"):
        value = f'"{sys.executable}" "{script}"'
    else:
        value = f'"{script}"'
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, value)
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception:
        pass


def play_reminder_sound(key):
    """播放提示音"""
    if not HAS_WINSOUND:
        return
    profile = SOUND_PROFILES.get(key, SOUND_PROFILES["custom"])
    for freq, duration in profile:
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass


def is_dnd_active(config):
    """检查是否在勿扰时间段内"""
    if not config.get("dnd_enabled", False):
        return False
    now = datetime.now()
    start_str = config.get("dnd_start", "22:00")
    end_str = config.get("dnd_end", "08:00")
    try:
        start_h, start_m = map(int, start_str.split(":"))
        end_h, end_m = map(int, end_str.split(":"))
        start_time = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end_time = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time
    except Exception:
        return False


def draw_progress_ring(painter, cx, cy, radius, progress, color, bg_color=(255, 255, 255, 255)):
    """绘制进度环"""
    # 背景环
    pen = QPen(QColor(*bg_color))
    pen.setWidth(5)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

    # 发光效果
    if progress > 0:
        glow_color = QColor(*color[:3], 50) if len(color) == 3 else QColor(*color[:3], 50)
        pen = QPen(glow_color)
        pen.setWidth(10)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        start_angle = 90 * 16
        span_angle = -int(progress * 360 * 16)
        painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, start_angle, span_angle)

    # 进度环
    pen = QPen(QColor(*color))
    pen.setWidth(5)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    start_angle = 90 * 16
    span_angle = -int(progress * 360 * 16)
    painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, start_angle, span_angle)


# ==================== 提醒弹窗（带贪睡） ====================

class ReminderPopup(QWidget):
    """提醒弹窗 - 支持贪睡、进度条、美化"""

    snooze_signal = pyqtSignal(str, int)  # (key, minutes)

    def __init__(self, message, color, key="custom", interval=30, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 220)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, (screen.height() - self.height()) // 2)

        self.message = message
        self.color = color
        self.key = key
        self.interval = interval
        self.opacity_val = 0.0
        self.total_time = 5000  # 4秒自动关闭
        self.elapsed_time = 0
        self.is_snoozed = False

        # 渐变动画
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_step)
        self.fade_timer.start(16)

        # 自动关闭计时器
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.update_progress)
        self.close_timer.start(16)

        # 4秒后自动关闭
        self.auto_close_timer = QTimer(self)
        self.auto_close_timer.setSingleShot(True)
        self.auto_close_timer.timeout.connect(self.fade_out)
        self.auto_close_timer.start(self.total_time)

        self.fading_in = True
        self.fading_out = False

        # 创建按钮
        self._create_buttons()

    def _create_buttons(self):
        """创建贪睡和关闭按钮"""
        # 间隔小于5分钟时隐藏贪睡按钮
        if self.interval < 5:
            self.snooze_btn = None
            return
        # 贪睡按钮
        self.snooze_btn = QPushButton("💤 延迟 5 分钟", self)
        self.snooze_btn.setGeometry(self.width() - 180, self.height() - 55, 120, 32)
        self.snooze_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.25);
                color: white;
                border: 1px solid rgba(255,255,255,0.4);
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,255,255,0.4);
            }
        """)
        self.snooze_btn.clicked.connect(self.snooze)

    def snooze(self):
        """贪睡 5 分钟"""
        self.is_snoozed = True
        self.snooze_signal.emit(self.key, 5)
        self.fade_out()

    def fade_step(self):
        """渐变动画"""
        if self.fading_in:
            self.opacity_val = min(1.0, self.opacity_val + 0.05)
            self.setWindowOpacity(self.opacity_val)
            if self.opacity_val >= 1.0:
                self.fading_in = False
        elif self.fading_out:
            self.opacity_val -= 0.05
            self.setWindowOpacity(max(0.0, self.opacity_val))
            if self.opacity_val <= 0.0:
                self.close()

    def fade_out(self):
        """开始渐出"""
        self.fading_out = True

    def update_progress(self):
        """更新进度"""
        self.elapsed_time += 16
        self.update()

    def paintEvent(self, event):
        """绘制弹窗"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 阴影
        shadow = QColor(0, 0, 0, 60)
        painter.setBrush(QBrush(shadow))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(8, 8, self.width() - 8, self.height() - 8, 24, 24)

        # 渐变背景
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(*self.color, 230))
        gradient.setColorAt(1, QColor(*self.color, 200))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, self.width() - 8, self.height() - 8, 24, 24)

        # 大图标
        painter.setPen(QColor(255, 255, 255, 80))
        painter.setFont(QFont("Segoe UI Emoji", 45))
        icon = self.message[0] if len(self.message) > 0 else "🔔"
        painter.drawText(25, 40, 70, 70, Qt.AlignCenter, icon)

        # 提醒文字
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        text = self.message[2:] if len(self.message) > 2 else self.message
        painter.drawText(105, 35, self.width() - 130, 80, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)

        # 底部进度条
        progress = min(1.0, self.elapsed_time / self.total_time)
        bar_y = self.height() - 12
        bar_width = self.width() - 30
        # 背景
        painter.setBrush(QColor(255, 255, 255, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(15, bar_y, bar_width, 4, 2, 2)
        # 进度
        painter.setBrush(QColor(255, 255, 255, 180))
        painter.drawRoundedRect(15, bar_y, int(bar_width * (1 - progress)), 4, 2, 2)

    def mousePressEvent(self, event):
        """点击关闭"""
        if self.snooze_btn and self.snooze_btn.geometry().contains(event.pos()):
            return
        record_stat(self.key, "completed")
        self.fade_out()


# ==================== 自定义提醒对话框 ====================

class CustomReminderDialog(QDialog):
    """添加/编辑自定义提醒"""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("添加自定义提醒" if data is None else "编辑自定义提醒")
        self.setMinimumSize(380, 280)
        self.resize(420, 320)

        p = THEME.get("primary", (102, 126, 234))
        s = THEME.get("secondary", (118, 75, 162))
        self.setStyleSheet(f"""
            QDialog {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a1a2e, stop:0.3 #16213e, stop:0.6 #0f3460, stop:1 #533483);
            }}
            QLabel {{ color: rgba(200,180,255,0.9); font-size: 13px; }}
            QLineEdit, QSpinBox {{
                background: rgba(200,180,255,0.1);
                color: rgba(200,180,255,1);
                border: 1px solid rgba(200,180,255,0.2);
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
            }}
            QSpinBox {{
                padding-right: 22px;
                min-width: 85px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1px solid rgba(200,180,255,0.5);
                background: rgba(200,180,255,0.15);
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({p[0]},{p[1]},{p[2]},0.6), stop:1 rgba({s[0]},{s[1]},{s[2]},0.6));
                color: rgba(200,180,255,1);
                border: 1px solid rgba(200,180,255,0.25);
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba({p[0]},{p[1]},{p[2]},0.8), stop:1 rgba({s[0]},{s[1]},{s[2]},0.8));
                border: 1px solid rgba(200,180,255,0.5);
            }}
            QPushButton#iconBtn {{
                min-width: 40px; max-width: 40px;
                min-height: 40px; max-height: 40px;
                font-size: 20px;
                padding: 0;
            }}
        """)

        layout = QFormLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(35, 30, 35, 30)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("例如：吃药提醒")
        if data:
            self.name_edit.setText(data.get("name", ""))
        layout.addRow("提醒名称:", self.name_edit)

        self.icon = data.get("icon", "🔔") if data else "🔔"
        self.icon_btn = QPushButton(self.icon)
        self.icon_btn.setObjectName("iconBtn")
        self.icon_btn.clicked.connect(self.choose_icon)
        layout.addRow("选择图标:", self.icon_btn)

        self.msg_edit = QLineEdit()
        self.msg_edit.setPlaceholderText("例如：该吃药了！")
        if data:
            self.msg_edit.setText(data.get("message", ""))
        layout.addRow("提醒内容:", self.msg_edit)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 480)
        self.interval_spin.setValue(data.get("interval", 30) if data else 30)
        self.interval_spin.setSuffix(" 分钟")
        layout.addRow("间隔时间:", self.interval_spin)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)

    def choose_icon(self):
        item, ok = QInputDialog.getItem(self, "选择图标", "图标:", ICON_CHOICES, 0, False)
        if ok and item:
            self.icon = item
            self.icon_btn.setText(item)

    def validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入提醒名称")
            return
        if not self.msg_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入提醒内容")
            return
        self.accept()

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "icon": self.icon,
            "message": self.msg_edit.text().strip(),
            "interval": self.interval_spin.value(),
            "enabled": True,
        }


# ==================== 开关控件 ====================

class ToggleSwitch(QWidget):
    """仿 iOS 滑动开关"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._offset = 22.0 if checked else 2.0
        self.setFixedSize(46, 24)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"offset")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def isChecked(self):
        return self._checked

    def setChecked(self, val):
        if self._checked == val:
            return
        self._checked = val
        self._animate()

    def _animate(self):
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(22.0 if self._checked else 2.0)
        self._anim.start()

    def get_offset(self):
        return self._offset

    def set_offset(self, val):
        self._offset = val
        self.update()

    offset = pyqtProperty(float, fget=get_offset, fset=set_offset)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._checked = not self._checked
            self._animate()
            self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # 背景轨道
        if self._checked:
            p.setBrush(QColor(*THEME.get("primary", (102, 126, 234))))
        else:
            p.setBrush(QColor(80, 80, 100))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        # 圆形滑块
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(int(self._offset), 2, 20, 20)
        p.end()


# ==================== 设置面板（现代化） ====================

_DIALOG_COLORS = {
    "light": {
        "bg": "stop:0 #1a1a2e, stop:0.3 #16213e, stop:0.6 #0f3460, stop:1 #533483",
        "text": "rgba(200,180,255,0.9)", "text_full": "rgba(200,180,255,1)",
        "input_bg": "rgba(200,180,255,0.1)", "input_bg_h": "rgba(200,180,255,0.15)",
        "border": "rgba(200,180,255,0.2)", "border_h": "rgba(200,180,255,0.5)",
        "spin_btn": "rgba(200,180,255,0.15)", "spin_btn_h": "rgba(200,180,255,0.3)",
        "grp_bg": "stop:0 rgba(200,180,255,0.08), stop:0.5 rgba(200,180,255,0.12), stop:1 rgba(200,180,255,0.15)",
        "grp_border": "rgba(200,180,255,0.12)", "grp_title": "rgba(200,180,255,0.95)",
        "scroll_bg": "rgba(200,180,255,0.05)", "scroll_h": "rgba(200,180,255,0.2)",
        "scroll_hh": "rgba(200,180,255,0.35)",
        "tooltip_bg": "rgba(30,30,50,230)", "tooltip_border": "rgba(200,180,255,0.3)",
    },
    "dark": {
        "bg": "stop:0 #0a0a0f, stop:0.4 #111118, stop:0.7 #0d0d14, stop:1 #141420",
        "text": "rgba(180,180,200,0.9)", "text_full": "rgba(200,200,220,1)",
        "input_bg": "rgba(200,200,220,0.06)", "input_bg_h": "rgba(200,200,220,0.1)",
        "border": "rgba(200,200,220,0.12)", "border_h": "rgba(200,200,220,0.3)",
        "spin_btn": "rgba(200,200,220,0.08)", "spin_btn_h": "rgba(200,200,220,0.15)",
        "grp_bg": "stop:0 rgba(200,200,220,0.04), stop:0.5 rgba(200,200,220,0.06), stop:1 rgba(200,200,220,0.08)",
        "grp_border": "rgba(200,200,220,0.08)", "grp_title": "rgba(180,180,200,0.9)",
        "scroll_bg": "rgba(200,200,220,0.03)", "scroll_h": "rgba(200,200,220,0.12)",
        "scroll_hh": "rgba(200,200,220,0.22)",
        "tooltip_bg": "rgba(15,15,22,240)", "tooltip_border": "rgba(200,200,220,0.15)",
    },
}


def _row_style():
    if THEME.get("bg_start", (102, 126, 234))[0] < 50:
        return """
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(200,200,220,0.06), stop:1 rgba(200,200,220,0.08));
            border: 1px solid rgba(200,200,220,0.08);
            border-radius: 10px; padding: 8px 12px;
        """
    else:
        return """
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(200,180,255,0.1), stop:1 rgba(200,180,255,0.15));
            border: 1px solid rgba(200,180,255,0.1);
            border-radius: 10px; padding: 8px 12px;
        """


def _build_dialog_style(theme_name, check_path, arrow_up_path, arrow_down_path):
    c = _DIALOG_COLORS.get(theme_name, _DIALOG_COLORS["dark"])
    p = THEME.get("primary", (102, 126, 234))
    s = THEME.get("secondary", (118, 75, 162))
    if theme_name == "dark":
        bg_grad = c["bg"]
        # 暗色模式按钮用深色
        bpr, bpy, bpb = 40, 40, 55
        bsr, bsy, bsb = 35, 35, 50
    else:
        bpr, bpy, bpb = p[0], p[1], p[2]
        bsr, bsy, bsb = s[0], s[1], s[2]
        def _dim(v, factor=0.35):
            return max(10, int(v * factor))
        bg_grad = (f"stop:0 rgb({_dim(p[0])},{_dim(p[1])},{_dim(p[2])}), "
                   f"stop:0.4 rgb({_dim(p[0],0.45)},{_dim(p[1],0.45)},{_dim(p[2],0.45)}), "
                   f"stop:0.7 rgb({_dim(p[0])},{_dim(p[1])},{_dim(p[2])}), "
                   f"stop:1 rgb({_dim(s[0])},{_dim(s[1])},{_dim(s[2])})")
    return """
        QDialog { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, %(bg)s); }
        QLabel { color: %(text)s; font-size: 13px; }
        QSpinBox {
            background: %(input_bg)s; color: %(text_full)s;
            border: 1px solid %(border)s; border-radius: 8px;
            padding: 6px; padding-right: 22px; font-size: 13px; min-width: 85px;
        }
        QSpinBox:hover { border: 1px solid %(border_h)s; background: %(input_bg_h)s; }
        QSpinBox::up-button, QSpinBox::down-button {
            background: %(spin_btn)s; border: none; border-radius: 3px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: %(spin_btn_h)s; }
        QSpinBox::up-arrow { image: url(%(arrow_up)s); width: 16px; height: 16px; }
        QSpinBox::down-arrow { image: url(%(arrow_down)s); width: 16px; height: 16px; }
        QCheckBox { color: %(text)s; font-size: 13px; }
        QCheckBox::indicator {
            width: 20px; height: 20px;
            border: 2px solid %(border)s; border-radius: 5px;
            background: rgba(255,255,255,0.9);
        }
        QCheckBox::indicator:hover { border: 2px solid %(border_h)s; background: %(input_bg_h)s; }
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgb(%(pr)s,%(pg)s,%(pb)s), stop:1 rgb(%(sr)s,%(sg)s,%(sb)s));
            border-color: %(border_h)s; image: url(%(check)s);
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(%(bpr)s,%(bpy)s,%(bpb)s,0.6), stop:1 rgba(%(bsr)s,%(bsy)s,%(bsb)s,0.6));
            color: %(text_full)s; border: 1px solid %(border)s;
            border-radius: 10px; padding: 10px 24px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(%(bpr)s,%(bpy)s,%(bpb)s,0.8), stop:1 rgba(%(bsr)s,%(bsy)s,%(bsb)s,0.8));
            border: 1px solid %(border_h)s;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(%(bpr)s,%(bpy)s,%(bpb)s,0.9), stop:1 rgba(%(bsr)s,%(bsy)s,%(bsb)s,0.9));
        }
        QPushButton#editBtn {
            background: rgba(72,209,204,0.15); color: rgba(72,209,204,0.9);
            border: 1px solid rgba(72,209,204,0.2); border-radius: 8px;
            padding: 0; font-size: 16px;
        }
        QPushButton#editBtn:hover {
            background: rgba(72,209,204,0.35); border: 1px solid rgba(72,209,204,0.6);
            color: rgba(72,209,204,1);
        }
        QPushButton#editBtn:pressed { background: rgba(72,209,204,0.5); }
        QPushButton#delBtn {
            background: rgba(244,67,54,0.12); color: rgba(244,67,54,0.85);
            border: 1px solid rgba(244,67,54,0.2); border-radius: 8px;
            padding: 0; font-size: 16px;
        }
        QPushButton#delBtn:hover {
            background: rgba(244,67,54,0.35); border: 1px solid rgba(244,67,54,0.6);
            color: rgba(244,67,54,1);
        }
        QPushButton#delBtn:pressed { background: rgba(244,67,54,0.5); }
        QGroupBox {
            color: %(grp_title)s;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, %(grp_bg)s);
            border: 1px solid %(grp_border)s; border-radius: 14px;
            margin-top: 12px; padding-top: 18px; font-size: 13px; font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin; left: 18px; padding: 0 8px; color: %(grp_title)s;
        }
        QLineEdit {
            background: %(input_bg)s; color: %(text_full)s;
            border: 1px solid %(border)s; border-radius: 8px; padding: 6px; font-size: 13px;
        }
        QLineEdit:focus { border: 1px solid %(border_h)s; background: %(input_bg_h)s; }
        QScrollArea { border: none; background: transparent; }
        QScrollBar:vertical { background: %(scroll_bg)s; width: 8px; border-radius: 4px; }
        QScrollBar::handle:vertical {
            background: %(scroll_h)s; border-radius: 4px; min-height: 30px;
        }
        QScrollBar::handle:vertical:hover { background: %(scroll_hh)s; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        QToolTip {
            background: %(tooltip_bg)s; color: %(text_full)s;
            border: 1px solid %(tooltip_border)s; border-radius: 6px;
            padding: 5px 10px; font-size: 12px;
        }
    """ % {
        **c,
        "bg": bg_grad,
        "check": check_path,
        "arrow_up": arrow_up_path,
        "arrow_down": arrow_down_path,
        "pr": p[0], "pg": p[1], "pb": p[2],
        "sr": s[0], "sg": s[1], "sb": s[2],
        "bpr": bpr, "bpy": bpy, "bpb": bpb,
        "bsr": bsr, "bsy": bsy, "bsb": bsb,
    }


class SettingsDialog(QDialog):
    """设置面板 - 卡片式布局"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.custom_items = list(config.get("custom", []))
        self.custom_checks = []
        self.custom_spins = []
        self.custom_btn_widgets = []
        self.custom_containers = []

        self.setWindowTitle("健康提醒 - 设置")
        self.setMinimumSize(480, 450)
        self.resize(480, 750)

        self._check_path = CHECK_ICON.replace("\\", "/")
        self._arrow_up_path = ARROW_UP_ICON.replace("\\", "/")
        self._arrow_down_path = ARROW_DOWN_ICON.replace("\\", "/")
        self._apply_style()

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(25, 20, 25, 20)

        # 标题
        title_label = QLabel("健康提醒助手")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 26px; font-weight: bold; color: rgba(200,180,255,1); border: none;")
        main_layout.addWidget(title_label)
        subtitle_label = QLabel("关爱健康，从每次提醒开始。")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12px; color: rgba(200,180,255,0.6); border: none; margin-bottom: 5px;")
        main_layout.addWidget(subtitle_label)

        # 主内容滚动区域
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        main_scroll_widget = QWidget()
        main_scroll_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(main_scroll_widget)
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(0, 0, 0, 0)
        main_scroll.setWidget(main_scroll_widget)

        # 提醒设置分组
        group = QGroupBox("提醒设置")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        self.form = QFormLayout(scroll_widget)
        self.form.setSpacing(10)
        self.form.setContentsMargins(10, 5, 10, 5)
        scroll.setWidget(scroll_widget)
        group_layout.addWidget(scroll)

        row_style = _row_style()

        # 内置提醒
        self.eye_check = QCheckBox("👀 护眼提醒")
        self.eye_check.setChecked(config["eye_care"]["enabled"])
        self.eye_spin = QSpinBox()
        self.eye_spin.setRange(1, 480)
        self.eye_spin.setValue(config["eye_care"]["interval"])
        self.eye_spin.setSuffix(" 分钟")
        eye_row = QWidget()
        eye_row.setStyleSheet(row_style)
        eye_lay = QHBoxLayout(eye_row)
        eye_lay.setContentsMargins(0, 0, 0, 0)
        eye_lay.addWidget(self.eye_check)
        eye_lay.addStretch()
        eye_lay.addWidget(QLabel("间隔:"))
        eye_lay.addWidget(self.eye_spin)
        self.form.addRow(eye_row)

        self.rest_check = QCheckBox("🧘 休息提醒")
        self.rest_check.setChecked(config["rest"]["enabled"])
        self.rest_spin = QSpinBox()
        self.rest_spin.setRange(1, 480)
        self.rest_spin.setValue(config["rest"]["interval"])
        self.rest_spin.setSuffix(" 分钟")
        rest_row = QWidget()
        rest_row.setStyleSheet(row_style)
        rest_lay = QHBoxLayout(rest_row)
        rest_lay.setContentsMargins(0, 0, 0, 0)
        rest_lay.addWidget(self.rest_check)
        rest_lay.addStretch()
        rest_lay.addWidget(QLabel("间隔:"))
        rest_lay.addWidget(self.rest_spin)
        self.form.addRow(rest_row)

        self.water_check = QCheckBox("💧 喝水提醒")
        self.water_check.setChecked(config["water"]["enabled"])
        self.water_spin = QSpinBox()
        self.water_spin.setRange(1, 480)
        self.water_spin.setValue(config["water"]["interval"])
        self.water_spin.setSuffix(" 分钟")
        water_row = QWidget()
        water_row.setStyleSheet(row_style)
        water_lay = QHBoxLayout(water_row)
        water_lay.setContentsMargins(0, 0, 0, 0)
        water_lay.addWidget(self.water_check)
        water_lay.addStretch()
        water_lay.addWidget(QLabel("间隔:"))
        water_lay.addWidget(self.water_spin)
        self.form.addRow(water_row)

        self._rebuild_custom_rows()
        content_layout.addWidget(group)

        # 添加自定义提醒
        add_btn = QPushButton("+ 添加自定义提醒")
        add_btn.clicked.connect(self._add_custom)
        content_layout.addWidget(add_btn)

        # 其他设置
        other_group = QGroupBox("高级设置")
        other_layout = QVBoxLayout(other_group)
        other_layout.setSpacing(10)

        # 勿扰模式
        dnd_row = QWidget()
        dnd_row.setStyleSheet(row_style)
        dnd_lay = QHBoxLayout(dnd_row)
        dnd_lay.setContentsMargins(0, 0, 0, 0)
        dnd_lay.addWidget(QLabel("🌙 勿扰模式"))
        dnd_lay.addStretch()

        # 时间选择合并容器
        time_box = QWidget()
        time_box.setStyleSheet("""
            background: rgba(200,180,255,0.15);
            border: 1px solid rgba(200,180,255,0.25);
            border-radius: 8px;
        """)
        time_lay = QHBoxLayout(time_box)
        time_lay.setContentsMargins(8, 4, 8, 4)
        time_lay.setSpacing(4)
        time_lay.addWidget(QLabel("从"))
        self.dnd_start = QLineEdit(config.get("dnd_start", "22:00"))
        self.dnd_start.setFixedWidth(50)
        self.dnd_start.setAlignment(Qt.AlignCenter)
        self.dnd_start.setStyleSheet("""
            QLineEdit {
                border: 1px solid rgba(200,180,255,0.2);
                border-radius: 4px;
                background: rgba(200,180,255,0.1);
                color: white;
                padding: 2px 4px;
            }
        """)
        time_lay.addWidget(self.dnd_start)
        time_lay.addWidget(QLabel("到"))
        self.dnd_end = QLineEdit(config.get("dnd_end", "08:00"))
        self.dnd_end.setFixedWidth(50)
        self.dnd_end.setAlignment(Qt.AlignCenter)
        self.dnd_end.setStyleSheet("""
            QLineEdit {
                border: 1px solid rgba(200,180,255,0.2);
                border-radius: 4px;
                background: rgba(200,180,255,0.1);
                color: white;
                padding: 2px 4px;
            }
        """)
        time_lay.addWidget(self.dnd_end)
        dnd_lay.addWidget(time_box)

        self.dnd_switch = ToggleSwitch(config.get("dnd_enabled", False))
        dnd_lay.addWidget(self.dnd_switch)
        other_layout.addWidget(dnd_row)

        # 提示音
        sound_row = QWidget()
        sound_row.setStyleSheet(row_style)
        sound_lay = QHBoxLayout(sound_row)
        sound_lay.setContentsMargins(0, 0, 0, 0)
        sound_lay.addWidget(QLabel("🔔 开启提示音"))
        sound_lay.addStretch()
        self.sound_switch = ToggleSwitch(config.get("sound", True))
        sound_lay.addWidget(self.sound_switch)
        other_layout.addWidget(sound_row)

        # 开机自启动
        autostart_row = QWidget()
        autostart_row.setStyleSheet(row_style)
        autostart_lay = QHBoxLayout(autostart_row)
        autostart_lay.setContentsMargins(0, 0, 0, 0)
        autostart_lay.addWidget(QLabel("🚀 开机自启动"))
        autostart_lay.addStretch()
        self.autostart_switch = ToggleSwitch(config.get("auto_start", False))
        autostart_lay.addWidget(self.autostart_switch)
        other_layout.addWidget(autostart_row)

        # 亮色模式
        theme_row = QWidget()
        theme_row.setStyleSheet(row_style)
        theme_lay = QHBoxLayout(theme_row)
        theme_lay.setContentsMargins(0, 0, 0, 0)
        theme_lay.addWidget(QLabel("🎨 亮/暗色模式"))
        theme_lay.addStretch()
        self.theme_switch = ToggleSwitch(config.get("theme", "light") == "dark")
        self.theme_switch.toggled.connect(self._on_theme_toggle)
        theme_lay.addWidget(self.theme_switch)
        other_layout.addWidget(theme_row)

        # 自定义渐变颜色
        self._grad_start_color = list(config.get("gradient_start")) if config.get("gradient_start") else None
        self._grad_end_color = list(config.get("gradient_end")) if config.get("gradient_end") else None

        grad_row = QWidget()
        grad_row.setStyleSheet(row_style)
        grad_lay = QHBoxLayout(grad_row)
        grad_lay.setContentsMargins(0, 0, 0, 0)
        grad_lay.addWidget(QLabel("🌈 渐变颜色"))
        grad_lay.addStretch()

        self._grad_start_preview = QLabel()
        self._grad_start_preview.setFixedSize(24, 24)
        self._update_color_preview(self._grad_start_preview, self._grad_start_color or list(THEME_PRESETS[config.get("theme", "light")]["primary"]))
        self._grad_start_preview.setCursor(Qt.PointingHandCursor)
        self._grad_start_preview.mousePressEvent = lambda _: self._pick_gradient_color("start")
        grad_lay.addWidget(self._grad_start_preview)

        grad_lay.addWidget(QLabel("→"))

        self._grad_end_preview = QLabel()
        self._grad_end_preview.setFixedSize(24, 24)
        self._update_color_preview(self._grad_end_preview, self._grad_end_color or list(THEME_PRESETS[config.get("theme", "light")]["secondary"]))
        self._grad_end_preview.setCursor(Qt.PointingHandCursor)
        self._grad_end_preview.mousePressEvent = lambda _: self._pick_gradient_color("end")
        grad_lay.addWidget(self._grad_end_preview)

        reset_btn = QPushButton("重置")
        reset_btn.setFixedSize(50, 28)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,180,255,0.1); color: rgba(200,180,255,0.7);
                border: 1px solid rgba(200,180,255,0.15); border-radius: 6px;
                font-size: 11px; padding: 0;
            }
            QPushButton:hover { background: rgba(200,180,255,0.2); color: rgba(200,180,255,1); }
        """)
        reset_btn.setToolTip("恢复主题默认颜色")
        reset_btn.clicked.connect(self._reset_gradient_colors)
        grad_lay.addWidget(reset_btn)

        other_layout.addWidget(grad_row)

        content_layout.addWidget(other_group)
        main_layout.addWidget(main_scroll)

        # 底部按钮
        bottom = QHBoxLayout()
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(save_btn)
        bottom.addWidget(cancel_btn)
        main_layout.addLayout(bottom)

        # 作者和版本号
        footer_label = QLabel("Bhands  V1.0")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("font-size: 11px; color: rgba(200,180,255,0.35); border: none;")
        main_layout.addWidget(footer_label)

        # 回车保存但不退出
        self.eye_spin.editingFinished.connect(self._auto_save)
        self.rest_spin.editingFinished.connect(self._auto_save)
        self.water_spin.editingFinished.connect(self._auto_save)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._auto_save()
            return
        super().keyPressEvent(event)

    def _apply_style(self):
        theme = self.config.get("theme", "light")
        self.setStyleSheet(_build_dialog_style(
            theme, self._check_path, self._arrow_up_path, self._arrow_down_path))

    def _on_theme_toggle(self, checked):
        theme = "dark" if checked else "light"
        self.config["gradient_start"] = self._grad_start_color
        self.config["gradient_end"] = self._grad_end_color
        apply_theme(theme)
        apply_gradient_colors(self.config)
        self.config["theme"] = theme
        self._apply_style()
        if self.parent():
            self.parent().config["theme"] = theme
            self.parent().update()
        save_config(self.config)

    def _update_color_preview(self, label, color):
        """更新色块预览"""
        r, g, b = color[0], color[1], color[2]
        label.setStyleSheet(
            f"background: rgb({r},{g},{b}); border: 2px solid rgba(200,180,255,0.3); border-radius: 4px;")

    def _pick_gradient_color(self, which):
        """弹出颜色选择器"""
        if which == "start":
            current = self._grad_start_color or list(THEME_PRESETS[self.config.get("theme", "light")]["primary"])
        else:
            current = self._grad_end_color or list(THEME_PRESETS[self.config.get("theme", "light")]["secondary"])
        color = QColorDialog.getColor(QColor(*current), self, "选择渐变颜色")
        if color.isValid():
            rgb = [color.red(), color.green(), color.blue()]
            if which == "start":
                self._grad_start_color = rgb
                self._update_color_preview(self._grad_start_preview, rgb)
            else:
                self._grad_end_color = rgb
                self._update_color_preview(self._grad_end_preview, rgb)

    def _reset_gradient_colors(self):
        """重置为主题默认渐变颜色"""
        self._grad_start_color = None
        self._grad_end_color = None
        theme = self.config.get("theme", "light")
        self._update_color_preview(self._grad_start_preview, list(THEME_PRESETS[theme]["primary"]))
        self._update_color_preview(self._grad_end_preview, list(THEME_PRESETS[theme]["secondary"]))

    def _rebuild_custom_rows(self):
        for container in self.custom_containers:
            self.form.removeRow(container)
        self.custom_checks.clear()
        self.custom_spins.clear()
        self.custom_btn_widgets.clear()
        self.custom_containers.clear()

        row_style = _row_style()

        for i, item in enumerate(self.custom_items):
            check = QCheckBox(f"{item['icon']} {item['name']}")
            check.setChecked(item.get("enabled", True))
            self.custom_checks.append(check)

            spin = QSpinBox()
            spin.setRange(1, 480)
            spin.setValue(item.get("interval", 30))
            spin.setSuffix(" 分钟")
            spin.editingFinished.connect(self._auto_save)
            self.custom_spins.append(spin)

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            row_layout.addWidget(spin)

            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(35, 35)
            edit_btn.setObjectName("editBtn")
            edit_btn.setToolTip("编辑")
            edit_btn.clicked.connect(lambda _, x=i: self._edit_custom(x))
            row_layout.addWidget(edit_btn)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(35, 35)
            del_btn.setObjectName("delBtn")
            del_btn.setToolTip("删除")
            del_btn.clicked.connect(lambda _, x=i: self._del_custom(x))
            row_layout.addWidget(del_btn)

            self.custom_btn_widgets.append(row_widget)

            container = QWidget()
            container.setStyleSheet(row_style)
            container_lay = QHBoxLayout(container)
            container_lay.setContentsMargins(0, 0, 0, 0)
            container_lay.addWidget(check)
            container_lay.addStretch()
            container_lay.addWidget(row_widget)
            self.custom_containers.append(container)
            self.form.addRow(container)

    def _add_custom(self):
        dialog = CustomReminderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.custom_items.append(dialog.get_data())
            self._rebuild_custom_rows()

    def _edit_custom(self, idx):
        if idx < 0 or idx >= len(self.custom_items):
            return
        dialog = CustomReminderDialog(self, self.custom_items[idx])
        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            new_data["enabled"] = self.custom_items[idx].get("enabled", True)
            self.custom_items[idx] = new_data
            self._rebuild_custom_rows()

    def _del_custom(self, idx):
        if idx < 0 or idx >= len(self.custom_items):
            return
        name = self.custom_items[idx]["name"]
        ret = QMessageBox.question(self, "确认删除", f"确定要删除「{name}」吗？",
                                   QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.custom_items.pop(idx)
            self._rebuild_custom_rows()

    def _auto_save(self):
        """保存配置但不关闭对话框"""
        self.config["eye_care"]["enabled"] = self.eye_check.isChecked()
        self.config["eye_care"]["interval"] = self.eye_spin.value()
        self.config["rest"]["enabled"] = self.rest_check.isChecked()
        self.config["rest"]["interval"] = self.rest_spin.value()
        self.config["water"]["enabled"] = self.water_check.isChecked()
        self.config["water"]["interval"] = self.water_spin.value()
        self.config["sound"] = self.sound_switch.isChecked()
        self.config["auto_start"] = self.autostart_switch.isChecked()
        self.config["dnd_enabled"] = self.dnd_switch.isChecked()
        self.config["theme"] = "dark" if self.theme_switch.isChecked() else "light"
        self.config["dnd_start"] = self.dnd_start.text().strip()
        self.config["dnd_end"] = self.dnd_end.text().strip()
        self.config["gradient_start"] = self._grad_start_color
        self.config["gradient_end"] = self._grad_end_color

        custom = []
        for i, item in enumerate(self.custom_items):
            item["enabled"] = self.custom_checks[i].isChecked()
            item["interval"] = self.custom_spins[i].value()
            custom.append(item)
        self.config["custom"] = custom

        save_config(self.config)

    def save(self):
        """保存配置并关闭对话框"""
        self._auto_save()
        apply_theme(self.config.get("theme", "light"))
        apply_gradient_colors(self.config)
        set_autostart(self.config.get("auto_start", False))
        if self.parent():
            self.parent().config = self.config
            self.parent().update()
        self.accept()


# ==================== 悬浮窗口（主界面） ====================

class FloatingWidget(QWidget):
    """悬浮窗口 - 支持迷你模式、进度环、勿扰"""

    BUILTIN = {
        "eye_care": ("👀", "护眼提醒", "让眼睛休息一下，远眺20秒吧！", (102, 126, 234)),
        "rest": ("🧘", "休息提醒", "站起来活动一下，伸个懒腰吧！", (118, 75, 162)),
        "water": ("💧", "喝水提醒", "记得喝水哦，保持身体水分！", (72, 209, 204)),
    }

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.paused = False
        self.drag_pos = QPoint()
        self.timers = {}
        self.next_times = {}
        self.snooze_timers = {}
        self.mini_mode = self.config.get("mini_mode", False)
        self.hovered = False

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_display)
        self.countdown_timer.start(100)

        self.init_ui()
        self.init_timers()
        self.init_tray()
        self.init_shortcuts()

    def init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.update_size()
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 80)

    def update_size(self):
        if self.mini_mode:
            size = self.config.get("widget_size", 80)
            self.setFixedSize(size, size)
        else:
            self.setFixedSize(220, 120)

    def _get_all_reminders(self):
        reminders = {}
        for key, (icon, title, msg, color) in self.BUILTIN.items():
            cfg = self.config.get(key, {})
            reminders[key] = {
                "icon": icon, "name": title, "message": msg,
                "color": color, "interval": cfg.get("interval", 20),
                "enabled": cfg.get("enabled", False),
            }
        for i, item in enumerate(self.config.get("custom", [])):
            key = f"custom_{i}"
            reminders[key] = {
                "icon": item.get("icon", "🔔"),
                "name": item.get("name", "自定义"),
                "message": item.get("message", ""),
                "color": CUSTOM_COLORS[i % len(CUSTOM_COLORS)],
                "interval": item.get("interval", 30),
                "enabled": item.get("enabled", True),
            }
        return reminders

    def init_timers(self):
        for key, info in self._get_all_reminders().items():
            if info["enabled"]:
                interval = info["interval"] * 60 * 1000
                timer = QTimer(self)
                timer.timeout.connect(lambda k=key: self.trigger_reminder(k))
                timer.start(interval)
                self.timers[key] = timer
                self.next_times[key] = datetime.now() + timedelta(milliseconds=interval)

    def reinit_timers(self):
        for timer in self.timers.values():
            timer.stop()
        for timer in self.snooze_timers.values():
            timer.stop()
        self.timers.clear()
        self.next_times.clear()
        self.snooze_timers.clear()
        self.init_timers()

    def trigger_reminder(self, key):
        if self.paused:
            return
        if is_dnd_active(self.config):
            return

        all_rem = self._get_all_reminders()
        if key not in all_rem:
            return
        info = all_rem[key]

        interval = info["interval"] * 60 * 1000
        self.next_times[key] = datetime.now() + timedelta(milliseconds=interval)

        # 记录统计
        record_stat(key, "triggered")

        # 播放提示音
        if self.config.get("sound", True):
            play_reminder_sound(key if key in BUILTIN_REMINDERS else "custom")

        # 系统通知
        try:
            notification.notify(title=info["name"], message=info["message"], timeout=5, app_name="健康提醒")
        except Exception:
            pass

        # 弹窗
        popup = ReminderPopup(f"{info['icon']} {info['message']}", info["color"], key, interval=info["interval"])
        popup.snooze_signal.connect(self.handle_snooze)
        popup.show()
        # 保持引用防止被回收
        if not hasattr(self, '_popups'):
            self._popups = []
        self._popups.append(popup)
        # 清理已关闭的弹窗引用
        self._popups = [p for p in self._popups if p.isVisible()]

    def handle_snooze(self, key, minutes):
        """处理贪睡"""
        if key in self.timers:
            self.timers[key].stop()

        def _snooze_callback(k=key):
            # 贪睡结束后重启原始定时器
            if k in self.timers:
                self.timers[k].start()
            self.trigger_reminder(k)

        snooze_timer = QTimer(self)
        snooze_timer.setSingleShot(True)
        snooze_timer.timeout.connect(_snooze_callback)
        snooze_timer.start(minutes * 60 * 1000)
        self.snooze_timers[key] = snooze_timer

    def get_next_reminder(self):
        if not self.next_times:
            return None, None
        nearest_key = min(self.next_times, key=lambda k: self.next_times[k])
        remaining = self.next_times[nearest_key] - datetime.now()
        if remaining.total_seconds() < 0:
            remaining = timedelta(seconds=0)
        return nearest_key, remaining

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.mini_mode:
            self._paint_mini(painter)
        else:
            self._paint_full(painter)

    def _paint_mini(self, painter):
        """迷你模式绘制"""
        size = self.config.get("widget_size", 80)
        shadow_offset = max(4, size // 12)
        circle_size = size - shadow_offset
        circle_r = circle_size // 2

        # 阴影
        shadow = QColor(0, 0, 0, 50)
        painter.setBrush(QBrush(shadow))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_offset, shadow_offset, circle_size, circle_size, circle_r, circle_r)

        # 圆形背景
        gradient = QRadialGradient(circle_r, circle_r, circle_r)
        gradient.setColorAt(0, QColor(*THEME["primary"], 230))
        gradient.setColorAt(1, QColor(*THEME["secondary"], 230))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, circle_size, circle_size, circle_r, circle_r)

        # 进度环
        key, remaining = self.get_next_reminder()
        all_rem = self._get_all_reminders()
        if key and remaining and key in all_rem:
            info = all_rem[key]
            total = info["interval"] * 60
            elapsed = total - remaining.total_seconds()
            progress = max(0, min(1, elapsed / total))
            ring_r = circle_r - 7
            draw_progress_ring(painter, circle_r, circle_r, ring_r, progress, info["color"])

            # 图标（内置提醒眨眼效果）
            icon_size = max(12, circle_size // 4)
            t = time.time() % 3.5
            blink = t < 0.4
            if key == "eye_care" and blink:
                self._draw_closed_eyes(painter, circle_r, icon_size)
            elif key == "rest" and blink:
                self._draw_closed_rest(painter, circle_r, icon_size)
            elif key == "water" and blink:
                self._draw_closed_water(painter, circle_r, icon_size)
            else:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Segoe UI Emoji", icon_size))
                painter.drawText(0, 0, circle_size, circle_size, Qt.AlignCenter, info["icon"])
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Segoe UI Emoji", max(12, circle_size // 4)))
            painter.drawText(0, 0, circle_size, circle_size, Qt.AlignCenter, "💚")

    def _draw_closed_eyes(self, painter, cx, size):
        """绘制闭眼状态的 👀 风格图标"""
        painter.setPen(Qt.NoPen)
        ew = int(size * 1.0)   # 眼睛宽度
        eh = int(size * 0.6)   # 眼睛高度
        gap = int(size * 0.35) # 两眼间距
        pupil_r = int(eh * 0.28)

        for side in (-1, 1):
            ex = cx + side * (ew // 2 + gap // 2) - ew // 2
            ey = cx - eh // 2

            # 白色眼球
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(ex, ey, ew, eh)

            # 黑色瞳孔
            px = ex + int(ew * 0.6) - pupil_r
            py = ey + int(eh * 0.55) - pupil_r
            painter.setBrush(QColor(30, 30, 30))
            painter.drawEllipse(px, py, pupil_r * 2, pupil_r * 2)

            # 上眼皮（从顶部盖住上半部分）
            painter.setBrush(QColor(*THEME["primary"], 230))
            painter.drawRect(ex - 1, ey - 1, ew + 2, eh // 2 + 2)

    def _draw_closed_rest(self, painter, cx, size):
        """绘制闭眼状态的休息图标 🧘"""
        painter.setPen(Qt.NoPen)
        s = size * 1.5
        # 头
        head_r = int(s * 0.22)
        painter.setBrush(QColor(255, 200, 150))
        painter.drawEllipse(cx - head_r, cx - int(s * 0.48), head_r * 2, head_r * 2)
        # 闭眼（两条横线）
        painter.setPen(QPen(QColor(80, 60, 50), max(1, int(s * 0.06)), Qt.SolidLine, Qt.RoundCap))
        hy = cx - int(s * 0.44)
        painter.drawLine(cx - int(head_r * 0.6), hy, cx - int(head_r * 0.15), hy)
        painter.drawLine(cx + int(head_r * 0.15), hy, cx + int(head_r * 0.6), hy)
        painter.setPen(Qt.NoPen)
        # 身体
        painter.setBrush(QColor(118, 75, 162))
        body_y = cx - int(s * 0.25)
        painter.drawEllipse(cx - int(s * 0.3), body_y, int(s * 0.6), int(s * 0.4))
        # 盘腿
        leg_y = cx + int(s * 0.05)
        painter.drawEllipse(cx - int(s * 0.42), leg_y, int(s * 0.84), int(s * 0.25))

    def _draw_closed_water(self, painter, cx, size):
        """绘制半满状态的水滴图标 💧"""
        painter.setPen(Qt.NoPen)
        s = size * 1.2
        drop_h = int(s * 0.9)
        drop_w = int(s * 0.55)
        top = cx - drop_h // 2

        # 水滴轮廓（倒三角 + 底部圆弧）
        path = QPainterPath()
        path.moveTo(cx, top)
        path.quadTo(cx + drop_w, top + drop_h * 0.55, cx + drop_w * 0.5, top + drop_h * 0.75)
        path.arcTo(cx - drop_w * 0.5, top + drop_h * 0.5, drop_w, drop_h * 0.5, 0, 180)
        path.quadTo(cx - drop_w, top + drop_h * 0.55, cx, top)

        # 空心水滴（白色描边）
        painter.setBrush(QColor(255, 255, 255, 80))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawPath(path)

        # 半满水位
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(72, 209, 204, 160))
        water_y = top + drop_h * 0.45
        water_clip = QPainterPath()
        water_clip.addRect(cx - drop_w, water_y, drop_w * 2, drop_h)
        filled = path.intersected(water_clip)
        painter.drawPath(filled)

    def _paint_full(self, painter):
        """完整模式绘制"""
        # 阴影
        shadow = QColor(0, 0, 0, 50)
        painter.setBrush(QBrush(shadow))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(6, 6, self.width() - 6, self.height() - 6, 18, 18)

        # 渐变背景
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(*THEME["primary"], 230))
        gradient.setColorAt(1, QColor(*THEME["secondary"], 230))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, self.width() - 6, self.height() - 6, 18, 18)

        # 标题
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        if is_dnd_active(self.config):
            status = "🌙 勿扰中"
        elif self.paused:
            status = "⏸ 已暂停"
        else:
            status = "💚 健康提醒"
        painter.drawText(15, 12, self.width() - 20, 25, Qt.AlignLeft, status)

        # 倒计时
        key, remaining = self.get_next_reminder()
        all_rem = self._get_all_reminders()
        if key and remaining and key in all_rem:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            info = all_rem[key]
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.setPen(QColor(255, 255, 255, 220))
            painter.drawText(15, 40, self.width() - 20, 20, Qt.AlignLeft,
                           f"{info['icon']} {info['name']}  {mins:02d}:{secs:02d}")

            # 迷你进度条
            total = info["interval"] * 60
            elapsed = total - remaining.total_seconds()
            progress = max(0, min(1, elapsed / total))
            bar_y = 65
            bar_width = self.width() - 30
            painter.setBrush(QColor(255, 255, 255, 40))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(15, bar_y, bar_width, 5, 2, 2)
            painter.setBrush(QColor(255, 255, 255, 180))
            painter.drawRoundedRect(15, bar_y, int(bar_width * progress), 5, 2, 2)
        else:
            painter.setFont(QFont("Microsoft YaHei", 10))
            painter.setPen(QColor(255, 255, 255, 180))
            painter.drawText(15, 40, self.width() - 20, 20, Qt.AlignLeft, "无提醒")

        # 底部提示
        painter.setFont(QFont("Microsoft YaHei", 8))
        painter.setPen(QColor(255, 255, 255, 120))
        painter.drawText(15, self.height() - 25, self.width() - 20, 20, Qt.AlignLeft, "右键菜单 | 双击设置")

    def update_display(self):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_settings()

    def enterEvent(self, event):
        self.hovered = True
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(50,50,70,240);
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 10px;
                padding: 5px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background: rgba(102,126,234,0.6);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255,255,255,0.15);
                margin: 4px 10px;
            }
        """)

        # 暂停/继续
        pause_text = "▶ 继续提醒" if self.paused else "⏸ 暂停提醒"
        pause_action = QAction(pause_text, self)
        pause_action.triggered.connect(self.toggle_pause)
        menu.addAction(pause_action)

        # 迷你/完整模式
        mode_text = "🔲 完整模式" if self.mini_mode else "🔳 迷你模式"
        mode_action = QAction(mode_text, self)
        mode_action.triggered.connect(self.toggle_mini_mode)
        menu.addAction(mode_action)

        # 迷你模式大小滑条
        if self.mini_mode:
            size_container = QWidget()
            size_layout = QHBoxLayout(size_container)
            size_layout.setContentsMargins(12, 4, 12, 4)
            size_layout.setSpacing(8)
            size_label = QLabel(f"大小: {self.config.get('widget_size', 80)}")
            size_label.setFixedWidth(65)
            size_label.setStyleSheet("color: white; font-size: 12px;")
            size_slider = QSlider(Qt.Horizontal)
            size_slider.setRange(60, 200)
            size_slider.setValue(self.config.get("widget_size", 80))
            size_slider.setStyleSheet("""
                QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,0.2); border-radius: 2px; }
                QSlider::handle:horizontal { width: 14px; height: 14px; margin: -5px 0; background: white; border-radius: 7px; }
                QSlider::sub-page:horizontal { background: rgba(102,126,234,0.8); border-radius: 2px; }
            """)
            size_slider.valueChanged.connect(lambda v: self._on_size_changed(v, size_label))
            size_layout.addWidget(size_label)
            size_layout.addWidget(size_slider)
            size_action = QWidgetAction(self)
            size_action.setDefaultWidget(size_container)
            menu.addAction(size_action)

        menu.addSeparator()

        # 勿扰开关
        dnd_text = "🔔 关闭勿扰" if self.config.get("dnd_enabled") else "🌙 开启勿扰"
        dnd_action = QAction(dnd_text, self)
        dnd_action.triggered.connect(self.toggle_dnd)
        menu.addAction(dnd_action)

        menu.addSeparator()

        # 今日统计
        stats_action = QAction("📊 今日统计", self)
        stats_action.triggered.connect(self.show_stats)
        menu.addAction(stats_action)

        # 设置
        settings_action = QAction("⚙ 设置", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # 退出
        quit_action = QAction("✖ 退出", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        menu.exec_(event.globalPos())

    def toggle_pause(self):
        self.paused = not self.paused
        if self.paused:
            for timer in self.timers.values():
                timer.stop()
        else:
            self.reinit_timers()

    def toggle_mini_mode(self):
        old_pos = self.pos()
        self.mini_mode = not self.mini_mode
        self.config["mini_mode"] = self.mini_mode
        save_config(self.config)
        self.update_size()
        self.move(old_pos)

    def _on_size_changed(self, value, label):
        self.config["widget_size"] = value
        save_config(self.config)
        label.setText(f"大小: {value}")
        if self.mini_mode:
            self.update_size()

    def toggle_dnd(self):
        self.config["dnd_enabled"] = not self.config.get("dnd_enabled", False)
        save_config(self.config)

    def show_stats(self):
        """显示今日统计"""
        stats = get_today_stats()
        if not stats:
            QMessageBox.information(self, "今日统计", "今天还没有提醒记录哦~")
            return

        all_rem = self._get_all_reminders()
        lines = ["📊 今日提醒统计\n"]
        total_triggered = 0
        total_completed = 0
        for key, data in stats.items():
            name = all_rem.get(key, {}).get("name", key)
            triggered = data.get("triggered", 0)
            completed = data.get("completed", 0)
            total_triggered += triggered
            total_completed += completed
            lines.append(f"  {name}: 触发 {triggered} 次, 完成 {completed} 次")

        lines.append(f"\n总计: 触发 {total_triggered} 次, 完成 {total_completed} 次")
        QMessageBox.information(self, "今日统计", "\n".join(lines))

    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config = dialog.config
            self.update_size()
            self.reinit_timers()

    def init_tray(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(*THEME["primary"]))
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI Emoji", 16))
        painter.drawText(0, 0, 32, 32, Qt.AlignCenter, "💚")
        painter.end()
        icon = QIcon(pixmap)

        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("健康提醒")

        tray_menu = QMenu()
        show_action = QAction("显示悬浮窗", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

    def init_shortcuts(self):
        """初始化全局快捷键"""
        # Ctrl+Shift+P 暂停/继续
        QShortcut(QKeySequence("Ctrl+Shift+P"), self).activated.connect(self.toggle_pause)
        # Ctrl+Shift+S 设置
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.open_settings)
        # Ctrl+Shift+Q 退出
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self).activated.connect(self.quit_app)
        # Ctrl+Shift+M 迷你模式
        QShortcut(QKeySequence("Ctrl+Shift+M"), self).activated.connect(self.toggle_mini_mode)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    def quit_app(self):
        self.tray.hide()
        QApplication.quit()


# ==================== 程序入口 ====================

class _TooltipLabel(QLabel):
    """自定义圆角 Tooltip，避免黑角"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent; color: rgba(200,180,255,1);")
        self.setContentsMargins(10, 6, 10, 6)

    def show_at(self, text, pos):
        font = self.font()
        font.setPointSize(10)
        self.setFont(font)
        self.setText(text)
        self.adjustSize()
        self.move(pos.x() + 12, pos.y() + 12)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(30, 30, 50, 230))
        painter.setPen(QColor(200, 180, 255, 76))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
        painter.end()
        super().paintEvent(event)


_tooltip = None


class _TooltipFilter(QObject):
    """全局事件过滤器，拦截 Tooltip 显示自定义圆角提示"""
    def eventFilter(self, obj, event):
        global _tooltip
        if event.type() == QEvent.ToolTip:
            text = obj.toolTip()
            if text:
                if _tooltip is None:
                    _tooltip = _TooltipLabel()
                font = _tooltip.font()
                font.setPointSize(9)
                _tooltip.setFont(font)
                _tooltip.show_at(text, event.globalPos())
            return True
        if event.type() in (QEvent.Leave, QEvent.Hide, QEvent.WindowDeactivate):
            if _tooltip is not None:
                _tooltip.hide()
        return super().eventFilter(obj, event)


def main():
    # 设置 Windows AppUserModelID，使通知标题显示为"健康提醒"而非"Python"
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("健康提醒.V1.0")
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.installEventFilter(_TooltipFilter(app))
    create_checkmark_icon()
    create_arrow_icons()

    widget = FloatingWidget()
    apply_theme(widget.config.get("theme", "light"))
    apply_gradient_colors(widget.config)
    set_autostart(widget.config.get("auto_start", False))
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
