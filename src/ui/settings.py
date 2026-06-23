# -*- coding: utf-8 -*-
"""设置面板：SettingsDialog（卡片式布局）+ CustomReminderDialog"""

import logging

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, QCheckBox,
    QPushButton, QLineEdit, QScrollArea, QGroupBox, QFormLayout,
    QColorDialog, QComboBox, QMessageBox, QWidget,
)
from PyQt5.QtWidgets import QGraphicsBlurEffect
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPixmap, QIcon, QPainter

from constants import (
    THEME, THEME_PRESETS, BUILTIN_REMINDERS, CUSTOM_COLORS,
    ICON_CHOICES, ICON_NAMES, FONT_UI, FONT_EMOJI, CHECK_ICON,
    ARROW_UP_ICON, ARROW_DOWN_ICON, POPUP_POSITION_MAP,
)
from utils import save_config, set_autostart
from constants import apply_theme, apply_gradient_colors
from ui.widgets import ToggleSwitch

logger = logging.getLogger(__name__)

# ==================== 样式定义 ====================

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
            background: rgba(180,180,220,0.12);
            border: 1px solid rgba(200,200,220,0.1);
            border-radius: 10px; padding: 8px 12px;
        """
    else:
        return """
            background: rgba(200,180,255,0.12);
            border: 1px solid rgba(200,180,255,0.15);
            border-radius: 10px; padding: 8px 12px;
        """


def _build_dialog_style(theme_name, check_path, arrow_up_path, arrow_down_path):
    c = _DIALOG_COLORS.get(theme_name, _DIALOG_COLORS["dark"])
    p = THEME.get("primary", (102, 126, 234))
    s = THEME.get("secondary", (118, 75, 162))
    if theme_name == "dark":
        bg_grad = c["bg"]
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
        QDialog { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, %(bg)s); }
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
            background: %(input_bg)s;
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
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, %(grp_bg)s);
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


# ==================== 自定义提醒对话框 ====================

class CustomReminderDialog(QDialog):
    """自定义提醒添加/编辑对话框"""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("自定义提醒" if data is None else "编辑提醒")
        self.setMinimumSize(380, 280)
        self.config = parent.config if parent and hasattr(parent, "config") else {}
        self.data = data
        self._selected_icon = data.get("icon", "☕") if data else "☕"

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 名称
        self.name_edit = QLineEdit(data.get("name", "") if data else "")
        self.name_edit.setPlaceholderText("提醒名称（如：吃药）")
        layout.addWidget(QLabel("名称:"))
        layout.addWidget(self.name_edit)

        # 图标选择（下拉列表）
        self.icon_combo = QComboBox()
        for icon in ICON_CHOICES:
            name = ICON_NAMES.get(icon, "")
            display = f"{icon}  {name}" if name else icon
            self.icon_combo.addItem(display, icon)
        idx = ICON_CHOICES.index(self._selected_icon) if self._selected_icon in ICON_CHOICES else 0
        self.icon_combo.setCurrentIndex(idx)
        self.icon_combo.setFixedSize(120, 36)
        self.icon_combo.setStyleSheet("""
            QComboBox {
                background: rgba(200,180,255,0.1); color: rgba(200,180,255,1);
                border: 1px solid rgba(200,180,255,0.2); border-radius: 8px;
                padding: 4px 8px; font-size: 15px;
            }
            QComboBox:hover { border: 1px solid rgba(200,180,255,0.4); }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox::down-arrow { width: 12px; height: 12px; }
            QComboBox QAbstractItemView {
                background: rgba(30,30,50,240); color: rgba(200,180,255,1);
                selection-background-color: rgba(200,180,255,0.15);
                border: 1px solid rgba(200,180,255,0.2);
                font-size: 15px; padding: 4px;
            }
        """)
        self.icon_combo.currentIndexChanged.connect(
            lambda idx: setattr(self, "_selected_icon", self.icon_combo.currentData()))
        icon_row = QHBoxLayout()
        icon_row.addWidget(QLabel("选择图标:"))
        icon_row.addWidget(self.icon_combo)
        icon_row.addStretch()
        layout.addLayout(icon_row)

        # 提醒消息
        self.msg_edit = QLineEdit(data.get("message", "") if data else "")
        self.msg_edit.setPlaceholderText("提醒消息（如：该吃药了）")
        layout.addWidget(QLabel("提醒消息:"))
        layout.addWidget(self.msg_edit)

        # 间隔时间
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 480)
        self.interval_spin.setValue(data.get("interval", 30) if data else 30)
        self.interval_spin.setSuffix(" 分钟")
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("间隔时间:"))
        interval_layout.addWidget(self.interval_spin)
        layout.addLayout(interval_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _icon_btn_style(self, selected):
        if selected:
            return """
                QPushButton {
                    background: rgba(102,126,234,0.4);
                    border: 2px solid rgba(102,126,234,0.8);
                    border-radius: 8px;
                    font-size: 16px;
                }
            """
        return """
            QPushButton {
                background: rgba(200,180,255,0.08);
                border: 1px solid rgba(200,180,255,0.15);
                border-radius: 8px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(200,180,255,0.2);
                border: 1px solid rgba(200,180,255,0.4);
            }
        """

    def _select_icon(self, icon):
        self._selected_icon = icon
        for i, btn in self.icon_buttons.items():
            btn.setStyleSheet(self._icon_btn_style(i == icon))

    def get_data(self):
        return {
            "name": self.name_edit.text().strip() or "自定义提醒",
            "icon": self._selected_icon,
            "message": self.msg_edit.text().strip() or "该做点什么了",
            "interval": self.interval_spin.value(),
            "enabled": True,
        }

    def accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请输入提醒名称")
            return
        super().accept()


# ==================== 设置面板 ====================

class SettingsDialog(QDialog):
    """设置面板 - 卡片式布局"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(400, 500)
        self.resize(500, 800)
        self.config = dict(config)  # 副本
        self.custom_items = [dict(item) for item in config.get("custom", [])]

        self._check_path = CHECK_ICON.replace("\\", "/")
        self._arrow_up_path = ARROW_UP_ICON.replace("\\", "/")
        self._arrow_down_path = ARROW_DOWN_ICON.replace("\\", "/")

        self._apply_style()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        main_scroll.setStyleSheet("background: transparent;")

        bg_widget = QWidget()
        bg_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        bg_widget.setStyleSheet("background: rgba(255,255,255,0.08);")
        blur = QGraphicsBlurEffect(bg_widget)
        blur.setBlurRadius(18)
        bg_widget.setGraphicsEffect(blur)

        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(14)
        main_scroll.setWidget(content_widget)

        row_style = _row_style()

        # ---- 内置提醒分组 ----
        builtin_group = QGroupBox("📋 内置提醒")
        builtin_layout = QVBoxLayout(builtin_group)
        builtin_layout.setSpacing(8)

        # 护眼
        eye_row = QWidget()
        eye_row.setStyleSheet(row_style)
        eye_lay = QHBoxLayout(eye_row)
        eye_lay.setContentsMargins(0, 0, 0, 0)
        eye_lay.addWidget(QLabel("👀 护眼提醒"))
        eye_lay.addStretch()
        self.eye_switch = ToggleSwitch(config["eye_care"]["enabled"])
        eye_lay.addWidget(self.eye_switch)
        self.eye_spin = QSpinBox()
        self.eye_spin.setRange(1, 480)
        self.eye_spin.setValue(config["eye_care"]["interval"])
        self.eye_spin.setSuffix(" 分钟")
        eye_lay.addWidget(self.eye_spin)
        builtin_layout.addWidget(eye_row)

        # 休息
        rest_row = QWidget()
        rest_row.setStyleSheet(row_style)
        rest_lay = QHBoxLayout(rest_row)
        rest_lay.setContentsMargins(0, 0, 0, 0)
        rest_lay.addWidget(QLabel("🧘 休息提醒"))
        rest_lay.addStretch()
        self.rest_switch = ToggleSwitch(config["rest"]["enabled"])
        rest_lay.addWidget(self.rest_switch)
        self.rest_spin = QSpinBox()
        self.rest_spin.setRange(1, 480)
        self.rest_spin.setValue(config["rest"]["interval"])
        self.rest_spin.setSuffix(" 分钟")
        rest_lay.addWidget(self.rest_spin)
        builtin_layout.addWidget(rest_row)

        # 喝水
        water_row = QWidget()
        water_row.setStyleSheet(row_style)
        water_lay = QHBoxLayout(water_row)
        water_lay.setContentsMargins(0, 0, 0, 0)
        water_lay.addWidget(QLabel("💧 喝水提醒"))
        water_lay.addStretch()
        self.water_switch = ToggleSwitch(config["water"]["enabled"])
        water_lay.addWidget(self.water_switch)
        self.water_spin = QSpinBox()
        self.water_spin.setRange(1, 480)
        self.water_spin.setValue(config["water"]["interval"])
        self.water_spin.setSuffix(" 分钟")
        water_lay.addWidget(self.water_spin)
        builtin_layout.addWidget(water_row)

        title_label = QLabel("健康提醒助手")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 30px; font-weight: bold; color: rgba(200,180,255,0.95); padding: 8px 0 2px 0; border: none;")
        content_layout.addWidget(title_label)

        subtitle_label = QLabel("关爱健康，从每次提醒开始")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("font-size: 12px; color: rgba(200,180,255,0.55); padding: 0 0 8px 0; border: none;")
        content_layout.addWidget(subtitle_label)

        content_layout.addWidget(builtin_group)

        # ---- 自定义提醒分组 ----
        self.builtin_layout = builtin_layout

        self.custom_checks = []
        self.custom_spins = []
        self.custom_btn_widgets = []
        self.custom_containers = []
        self._rebuild_custom_rows()

        add_btn = QPushButton("＋ 添加自定义提醒")
        add_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,180,255,0.1); color: rgba(200,180,255,0.85);
                border: 1px solid rgba(200,180,255,0.15); border-radius: 10px;
                padding: 10px 16px; font-size: 13px;
            }
            QPushButton:hover {
                background: rgba(200,180,255,0.18); color: rgba(200,180,255,1);
            }
        """)
        add_btn.clicked.connect(self._add_custom)
        content_layout.addWidget(add_btn)

        # ---- 勿扰模式分组 ----
        dnd_group = QGroupBox("🌙 勿扰模式")
        dnd_layout = QVBoxLayout(dnd_group)
        dnd_layout.setSpacing(8)

        dnd_row = QWidget()
        dnd_row.setStyleSheet(row_style)
        dnd_lay = QHBoxLayout(dnd_row)
        dnd_lay.setContentsMargins(0, 0, 0, 0)
        dnd_lay.addWidget(QLabel("启用勿扰"))
        dnd_lay.addStretch()
        self.dnd_switch = ToggleSwitch(config.get("dnd_enabled", False))
        dnd_lay.addWidget(self.dnd_switch)
        dnd_layout.addWidget(dnd_row)

        time_row = QWidget()
        time_row.setStyleSheet(row_style)
        time_lay = QHBoxLayout(time_row)
        time_lay.setContentsMargins(0, 0, 0, 0)
        time_lay.addWidget(QLabel("勿扰时段"))
        time_lay.addStretch()
        self.dnd_start = QLineEdit(config.get("dnd_start", "22:00"))
        self.dnd_start.setFixedWidth(70)
        self.dnd_start.setAlignment(Qt.AlignCenter)
        self.dnd_start.setToolTip("开始时间 (HH:MM)")
        time_lay.addWidget(self.dnd_start)
        time_lay.addWidget(QLabel("→"))
        self.dnd_end = QLineEdit(config.get("dnd_end", "08:00"))
        self.dnd_end.setFixedWidth(70)
        self.dnd_end.setAlignment(Qt.AlignCenter)
        self.dnd_end.setToolTip("结束时间 (HH:MM)")
        time_lay.addWidget(self.dnd_end)
        dnd_layout.addWidget(time_row)

        content_layout.addWidget(dnd_group)

        # ---- 其他设置分组 ----
        other_group = QGroupBox("⚙️ 其他设置")
        other_layout = QVBoxLayout(other_group)
        other_layout.setSpacing(8)

        # 提示音
        sound_row = QWidget()
        sound_row.setStyleSheet(row_style)
        sound_lay = QHBoxLayout(sound_row)
        sound_lay.setContentsMargins(0, 0, 0, 0)
        sound_lay.addWidget(QLabel("🔔 提示音"))
        sound_lay.addStretch()
        self.sound_switch = ToggleSwitch(config.get("sound", True))
        sound_lay.addWidget(self.sound_switch)
        other_layout.addWidget(sound_row)

        # 开机自启
        autostart_row = QWidget()
        autostart_row.setStyleSheet(row_style)
        autostart_lay = QHBoxLayout(autostart_row)
        autostart_lay.setContentsMargins(0, 0, 0, 0)
        autostart_lay.addWidget(QLabel("🚀 开机自启"))
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

        # 弹窗位置
        pos_row = QWidget()
        pos_row.setStyleSheet(row_style)
        pos_lay = QHBoxLayout(pos_row)
        pos_lay.setContentsMargins(0, 0, 0, 0)
        pos_lay.addWidget(QLabel("📍 弹窗位置"))
        pos_lay.addStretch()
        self.popup_pos_combo = QComboBox()
        self.popup_pos_combo.addItems(list(POPUP_POSITION_MAP.values()))
        pos_index_map = {k: i for i, k in enumerate(POPUP_POSITION_MAP.keys())}
        self.popup_pos_combo.setCurrentIndex(pos_index_map.get(config.get("popup_position", "center"), 0))
        self.popup_pos_combo.setStyleSheet("""
            QComboBox {
                background: rgba(200,180,255,0.1); color: rgba(200,180,255,1);
                border: 1px solid rgba(200,180,255,0.2); border-radius: 8px;
                padding: 4px 8px; font-size: 13px; min-width: 70px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgba(30,30,50,240); color: rgba(200,180,255,1);
                selection-background-color: rgba(102,126,234,0.6);
            }
        """)
        pos_lay.addWidget(self.popup_pos_combo)
        other_layout.addWidget(pos_row)

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
        footer_label = QLabel("Bhands  V2.0")
        footer_label.setAlignment(Qt.AlignCenter)
        footer_label.setStyleSheet("font-size: 12px; color: rgba(200,180,255,0.7); border: none;")
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
        r, g, b = color[0], color[1], color[2]
        label.setStyleSheet(
            f"background: rgb({r},{g},{b}); border: 2px solid rgba(200,180,255,0.3); border-radius: 4px;")

    def _pick_gradient_color(self, which):
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
        self._grad_start_color = None
        self._grad_end_color = None
        theme = self.config.get("theme", "light")
        self._update_color_preview(self._grad_start_preview, list(THEME_PRESETS[theme]["primary"]))
        self._update_color_preview(self._grad_end_preview, list(THEME_PRESETS[theme]["secondary"]))

    def _rebuild_custom_rows(self):
        for container in self.custom_containers:
            container.setParent(None)
            container.deleteLater()
        self.custom_checks.clear()
        self.custom_spins.clear()
        self.custom_btn_widgets.clear()
        self.custom_containers.clear()

        row_style = _row_style()

        for i, item in enumerate(self.custom_items):
            row = QWidget()
            row.setStyleSheet(row_style)
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)

            row_lay.addWidget(QLabel(f"{item['icon']} {item['name']}"))
            row_lay.addStretch()
            switch = ToggleSwitch(item.get("enabled", True))
            self.custom_checks.append(switch)
            row_lay.addWidget(switch)
            spin = QSpinBox()
            spin.setRange(1, 480)
            spin.setValue(item.get("interval", 30))
            spin.setSuffix(" 分钟")
            spin.editingFinished.connect(self._auto_save)
            self.custom_spins.append(spin)
            row_lay.addWidget(spin)
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(35, 35)
            edit_btn.setObjectName("editBtn")
            edit_btn.setToolTip("编辑")
            edit_btn.clicked.connect(lambda _, x=i: self._edit_custom(x))
            row_lay.addWidget(edit_btn)
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(35, 35)
            del_btn.setObjectName("delBtn")
            del_btn.setToolTip("删除")
            del_btn.clicked.connect(lambda _, x=i: self._del_custom(x))
            row_lay.addWidget(del_btn)

            self.custom_btn_widgets.append(row)
            self.custom_containers.append(row)
            self.builtin_layout.addWidget(row)

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
            self.custom_items[idx] = dialog.get_data()
            self._rebuild_custom_rows()

    def _del_custom(self, idx):
        if idx < 0 or idx >= len(self.custom_items):
            return
        item = self.custom_items[idx]
        icon = item.get("icon", "?")
        name = item.get("name", "")

        dlg = QDialog(self)
        dlg.setWindowTitle("确认删除")
        dlg.setFixedSize(360, 180)
        dlg.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(20,20,40,245), stop:1 rgba(40,20,60,245));
                border: 1px solid rgba(200,180,255,0.2);
                border-radius: 12px;
            }
        """)
        lay = QVBoxLayout(dlg)
        lay.setSpacing(16)
        lay.setContentsMargins(30, 24, 30, 20)

        icon_lbl = QLabel(icon)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 42px; background: transparent; border: none;")
        lay.addWidget(icon_lbl)

        # Set window title bar icon to match the reminder icon
        from PyQt5.QtGui import QPixmap, QIcon, QPainter
        from PyQt5.QtCore import Qt as _Qt
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = painter.font()
        font.setPixelSize(48)
        painter.setFont(font)
        painter.drawText(pix.rect(), _Qt.AlignCenter, icon)
        painter.end()
        dlg.setWindowIcon(QIcon(pix))

        msg = QLabel(f"\u786e\u5b9a\u8981\u5220\u9664\u63d0\u9192 \"{name}\" \u5417\uff1f")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: rgba(200,180,255,0.9); font-size: 14px; background: transparent; border: none;")
        lay.addWidget(msg)

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(16)
        btn_lay.addStretch()

        yes_btn = QPushButton("确定")
        yes_btn.setFixedSize(100, 36)
        yes_btn.setStyleSheet("""
            QPushButton {
                background: rgba(102,126,234,0.5); color: white; border: none;
                border-radius: 8px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background: rgba(102,126,234,0.7); }
        """)
        yes_btn.clicked.connect(dlg.accept)
        btn_lay.addWidget(yes_btn)

        no_btn = QPushButton("取消")
        no_btn.setFixedSize(100, 36)
        no_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,180,255,0.1); color: rgba(200,180,255,0.8); border: none;
                border-radius: 8px; font-size: 14px;
            }
            QPushButton:hover { background: rgba(200,180,255,0.2); }
        """)
        no_btn.clicked.connect(dlg.reject)
        btn_lay.addWidget(no_btn)
        btn_lay.addStretch()

        lay.addLayout(btn_lay)

        if dlg.exec_() == QDialog.Accepted:
            self.custom_items.pop(idx)
            self._rebuild_custom_rows()

    def _auto_save(self):
        """自动保存（编辑完成时）"""
        self._collect_config()
        save_config(self.config)

    def _collect_config(self):
        """收集当前 UI 状态到 config"""
        self.config["eye_care"]["enabled"] = self.eye_switch.isChecked()
        self.config["eye_care"]["interval"] = self.eye_spin.value()
        self.config["rest"]["enabled"] = self.rest_switch.isChecked()
        self.config["rest"]["interval"] = self.rest_spin.value()
        self.config["water"]["enabled"] = self.water_switch.isChecked()
        self.config["water"]["interval"] = self.water_spin.value()
        self.config["sound"] = self.sound_switch.isChecked()
        self.config["auto_start"] = self.autostart_switch.isChecked()
        self.config["dnd_enabled"] = self.dnd_switch.isChecked()
        self.config["dnd_start"] = self.dnd_start.text().strip()
        self.config["dnd_end"] = self.dnd_end.text().strip()
        self.config["gradient_start"] = self._grad_start_color
        self.config["gradient_end"] = self._grad_end_color
        pos_keys = list(POPUP_POSITION_MAP.keys())
        self.config["popup_position"] = pos_keys[self.popup_pos_combo.currentIndex()]

        # 自定义提醒
        for i, item in enumerate(self.custom_items):
            if i < len(self.custom_checks):
                item["enabled"] = self.custom_checks[i].isChecked()
            if i < len(self.custom_spins):
                item["interval"] = self.custom_spins[i].value()
        self.config["custom"] = self.custom_items

    def save(self):
        self._collect_config()
        apply_theme(self.config.get("theme", "light"))
        apply_gradient_colors(self.config)
        set_autostart(self.config.get("auto_start", False))
        save_config(self.config)
        self.accept()







