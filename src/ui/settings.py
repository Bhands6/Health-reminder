# -*- coding: utf-8 -*-
"""设置面板：SettingsDialog（设计稿深色卡片风）+ CustomReminderDialog

视觉规格来源：健康提醒助手 · 移动端设计稿（Ardot）
- 窗口底：深紫→深蓝青四段渐变；分组标题在卡片外（灰字小号）
- 每行独立圆角卡：彩色图标方块 + 标题 + 尾部控件（Stepper 胶囊 / ToggleSwitch）
- 底部「取消（次级）+ 保存（紫→青渐变主按钮）」等宽并排
- 不依赖 Windows 亚克力/DWM（此前两轮玻璃化翻车主因），纯 QSS 实现
"""

import copy
import logging

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QPushButton, QLineEdit, QScrollArea,
    QColorDialog, QComboBox, QMessageBox, QWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QPixmap, QIcon, QPainter

from constants import (
    THEME, THEME_PRESETS, BUILTIN_REMINDERS, CUSTOM_COLORS,
    ICON_CHOICES, ICON_NAMES, FONT_UI, FONT_EMOJI, CHECK_ICON,
    ARROW_UP_ICON, ARROW_DOWN_ICON, POPUP_POSITION_MAP,
)
from utils import save_config, set_autostart
from constants import apply_theme, apply_gradient_colors
from ui.widgets import ToggleSwitch, Stepper

logger = logging.getLogger(__name__)

# ==================== 设计稿强调色 ====================

_ACCENT_PURPLE = (139, 92, 246)   # 护眼 / 主强调
_ACCENT_TEAL = (45, 212, 191)     # 喝水 / 副强调
_ACCENT_GRAY = (148, 163, 184)    # 关闭态行的中性强调

# ==================== 样式定义 ====================

_DIALOG_COLORS = {
    "light": {
        "text": "rgba(62,54,110,0.85)", "text_full": "#2F2A56",
        "row_bg": "rgba(255,255,255,0.72)", "row_bg_h": "rgba(255,255,255,0.95)",
        "row_border": "rgba(80,70,150,0.10)",
        "host_bg": "rgba(80,70,150,0.13)", "host_btn_h": "rgba(80,70,150,0.22)",
        "stepper_text": "#2F2A56",
        "grp_title": "rgba(62,54,110,0.55)",
        "input_bg": "rgba(255,255,255,0.80)", "input_border": "rgba(80,70,150,0.15)",
        "input_border_h": "rgba(80,70,150,0.35)",
        "combo_popup_bg": "rgba(255,255,255,252)", "combo_popup_text": "#2F2A56",
        "cancel_bg": "rgba(80,70,150,0.08)", "cancel_bg_h": "rgba(80,70,150,0.16)",
        "scroll_bg": "rgba(80,70,150,0.06)", "scroll_h": "rgba(80,70,150,0.18)",
        "scroll_hh": "rgba(80,70,150,0.32)",
        "tooltip_bg": "rgba(250,249,255,245)", "tooltip_border": "rgba(80,70,150,0.25)",
        "tooltip_text": "#2F2A56",
    },
    "dark": {
        "text": "rgba(226,222,245,0.85)", "text_full": "#EFEDFB",
        "row_bg": "rgba(255,255,255,0.085)", "row_bg_h": "rgba(255,255,255,0.13)",
        "row_border": "rgba(255,255,255,0.07)",
        "host_bg": "rgba(255,255,255,0.12)", "host_btn_h": "rgba(255,255,255,0.16)",
        "stepper_text": "#EFEDFB",
        "grp_title": "rgba(226,222,245,0.42)",
        "input_bg": "rgba(255,255,255,0.07)", "input_border": "rgba(255,255,255,0.08)",
        "input_border_h": "rgba(255,255,255,0.22)",
        "combo_popup_bg": "rgba(30,28,58,248)", "combo_popup_text": "#EFEDFB",
        "cancel_bg": "rgba(255,255,255,0.08)", "cancel_bg_h": "rgba(255,255,255,0.16)",
        "scroll_bg": "rgba(255,255,255,0.03)", "scroll_h": "rgba(255,255,255,0.12)",
        "scroll_hh": "rgba(255,255,255,0.22)",
        "tooltip_bg": "rgba(24,22,48,242)", "tooltip_border": "rgba(226,222,245,0.18)",
        "tooltip_text": "#EFEDFB",
    },
}


def _icon_tint(theme_name, rgb, alpha):
    """行图标方块的内联底色（构建时定格，与旧行为一致）"""
    r, g, b = rgb
    return f"rgba({r},{g},{b},{alpha})"


def _build_dialog_style(theme_name, check_path, arrow_up_path, arrow_down_path):
    c = _DIALOG_COLORS.get(theme_name, _DIALOG_COLORS["dark"])
    # 背景恢复原版联动：跟随用户的渐变颜色（THEME primary/secondary）暗化生成——
    # 「渐变颜色」调节的正是这里（保存/主题切换后生效）
    p = THEME.get("primary", (102, 126, 234))
    s = THEME.get("secondary", (118, 75, 162))

    def _dim(v, factor=0.35):
        return max(10, int(v * factor))

    bg_grad = (f"stop:0 rgb({_dim(p[0])},{_dim(p[1])},{_dim(p[2])}), "
               f"stop:0.4 rgb({_dim(p[0], 0.45)},{_dim(p[1], 0.45)},{_dim(p[2], 0.45)}), "
               f"stop:0.7 rgb({_dim(p[0])},{_dim(p[1])},{_dim(p[2])}), "
               f"stop:1 rgb({_dim(s[0])},{_dim(s[1])},{_dim(s[2])})")
    return """
        QDialog { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, %(bg)s); }
        QLabel { color: %(text)s; font-size: 13px; background: transparent; }

        /* ---- 行卡：彩色图标方块 + 标题 + 尾部控件 ---- */
        QWidget#settingRow {
            background: %(row_bg)s;
            border: 1px solid %(row_border)s;
            border-radius: 14px;
        }
        QWidget#settingRow:hover { background: %(row_bg_h)s; }
        QWidget#settingRow QLabel { border: none; }

        /* ---- 水平步进器：「− 值 单位 +」胶囊 ---- */
        QWidget#stepperHost {
            background: %(host_bg)s; border: none; border-radius: 15px;
        }
        QPushButton#stepperBtn {
            background: transparent; color: %(stepper_text)s;
            border: none; border-radius: 12px;
            font-size: 15px; font-weight: bold; padding: 0;
        }
        QPushButton#stepperBtn:hover { background: %(host_btn_h)s; }
        QPushButton#stepperBtn:pressed { background: %(host_btn_h)s; }
        QLabel#stepperValue {
            color: %(stepper_text)s; font-size: 13px;
            background: transparent; border: none;
        }

        /* ---- 分组标题（卡片外灰字）---- */
        QLabel#groupTitle {
            color: %(grp_title)s; font-size: 12px; font-weight: bold;
            background: transparent; border: none; padding: 0;
        }
        QLabel#dialogTitle {
            color: %(text_full)s; font-size: 22px; font-weight: bold;
            background: transparent; border: none; padding: 0;
        }
        QLabel#dialogSubtitle {
            color: %(grp_title)s; font-size: 12px;
            background: transparent; border: none; padding: 0;
        }
        QLabel#footerLabel {
            color: %(grp_title)s; font-size: 12px;
            background: transparent; border: none;
        }

        /* ---- 底部按钮：取消（次级）/ 保存（渐变主按钮）---- */
        QPushButton#saveBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #8B5CF6, stop:1 #2DD4BF);
            color: #FFFFFF; border: none; border-radius: 21px;
            padding: 12px 18px; font-size: 14px; font-weight: bold;
        }
        QPushButton#saveBtn:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #9D70F8, stop:1 #3EDCCA);
        }
        QPushButton#saveBtn:pressed {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #7A4CE0, stop:1 #26BFAA);
        }
        QPushButton#cancelBtn {
            background: %(cancel_bg)s; color: %(text_full)s;
            border: none; border-radius: 21px;
            padding: 12px 18px; font-size: 14px;
        }
        QPushButton#cancelBtn:hover { background: %(cancel_bg_h)s; }

        /* ---- 添加自定义提醒（整行虚线感按钮）---- */
        QPushButton#addBtn {
            background: %(host_bg)s; color: %(text_full)s;
            border: 1px dashed %(input_border_h)s; border-radius: 14px;
            padding: 12px 16px; font-size: 13px;
        }
        QPushButton#addBtn:hover { background: %(host_btn_h)s; }

        /* ---- 重置 / 编辑 / 删除 ---- */
        QPushButton#resetBtn {
            background: %(host_bg)s; color: %(text)s;
            border: none; border-radius: 8px;
            font-size: 11px; padding: 0;
        }
        QPushButton#resetBtn:hover { background: %(host_btn_h)s; color: %(text_full)s; }
        QPushButton#editBtn {
            background: %(host_bg)s; color: %(stepper_text)s;
            border: none; border-radius: 10px; padding: 0; font-size: 15px;
        }
        QPushButton#editBtn:hover { background: %(host_btn_h)s; }
        QPushButton#delBtn {
            background: rgba(244,67,54,0.12); color: rgba(244,67,54,0.9);
            border: none; border-radius: 10px; padding: 0; font-size: 14px;
        }
        QPushButton#delBtn:hover { background: rgba(244,67,54,0.32); color: #FFFFFF; }

        /* ---- 输入类 ---- */
        QLineEdit {
            background: %(input_bg)s; color: %(text_full)s;
            border: 1px solid %(input_border)s; border-radius: 9px;
            padding: 6px; font-size: 13px;
        }
        QLineEdit:focus { border: 1px solid %(input_border_h)s; }
        QSpinBox {
            background: %(input_bg)s; color: %(text_full)s;
            border: 1px solid %(input_border)s; border-radius: 9px;
            padding: 6px; padding-right: 22px; font-size: 13px; min-width: 85px;
        }
        QSpinBox:hover { border: 1px solid %(input_border_h)s; }
        QSpinBox::up-button, QSpinBox::down-button {
            background: %(host_bg)s; border: none; border-radius: 3px;
        }
        QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: %(host_btn_h)s; }
        QSpinBox::up-arrow { image: url(%(arrow_up)s); width: 14px; height: 14px; }
        QSpinBox::down-arrow { image: url(%(arrow_down)s); width: 14px; height: 14px; }
        QComboBox {
            background: %(input_bg)s; color: %(text_full)s;
            border: 1px solid %(input_border)s; border-radius: 9px;
            padding: 5px 10px; font-size: 13px; min-width: 70px;
        }
        QComboBox:hover { border: 1px solid %(input_border_h)s; }
        QComboBox::drop-down { border: none; width: 22px; }
        QComboBox QAbstractItemView {
            background: %(combo_popup_bg)s; color: %(combo_popup_text)s;
            selection-background-color: %(host_btn_h)s;
            border: 1px solid %(input_border)s;
            font-size: 13px; padding: 4px;
        }

        QScrollArea { border: none; background: transparent; }
        QScrollBar:vertical { background: %(scroll_bg)s; width: 8px; border-radius: 4px; }
        QScrollBar::handle:vertical {
            background: %(scroll_h)s; border-radius: 4px; min-height: 30px;
        }
        QScrollBar::handle:vertical:hover { background: %(scroll_hh)s; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        QToolTip {
            background: %(tooltip_bg)s; color: %(tooltip_text)s;
            border: 1px solid %(tooltip_border)s; border-radius: 6px;
            padding: 5px 10px; font-size: 12px;
        }
    """ % {
        **c,
        "bg": bg_grad,
        "check": check_path,
        "arrow_up": arrow_up_path,
        "arrow_down": arrow_down_path,
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
        ok_btn.setObjectName("saveBtn")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

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
    """设置面板 - 设计稿深色卡片风"""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(400, 500)
        self.resize(500, 830)
        # 深拷贝，保证「取消」时外部配置与全局主题都不受影响
        self.config = copy.deepcopy(config)
        self.custom_items = [dict(item) for item in config.get("custom", [])]
        # 记录打开面板时的主题状态，供 reject 回滚
        self._origin_theme = config.get("theme", "light")
        self._origin_gradient = (
            config.get("gradient_start"), config.get("gradient_end")
        )

        self._check_path = CHECK_ICON.replace("\\", "/")
        self._arrow_up_path = ARROW_UP_ICON.replace("\\", "/")
        self._arrow_down_path = ARROW_DOWN_ICON.replace("\\", "/")

        self._apply_style()

        theme = self.config.get("theme", "light")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 14, 18, 14)
        main_layout.setSpacing(10)

        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setAttribute(Qt.WA_TranslucentBackground, True)
        main_scroll.setStyleSheet("background: transparent;")

        content_widget = QWidget()
        content_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        main_scroll.setWidget(content_widget)

        # ---- 标题区（左对齐，设计稿样式）----
        title_label = QLabel("健康提醒助手")
        title_label.setObjectName("dialogTitle")
        subtitle_label = QLabel("关爱健康，从每次提醒开始")
        subtitle_label.setObjectName("dialogSubtitle")
        content_layout.addWidget(title_label)
        content_layout.addWidget(subtitle_label)
        content_layout.addSpacing(4)

        # ---- 内置提醒分组 ----
        builtin_box, builtin_layout = self._make_group("☑", "内置提醒", theme)
        content_layout.addWidget(builtin_box)

        # 护眼（紫）——尾部顺序：Stepper 在左、开关最右（设计稿）
        eye_row, eye_lay = self._make_row(
            "👁", _icon_tint(theme, _ACCENT_PURPLE, 0.28), "护眼提醒")
        self.eye_spin = Stepper(config["eye_care"]["interval"], 1, 480)
        self.eye_spin.editingFinished.connect(self._auto_save)
        eye_lay.addWidget(self.eye_spin)
        self.eye_switch = ToggleSwitch(config["eye_care"]["enabled"], accent=_ACCENT_PURPLE)
        eye_lay.addWidget(self.eye_switch)
        builtin_layout.addWidget(eye_row)

        # 休息（中性灰紫）
        rest_row, rest_lay = self._make_row(
            "🧘", _icon_tint(theme, _ACCENT_GRAY, 0.16), "休息提醒")
        self.rest_spin = Stepper(config["rest"]["interval"], 1, 480)
        self.rest_spin.editingFinished.connect(self._auto_save)
        rest_lay.addWidget(self.rest_spin)
        self.rest_switch = ToggleSwitch(config["rest"]["enabled"], accent=_ACCENT_TEAL)
        rest_lay.addWidget(self.rest_switch)
        builtin_layout.addWidget(rest_row)

        # 喝水（青绿高亮）
        water_row, water_lay = self._make_row(
            "💧", _icon_tint(theme, _ACCENT_TEAL, 0.22), "喝水提醒")
        self.water_spin = Stepper(config["water"]["interval"], 1, 480)
        self.water_spin.editingFinished.connect(self._auto_save)
        water_lay.addWidget(self.water_spin)
        self.water_switch = ToggleSwitch(config["water"]["enabled"], accent=_ACCENT_TEAL)
        water_lay.addWidget(self.water_switch)
        builtin_layout.addWidget(water_row)

        # ---- 自定义提醒分组 ----
        custom_box, custom_group_layout = self._make_group("✦", "自定义提醒", theme)
        content_layout.addWidget(custom_box)

        # 提醒行放在独立容器中，重建时不会影响下方的「添加」按钮
        self.custom_rows_widget = QWidget()
        self.custom_rows_widget.setAttribute(Qt.WA_TranslucentBackground, True)
        self.custom_rows_widget.setStyleSheet("background: transparent;")
        self.custom_layout = QVBoxLayout(self.custom_rows_widget)
        self.custom_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_layout.setSpacing(8)
        custom_group_layout.addWidget(self.custom_rows_widget)

        self.custom_checks = []
        self.custom_spins = []
        self.custom_btn_widgets = []
        self.custom_containers = []
        self._rebuild_custom_rows()

        add_btn = QPushButton("＋  添加自定义提醒")
        add_btn.setObjectName("addBtn")
        add_btn.clicked.connect(self._add_custom)
        custom_group_layout.addWidget(add_btn)

        # ---- 勿扰模式分组 ----
        dnd_box, dnd_layout = self._make_group("☾", "勿扰模式", theme)
        content_layout.addWidget(dnd_box)

        dnd_row, dnd_lay = self._make_row(
            "🌙", _icon_tint(theme, _ACCENT_PURPLE, 0.24), "启用勿扰")
        self.dnd_switch = ToggleSwitch(config.get("dnd_enabled", False), accent=_ACCENT_PURPLE)
        dnd_lay.addWidget(self.dnd_switch)
        dnd_layout.addWidget(dnd_row)

        time_row, time_lay = self._make_row(
            "🕒", _icon_tint(theme, _ACCENT_GRAY, 0.14), "勿扰时段")
        self.dnd_start = QLineEdit(config.get("dnd_start", "22:00"))
        self.dnd_start.setFixedWidth(72)
        self.dnd_start.setAlignment(Qt.AlignCenter)
        self.dnd_start.setToolTip("开始时间 (HH:MM)")
        time_lay.addWidget(self.dnd_start)
        arrow_lbl = QLabel("→")
        arrow_lbl.setStyleSheet("background: transparent; border: none;")
        time_lay.addWidget(arrow_lbl)
        self.dnd_end = QLineEdit(config.get("dnd_end", "08:00"))
        self.dnd_end.setFixedWidth(72)
        self.dnd_end.setAlignment(Qt.AlignCenter)
        self.dnd_end.setToolTip("结束时间 (HH:MM)")
        time_lay.addWidget(self.dnd_end)
        dnd_layout.addWidget(time_row)

        # ---- 其他设置分组 ----
        other_box, other_layout = self._make_group("⚙", "其他设置", theme)
        content_layout.addWidget(other_box)

        # 提示音（紫）
        sound_row, sound_lay = self._make_row(
            "🔔", _icon_tint(theme, _ACCENT_PURPLE, 0.24), "提示音")
        self.sound_switch = ToggleSwitch(config.get("sound", True), accent=_ACCENT_PURPLE)
        sound_lay.addWidget(self.sound_switch)
        other_layout.addWidget(sound_row)

        # 开机自启（青）
        autostart_row, autostart_lay = self._make_row(
            "⏻", _icon_tint(theme, _ACCENT_TEAL, 0.20), "开机自启")
        self.autostart_switch = ToggleSwitch(config.get("auto_start", False), accent=_ACCENT_TEAL)
        autostart_lay.addWidget(self.autostart_switch)
        other_layout.addWidget(autostart_row)

        # 亮/暗色模式（青）
        theme_row, theme_lay = self._make_row(
            "◐", _icon_tint(theme, _ACCENT_TEAL, 0.20), "亮/暗色模式")
        self.theme_switch = ToggleSwitch(config.get("theme", "light") == "dark", accent=_ACCENT_TEAL)
        self.theme_switch.toggled.connect(self._on_theme_toggle)
        theme_lay.addWidget(self.theme_switch)
        other_layout.addWidget(theme_row)

        # 自定义渐变颜色
        self._grad_start_color = list(config.get("gradient_start")) if config.get("gradient_start") else None
        self._grad_end_color = list(config.get("gradient_end")) if config.get("gradient_end") else None

        grad_row, grad_lay = self._make_row(
            "🎨", _icon_tint(theme, _ACCENT_PURPLE, 0.24), "渐变颜色")

        self._grad_start_preview = QLabel()
        self._grad_start_preview.setFixedSize(24, 24)
        self._update_color_preview(self._grad_start_preview, self._grad_start_color or list(THEME_PRESETS[config.get("theme", "light")]["primary"]))
        self._grad_start_preview.setCursor(Qt.PointingHandCursor)
        self._grad_start_preview.mousePressEvent = lambda _: self._pick_gradient_color("start")
        grad_lay.addWidget(self._grad_start_preview)

        grad_arrow = QLabel("→")
        grad_arrow.setStyleSheet("background: transparent; border: none;")
        grad_lay.addWidget(grad_arrow)

        self._grad_end_preview = QLabel()
        self._grad_end_preview.setFixedSize(24, 24)
        self._update_color_preview(self._grad_end_preview, self._grad_end_color or list(THEME_PRESETS[config.get("theme", "light")]["secondary"]))
        self._grad_end_preview.setCursor(Qt.PointingHandCursor)
        self._grad_end_preview.mousePressEvent = lambda _: self._pick_gradient_color("end")
        grad_lay.addWidget(self._grad_end_preview)

        grad_lay.addStretch()
        reset_btn = QPushButton("重置")
        reset_btn.setObjectName("resetBtn")
        reset_btn.setFixedSize(52, 28)
        reset_btn.setToolTip("恢复主题默认颜色")
        reset_btn.clicked.connect(self._reset_gradient_colors)
        grad_lay.addWidget(reset_btn)

        other_layout.addWidget(grad_row)

        # 弹窗位置
        pos_row, pos_lay = self._make_row(
            "📍", _icon_tint(theme, _ACCENT_PURPLE, 0.24), "弹窗位置")
        self.popup_pos_combo = QComboBox()
        self.popup_pos_combo.addItems(list(POPUP_POSITION_MAP.values()))
        pos_index_map = {k: i for i, k in enumerate(POPUP_POSITION_MAP.keys())}
        self.popup_pos_combo.setCurrentIndex(pos_index_map.get(config.get("popup_position", "center"), 0))
        pos_lay.addWidget(self.popup_pos_combo)
        other_layout.addWidget(pos_row)

        main_layout.addWidget(main_scroll)

        # 底部按钮：取消（左，次级）/ 保存（右，渐变主按钮），等宽
        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("保存")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save)
        bottom.addWidget(cancel_btn, 1)
        bottom.addWidget(save_btn, 1)
        main_layout.addLayout(bottom)

        # 作者和版本号
        footer_label = QLabel("Bhands · V3.0")
        footer_label.setObjectName("footerLabel")
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)

        # 回车保存但不退出
        self.eye_spin.editingFinished.connect(self._auto_save)
        self.rest_spin.editingFinished.connect(self._auto_save)
        self.water_spin.editingFinished.connect(self._auto_save)

    # ---- 布局 helper ----

    def _make_group(self, icon, text, theme):
        """分组 = 卡片外灰字标题 + 竖排容器（设计稿样式）"""
        box = QWidget()
        box.setAttribute(Qt.WA_TranslucentBackground, True)
        box.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(2, 0, 2, 0)
        lay.setSpacing(8)
        lbl = QLabel(f"{icon}  {text}")
        lbl.setObjectName("groupTitle")
        lay.addWidget(lbl)
        return box, lay

    def _make_row(self, icon, tint, title):
        """行卡 = 彩色图标方块 + 标题 +（调用方追加尾部控件）"""
        row = QWidget()
        row.setObjectName("settingRow")
        row.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 8, 12, 8)
        lay.setSpacing(12)
        icon_lbl = QLabel(icon)
        icon_lbl.setFixedSize(34, 34)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background: {tint}; border: none; border-radius: 10px; font-size: 18px;")
        lay.addWidget(icon_lbl)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(title_lbl)
        lay.addStretch()
        return row, lay

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._auto_save()
            return
        super().keyPressEvent(event)

    def _apply_style(self):
        # 设置面板固定用设计稿深色卡片风（不随全局主题切换）——
        # 全局主题/渐变色只控制悬浮窗与提醒弹窗，互不影响
        self.setStyleSheet(_build_dialog_style(
            "dark", self._check_path, self._arrow_up_path, self._arrow_down_path))

    def _on_theme_toggle(self, checked):
        theme = "dark" if checked else "light"
        self.config["gradient_start"] = self._grad_start_color
        self.config["gradient_end"] = self._grad_end_color
        self.config["theme"] = theme
        apply_theme(theme)
        apply_gradient_colors(self.config)
        # 重刷面板：控件样式恒为设计稿深色卡片风（_apply_style 固定 dark 色板），
        # 但背景渐变跟随 THEME（用户渐变色暗化版）即时更新
        self._apply_style()
        parent = self.parent()
        if parent is not None and hasattr(parent, "config"):
            parent.config["theme"] = theme
            parent.update()

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

        theme = self.config.get("theme", "light")

        for i, item in enumerate(self.custom_items):
            tint = _icon_tint(theme, _ACCENT_PURPLE, 0.24)
            row, row_lay = self._make_row(item.get("icon", "☕"), tint, item.get("name", ""))

            spin = Stepper(item.get("interval", 30), 1, 480)
            spin.editingFinished.connect(self._auto_save)
            self.custom_spins.append(spin)
            row_lay.addWidget(spin)

            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(34, 34)
            edit_btn.setObjectName("editBtn")
            edit_btn.setToolTip("编辑")
            edit_btn.clicked.connect(lambda _, x=i: self._edit_custom(x))
            row_lay.addWidget(edit_btn)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(34, 34)
            del_btn.setObjectName("delBtn")
            del_btn.setToolTip("删除")
            del_btn.clicked.connect(lambda _, x=i: self._del_custom(x))
            row_lay.addWidget(del_btn)

            switch = ToggleSwitch(item.get("enabled", True), accent=_ACCENT_TEAL)
            self.custom_checks.append(switch)
            row_lay.addWidget(switch)

            self.custom_btn_widgets.append(row)
            self.custom_containers.append(row)
            self.custom_layout.addWidget(row)

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
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.TextAntialiasing)
        font = painter.font()
        font.setPixelSize(48)
        painter.setFont(font)
        painter.drawText(pix.rect(), Qt.AlignCenter, icon)
        painter.end()
        dlg.setWindowIcon(QIcon(pix))

        msg = QLabel(f"确定要删除提醒 \"{name}\" 吗？")
        msg.setAlignment(Qt.AlignCenter)
        msg.setStyleSheet("color: rgba(226,222,245,0.9); font-size: 14px; background: transparent; border: none;")
        lay.addWidget(msg)

        btn_lay = QHBoxLayout()
        btn_lay.setSpacing(16)
        btn_lay.addStretch()

        yes_btn = QPushButton("确定")
        yes_btn.setFixedSize(100, 36)
        yes_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8B5CF6, stop:1 #2DD4BF);
                color: white; border: none;
                border-radius: 18px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #9D70F8, stop:1 #3EDCCA);
            }
        """)
        yes_btn.clicked.connect(dlg.accept)
        btn_lay.addWidget(yes_btn)

        no_btn = QPushButton("取消")
        no_btn.setFixedSize(100, 36)
        no_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,0.08); color: rgba(226,222,245,0.85); border: none;
                border-radius: 18px; font-size: 14px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.16); }
        """)
        no_btn.clicked.connect(dlg.reject)
        btn_lay.addWidget(no_btn)
        btn_lay.addStretch()

        lay.addLayout(btn_lay)

        if dlg.exec_() == QDialog.Accepted:
            self.custom_items.pop(idx)
            self._rebuild_custom_rows()

    def _auto_save(self):
        """编辑完成时把当前 UI 值收进对话框内部状态

        刻意不落盘：写文件统一交给「保存」按钮，
        否则改了输入框再点「取消」，改动其实已经写进磁盘了。
        """
        self._collect_config()

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

    def reject(self):
        """取消：丢弃未保存的改动，并把主题与渐变还原到打开面板时的状态"""
        apply_theme(self._origin_theme)
        apply_gradient_colors({
            "gradient_start": self._origin_gradient[0],
            "gradient_end": self._origin_gradient[1],
        })
        parent = self.parent()
        if parent is not None and hasattr(parent, "config"):
            parent.config["theme"] = self._origin_theme
            parent.update()
        super().reject()
