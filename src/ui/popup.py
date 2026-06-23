# -*- coding: utf-8 -*-
"""提醒弹窗：渐变背景、自动关闭、贪睡功能"""

import logging

from PyQt5.QtWidgets import QWidget, QPushButton, QApplication, QDesktopWidget
from PyQt5.QtCore import Qt, QTimer, QRect, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QFont, QLinearGradient, QBrush

from constants import FONT_EMOJI, FONT_UI

logger = logging.getLogger(__name__)


class ReminderPopup(QWidget):
    """提醒弹窗"""
    snooze_signal = pyqtSignal(str, int)  # key, minutes

    def __init__(self, message, color, key="custom", interval=30, position="center", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 160)

        # 定位（添加偏移量避免重叠）
        screen = QApplication.primaryScreen().geometry()
        margin = 20
        w, h = self.width(), self.height()
        
        # 使用类变量跟踪弹窗数量，添加偏移量
        if not hasattr(ReminderPopup, '_popup_count'):
            ReminderPopup._popup_count = 0
        ReminderPopup._popup_count += 1
        offset = (ReminderPopup._popup_count - 1) * 30  # 每个弹窗偏移30像素
        
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
        """创建贪睡和关闭按钮"""
        # 间隔小于 5 分钟时隐藏贪睡按钮
        if self.interval < 5:
            self.snooze_btn = None
            return
        # 贪睡按钮 - 放在底部
        self.snooze_btn = QPushButton("💤 延迟 5 分钟", self)
        self.snooze_btn.setGeometry(self.width() - 180, self.height() - 40, 120, 32)
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

        # 关闭按钮 - 放在底部
        self.close_btn = QPushButton("✓ 知道了", self)
        self.close_btn.setGeometry(self.width() - 310, self.height() - 40, 100, 32)
        self.close_btn.setStyleSheet("""
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
        self.close_btn.clicked.connect(self.acknowledge)

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
        painter.setFont(QFont(FONT_EMOJI, 45))
        icon = self.message[0] if len(self.message) > 0 else "🔔"
        painter.drawText(25, 40, 70, 70, Qt.AlignCenter, icon)

        # 提醒文字
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont(FONT_UI, 14, QFont.Bold))
        text = self.message[2:] if len(self.message) > 2 else self.message
        painter.drawText(105, 25, self.width() - 130, 70, Qt.AlignLeft | Qt.AlignVCenter | Qt.TextWordWrap, text)

        # 底部进度条
        progress = min(1.0, self.elapsed_time / self.total_time)
        bar_y = self.height() - 12
        bar_width = self.width() - 30
        painter.setBrush(QColor(255, 255, 255, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(15, bar_y, bar_width, 4, 2, 2)
        painter.setBrush(QColor(255, 255, 255, 150))
        painter.drawRoundedRect(15, bar_y, int(bar_width * progress), 4, 2, 2)

        painter.end()
