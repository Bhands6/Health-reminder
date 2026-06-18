# -*- coding: utf-8 -*-
"""自定义控件：ToggleSwitch、TooltipLabel、TooltipFilter、进度环绘制"""

import time

from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal,
    QObject, QEvent, QSize,
)
from PyQt5.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QRadialGradient,
)

from constants import THEME, FONT_UI, FONT_EMOJI


class ToggleSwitch(QWidget):
    """自定义开关控件"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._offset = 22.0 if checked else 2.0
        self._anim = QPropertyAnimation(self, b"offset", self)
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


class TooltipLabel(QLabel):
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


class TooltipFilter(QObject):
    """全局事件过滤器，拦截 Tooltip 显示自定义圆角提示"""
    def eventFilter(self, obj, event):
        global _tooltip
        if event.type() == QEvent.ToolTip:
            text = obj.toolTip()
            if text:
                if _tooltip is None:
                    _tooltip = TooltipLabel()
                font = _tooltip.font()
                font.setPointSize(9)
                _tooltip.setFont(font)
                _tooltip.show_at(text, event.globalPos())
            return True
        if event.type() in (QEvent.Leave, QEvent.Hide, QEvent.WindowDeactivate):
            if _tooltip is not None:
                _tooltip.hide()
        return super().eventFilter(obj, event)


def draw_progress_ring(painter, cx, cy, radius, progress, color, bg_color=(255, 255, 255, 255)):
    """绘制进度环"""
    # 背景环
    pen = QPen(QColor(*bg_color), 3)
    pen.setCapStyle(Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

    # 进度环
    pen.setColor(QColor(*color, 220))
    pen.setWidth(4)
    painter.setPen(pen)
    start_angle = 90 * 16
    span_angle = -int(progress * 360 * 16)
    painter.drawArc(cx - radius, cy - radius, radius * 2, radius * 2, start_angle, span_angle)


def draw_closed_eyes(painter, cx, size, theme_color):
    """绘制闭眼状态的 👀 风格图标"""
    painter.setPen(Qt.NoPen)
    ew = int(size * 1.0)
    eh = int(size * 0.6)
    gap = int(size * 0.35)
    pupil_r = int(eh * 0.28)

    for side in (-1, 1):
        ex = cx + side * (ew // 2 + gap // 2) - ew // 2
        ey = cx - eh // 2
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(ex, ey, ew, eh)
        px = ex + int(ew * 0.6) - pupil_r
        py = ey + int(eh * 0.55) - pupil_r
        painter.setBrush(QColor(30, 30, 30))
        painter.drawEllipse(px, py, pupil_r * 2, pupil_r * 2)
        painter.setBrush(QColor(*theme_color, 230))
        painter.drawRect(ex - 1, ey - 1, ew + 2, eh // 2 + 2)


def draw_closed_rest(painter, cx, size):
    """绘制闭眼状态的休息图标 🧘"""
    painter.setPen(Qt.NoPen)
    s = size * 1.5
    head_r = int(s * 0.22)
    painter.setBrush(QColor(255, 200, 150))
    painter.drawEllipse(cx - head_r, cx - int(s * 0.48), head_r * 2, head_r * 2)
    painter.setPen(QPen(QColor(80, 60, 50), max(1, int(s * 0.06)), Qt.SolidLine, Qt.RoundCap))
    hy = cx - int(s * 0.44)
    painter.drawLine(cx - int(head_r * 0.6), hy, cx - int(head_r * 0.15), hy)
    painter.drawLine(cx + int(head_r * 0.15), hy, cx + int(head_r * 0.6), hy)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(118, 75, 162))
    body_y = cx - int(s * 0.25)
    painter.drawEllipse(cx - int(s * 0.3), body_y, int(s * 0.6), int(s * 0.4))
    leg_y = cx + int(s * 0.05)
    painter.drawEllipse(cx - int(s * 0.42), leg_y, int(s * 0.84), int(s * 0.25))


def draw_closed_water(painter, cx, size):
    """绘制半满状态的水滴图标 💧"""
    from PyQt5.QtGui import QPainterPath
    painter.setPen(Qt.NoPen)
    s = size * 1.2
    drop_h = int(s * 0.9)
    drop_w = int(s * 0.55)
    top = cx - drop_h // 2

    path = QPainterPath()
    path.moveTo(cx, top)
    path.quadTo(cx + drop_w, top + drop_h * 0.55, cx + drop_w * 0.5, top + drop_h * 0.75)
    path.arcTo(cx - drop_w * 0.5, top + drop_h * 0.5, drop_w, drop_h * 0.5, 0, 180)
    path.quadTo(cx - drop_w, top + drop_h * 0.55, cx, top)

    painter.setBrush(QColor(255, 255, 255, 80))
    painter.setPen(QPen(QColor(255, 255, 255), 2))
    painter.drawPath(path)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(72, 209, 204, 160))
    water_y = top + drop_h * 0.45
    water_clip = QPainterPath()
    water_clip.addRect(cx - drop_w, water_y, drop_w * 2, drop_h)
    filled = path.intersected(water_clip)
    painter.drawPath(filled)

