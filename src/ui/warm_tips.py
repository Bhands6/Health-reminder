# -*- coding: utf-8 -*-
"""温馨提醒：点击悬浮球时显示大量随机温馨提醒"""

import random
from PyQt5.QtWidgets import QWidget, QLabel, QApplication, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QPoint, QRect
from PyQt5.QtGui import QColor, QPainter, QFont, QLinearGradient, QBrush

from constants import FONT_UI


class WarmTipWindow(QWidget):
    """单个温馨提醒窗口"""
    
    def __init__(self, tip, bg_color, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.tip = tip
        self.bg_color = bg_color
        self.opacity_val = 0.0
        self.fading_in = True
        self.fading_out = False
        
        # 窗口大小
        self.setFixedSize(250, 60)
        
        # 随机位置
        screen = QApplication.primaryScreen().geometry()
        x = random.randint(0, screen.width() - self.width())
        y = random.randint(0, screen.height() - self.height())
        self.move(x, y)
        
        # 淡入动画
        self.fade_timer = QTimer(self)
        self.fade_timer.timeout.connect(self.fade_step)
        self.fade_timer.start(16)
    
    def fade_step(self):
        """淡入淡出动画"""
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
    
    def start_fade_out(self):
        """开始淡出"""
        self.fading_out = True
    
    def paintEvent(self, event):
        """绘制窗口"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 解析背景颜色
        color = QColor(self.bg_color)
        
        # 渐变背景
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 230))
        gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 200))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 15, 15)
        
        # 提醒文字
        painter.setPen(QColor(80, 80, 80))
        painter.setFont(QFont(FONT_UI, 16))
        painter.drawText(self.rect(), Qt.AlignCenter, self.tip)
        
        painter.end()


class WarmTipController(QWidget):
    """温馨提醒控制窗口（合并控制和提示）"""
    
    def __init__(self, parent=None, heart_mode=False):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.heart_mode = heart_mode
        
        self.setFixedSize(400, 200)
        
        # 屏幕上方居中显示
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = 200  # 距离顶部200像素
        self.move(x, y)
        
        self.tips_window = []
        self.close_all = False
        self.current_index = 0
        self.total_windows = 100  # 默认值，可以从配置中读取
        
        self.tips = [
            '多喝水哦~', '保持微笑呀', '每天都要元气满满',
            '记得吃水果', '保持好心情', '好好爱自己', '我想你了',
            '梦想成真', '期待下一次见面', '金榜题名', '顺顺利利', '早点休息',
            '愿所有烦恼都消失', '别熬夜', '今天过得开心嘛', '天冷了,多穿衣服',
            '你是最棒的', '加油哦', '辛苦了', '休息一下吧'
        ]
        
        self.bg_colors = [
            'lightpink', 'skyblue', 'lightgreen', 'lavender',
            'lightyellow', 'aquamarine', 'mistyrose', 'honeydew',
            'lavenderblush', 'oldlace', 'plum', 'coral', 'bisque'
        ]
        
        # 定时器
        self.create_timer = QTimer(self)
        self.create_timer.timeout.connect(self.create_one_tip)
        
        self.close_timer = QTimer(self)
        self.close_timer.timeout.connect(self.close_next_window)
        
        self.keep_on_top_timer = QTimer(self)
        self.keep_on_top_timer.timeout.connect(self.keep_on_top)
        
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        pass
    
    def paintEvent(self, event):
        """自定义绘制，精确控制文本位置"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制背景
        painter.setBrush(QColor("lightpink"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        # 绘制标题 - 在上半部分居中
        painter.setPen(QColor("red"))
        painter.setFont(QFont(FONT_UI, 28, QFont.Bold))
        title_rect = QRect(0, 0, self.width(), self.height() // 2)
        painter.drawText(title_rect, Qt.AlignCenter, "~❤️万事顺意❤️~")
        
        # 绘制提示文字 - 在下半部分居中
        painter.setPen(QColor("gray"))
        painter.setFont(QFont(FONT_UI, 12))
        hint_rect = QRect(0, self.height() // 2, self.width(), self.height() // 2)
        painter.drawText(hint_rect, Qt.AlignCenter, "按空格键关闭所有窗口")
        
        painter.end()
    
    def _generate_heart_points(self, num_points, window_width, window_height):
        """生成心形坐标点"""
        import math
        screen = QApplication.primaryScreen().geometry()
        screen_w = screen.width()
        screen_h = screen.height()
        
        margin_x = max(20, window_width // 2)
        margin_y = max(20, window_height // 2)
        usable_w = max(1, screen_w - margin_x * 2 - window_width)
        usable_h = max(1, screen_h - margin_y * 2 - window_height)
        
        points = []
        for i in range(num_points):
            t = 2 * math.pi * i / num_points
            x0 = 16 * math.sin(t) ** 3
            y0 = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            points.append((x0, y0))
        
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(1e-6, max_x - min_x)
        span_y = max(1e-6, max_y - min_y)
        
        mapped_points = []
        seen_points = set()
        for x0, y0 in points:
            nx = (x0 - min_x) / span_x
            ny = (y0 - min_y) / span_y
            px = int(margin_x + nx * usable_w)
            py = int(margin_y + (1 - ny) * usable_h)
            px = max(0, min(px, screen_w - window_width))
            py = max(0, min(py, screen_h - window_height))
            if (px, py) not in seen_points:
                seen_points.add((px, py))
                mapped_points.append((px, py))
        
        return mapped_points
    
    def start(self):
        """开始显示温馨提醒"""
        self.show()
        self.raise_()
        self.activateWindow()
        
        # 如果是爱心模式，生成心形坐标
        if self.heart_mode:
            self._heart_points = self._generate_heart_points(
                self.total_windows, 250, 60
            )
            self.total_windows = len(self._heart_points)
        
        # 开始创建温馨提醒窗口
        self.create_timer.start(1)  # 每1ms创建一个
        
        # 开始保持最上层
        self.keep_on_top_timer.start(500)
    
    def create_one_tip(self):
        """创建一个温馨提醒窗口"""
        if self.current_index >= self.total_windows:
            self.create_timer.stop()
            return
        
        tip = random.choice(self.tips)
        bg_color = random.choice(self.bg_colors)
        
        if self.heart_mode and self.current_index < len(self._heart_points):
            # 爱心模式：使用心形坐标
            x, y = self._heart_points[self.current_index]
            window = WarmTipWindow(tip, bg_color)
            window.move(x, y)
        else:
            window = WarmTipWindow(tip, bg_color)
        
        window.show()
        self.tips_window.append(window)
        
        self.current_index += 1
    
    def close_next_window(self):
        """逐个关闭窗口"""
        if self.close_all:
            if self.tips_window:
                window = self.tips_window.pop(0)
                window.start_fade_out()
            else:
                self.close_timer.stop()
                self.close()
    
    def keep_on_top(self):
        """保持控制窗口在最上层"""
        if self.isVisible():
            self.raise_()
    

    
    def keyPressEvent(self, event):
        """按键事件"""
        if event.key() == Qt.Key_Space:
            self.on_space_press()
    
    def on_space_press(self):
        """空格键关闭所有窗口"""
        if not self.close_all:
            self.close_all = True
            self.keep_on_top_timer.stop()
            
            # 开始逐个关闭
            self.close_timer.start(1)  # 每1ms关闭一个
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)


def show_warm_tips(count=50, heart_mode=False):
    """显示温馨提醒（供外部调用）"""
    controller = WarmTipController(heart_mode=heart_mode)
    controller.total_windows = count
    controller.start()
    return controller
