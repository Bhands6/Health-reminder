# -*- coding: utf-8 -*-
"""提醒弹窗：渐变背景、自动关闭、贪睡功能"""

import logging

from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QRect, QRectF, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QFont, QLinearGradient, QBrush, QPen

from constants import FONT_EMOJI, FONT_UI
# 弹窗按钮不用 PillButton（半透明 Tool 窗口上自绘会 native crash，见 _create_buttons 注释）

logger = logging.getLogger(__name__)


class ReminderPopup(QWidget):
    """提醒弹窗"""
    snooze_signal = pyqtSignal(str, int)  # key, minutes

    # 当前存活的弹窗数量（关闭时递减，避免偏移无限累积）
    _popup_count = 0
    # 最大堆叠层数，超出后回到起点重新排列
    _MAX_STACK = 6

    def __init__(self, message, color, key="custom", interval=30, position="center", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 172)

        # 定位（添加偏移量避免重叠）
        screen = QApplication.primaryScreen().geometry()
        margin = 20
        w, h = self.width(), self.height()
        
        # 按当前存活弹窗数计算偏移，堆叠层数封顶后回绕，避免超出屏幕
        ReminderPopup._popup_count += 1
        stack = (ReminderPopup._popup_count - 1) % ReminderPopup._MAX_STACK
        offset = stack * 30  # 每个弹窗偏移30像素
        
        pos_map = {
            "center": ((screen.width() - w) // 2 + offset, (screen.height() - h) // 2 + offset),
            "top_left": (margin + offset, margin + offset),
            "top_right": (screen.width() - w - margin - offset, margin + offset),
            "bottom_left": (margin + offset, screen.height() - h - margin - offset),
            "bottom_right": (screen.width() - w - margin - offset, screen.height() - h - margin - offset),
            "top_center": ((screen.width() - w) // 2 + offset, margin + offset),
            "bottom_center": ((screen.width() - w) // 2 + offset, screen.height() - h - margin - offset),
        }
        x, y = pos_map.get(position, pos_map["center"])
        self.move(x, y)

        self.message = message
        self.color = color
        self.key = key
        self.interval = interval
        self.opacity_val = 0.0
        self.total_time = 5000  # 5 秒自动关闭
        self.elapsed_time = 0
        self.is_snoozed = False
        self._count_released = False  # 防止 closeEvent 重复递减计数

        # 渐变动画
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_step)
        self.fade_timer.start(16)

        # 自动关闭计时器
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.update_progress)
        self.close_timer.start(16)

        # 5 秒后自动关闭
        self.auto_close_timer = QTimer(self)
        self.auto_close_timer.setSingleShot(True)
        self.auto_close_timer.timeout.connect(self.fade_out)
        self.auto_close_timer.start(self.total_time)

        self.fading_in = True
        self.fading_out = False

        # 创建按钮
        self._create_buttons()

    def _create_buttons(self):
        """创建贪睡和关闭按钮（QSS 玻璃质感胶囊，底部右对齐）

        「知道了」始终创建 —— 否则用户无法确认提醒，completed 统计也永远记不到。
        间隔小于 5 分钟时贪睡（延迟 5 分钟）没有意义，只隐藏贪睡按钮。

        ⚠️ 弹窗按钮必须用 QPushButton + QSS（带 1px 实色边框保证圆角生效），
        不能用 PillButton——PillButton 在半透明 Tool 窗口上绘制会 native crash
        （设置面板 QDialog 上正常，仅弹窗上下文崩，真机实测）。
        """
        glass_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,52), stop:1 rgba(255,255,255,16));
                color: #F5F3FC;
                border: 1px solid rgba(255,255,255,88);
                border-radius: 17px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,72), stop:1 rgba(255,255,255,30));
                border: 1px solid rgba(255,255,255,120);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,40), stop:1 rgba(255,255,255,12));
            }
        """
        tint_style = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(150,110,250,190), stop:1 rgba(45,212,191,150));
                color: #FFFFFF;
                border: 1px solid rgba(255,255,255,100);
                border-radius: 17px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(160,125,255,215), stop:1 rgba(60,220,200,180));
                border: 1px solid rgba(255,255,255,130);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(130,90,235,200), stop:1 rgba(35,190,170,160));
            }
        """
        btn_y = 84
        # 知道了：彩色玻璃主按钮，右对齐
        self.close_btn = QPushButton("✓  知道了", self)
        self.close_btn.setGeometry(self.width() - 20 - 106, btn_y, 106, 34)
        self.close_btn.setStyleSheet(tint_style)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.clicked.connect(self.acknowledge)

        # 贪睡按钮（白色玻璃次级）
        if self.interval >= 5:
            self.snooze_btn = QPushButton("💤  延迟 5 分钟", self)
            self.snooze_btn.setGeometry(self.width() - 20 - 106 - 10 - 148, btn_y, 148, 34)
            self.snooze_btn.setStyleSheet(glass_style)
            self.snooze_btn.setCursor(Qt.PointingHandCursor)
            self.snooze_btn.clicked.connect(self.snooze)
        else:
            self.snooze_btn = None
            self.close_btn.move((self.width() - 106) // 2, btn_y)

    def acknowledge(self):
        """用户确认提醒（完成）"""
        from utils import record_stat
        record_stat(self.key, "completed")
        self.fade_out()

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

    def closeEvent(self, event):
        """关闭时释放弹窗计数，避免偏移量无限累积"""
        if not self._count_released:
            self._count_released = True
            ReminderPopup._popup_count = max(0, ReminderPopup._popup_count - 1)
        super().closeEvent(event)

    def update_progress(self):
        """更新进度"""
        self.elapsed_time += 16
        self.update()

    def paintEvent(self, event):
        """绘制弹窗：深色玻璃卡片 + 主题色点缀（左竖条/图标方块/进度条）"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # 阴影
        painter.setBrush(QColor(0, 0, 0, 70))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(6, 8, w - 4, h - 4, 22, 22)

        # 卡片底：深色玻璃渐变（与设置面板同视觉语言）+ 高光描边
        card = QRectF(0, 0, w - 8, h - 8)
        gradient = QLinearGradient(0, 0, 0, card.height())
        gradient.setColorAt(0, QColor(38, 33, 74))
        gradient.setColorAt(1, QColor(20, 24, 48))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 26), 1))
        painter.drawRoundedRect(card, 20, 20)

        accent = QColor(*self.color)

        # 左侧强调色竖条
        painter.setBrush(accent)
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 16, 4, int(card.height() - 32), 2, 2)

        # 图标方块（accent tint + emoji）
        painter.setBrush(QColor(self.color[0], self.color[1], self.color[2], 70))
        painter.drawRoundedRect(20, 18, 46, 46, 13, 13)
        painter.setPen(QColor(255, 255, 255, 235))
        painter.setFont(QFont(FONT_EMOJI, 22))
        icon = self.message[0] if len(self.message) > 0 else "🔔"
        painter.drawText(QRect(20, 18, 46, 46), Qt.AlignCenter, icon)

        # 提醒文字（白色粗体，两行内）
        painter.setPen(QColor(245, 243, 252))
        painter.setFont(QFont(FONT_UI, 14, QFont.Bold))
        text = self.message[2:] if len(self.message) > 2 else self.message
        painter.drawText(QRect(82, 14, w - 104, 54),
                         Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)

        # 底部进度条（轨道白 12% + accent 填充）
        progress = min(1.0, self.elapsed_time / self.total_time)
        bar_y = h - 26
        bar_width = w - 48
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(20, bar_y, bar_width, 4, 2, 2)
        painter.setBrush(accent)
        painter.drawRoundedRect(20, bar_y, int(bar_width * progress), 4, 2, 2)

        painter.end()
