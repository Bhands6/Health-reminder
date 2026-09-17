# -*- coding: utf-8 -*-
"""自定义控件：ToggleSwitch、TooltipLabel、TooltipFilter、进度环绘制"""

import time

from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QLineEdit
from PyQt5.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal,
    QObject, QEvent, QSize, QRectF,
)
from PyQt5.QtGui import (
    QColor, QPainter, QBrush, QPen, QFont, QRadialGradient, QLinearGradient,
    QIntValidator,
)

from constants import THEME, FONT_UI, FONT_EMOJI


class ToggleSwitch(QWidget):
    """自定义开关控件（accent：可选强调色，默认主题主色）"""
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None, accent=None):
        super().__init__(parent)
        self.setFixedSize(44, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._checked = checked
        self._accent = accent
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
        # 背景轨道（选中用强调色；未选中按主题深浅取灰——浅色下深灰过重）
        if self._checked:
            p.setBrush(QColor(*(self._accent or THEME.get("primary", (102, 126, 234)))))
        else:
            bg = THEME.get("bg_start", (102, 126, 234))
            is_dark = (bg[0] + bg[1] + bg[2]) / 3 < 128
            p.setBrush(QColor(80, 80, 100) if is_dark else QColor(178, 178, 198))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        # 圆形滑块
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(int(self._offset), 2, 20, 20)
        p.end()


class PillButton(QPushButton):
    """QPainter 自绘胶囊按钮。

    Qt QSS 的 border:none / border:transparent 在真机不裁剪圆角背景（直角实锤），
    观感按钮一律用本类自绘，不再依赖 QSS 圆角。
    kind: primary=紫→青渐变(白字) / muted=中性灰 / danger=红调 / dashed=虚线框
    颜色随主题深浅自适应（THEME.bg_start 平均亮度）。
    """
    def __init__(self, text="", parent=None, kind="muted", radius=21):
        super().__init__(text, parent)
        self._kind = kind
        self._radius = radius
        self._hover = False
        self._pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")
        self.setMinimumHeight(28)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def _is_dark(self):
        # 设置面板背景恒为渐变色 dim(0.35/0.45) 暗化版（任意渐变色下都是深底），
        # 因此 muted/dashed 恒用「暗底亮字」——不能按主题亮暗判断（light 预设的
        # 深紫字落在暗化底上会隐形，真机实锤）
        return True

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        r = min(self._radius, self.height() / 2)
        dark = self._is_dark()
        if self._kind == "primary":
            g = QLinearGradient(0, 0, self.width(), 0)
            if self._pressed:
                g.setColorAt(0, QColor(122, 76, 224))
                g.setColorAt(1, QColor(38, 191, 170))
            elif self._hover:
                g.setColorAt(0, QColor(157, 112, 248))
                g.setColorAt(1, QColor(62, 220, 202))
            else:
                g.setColorAt(0, QColor(139, 92, 246))
                g.setColorAt(1, QColor(45, 212, 191))
            p.setBrush(QBrush(g))
            p.setPen(Qt.NoPen)
        elif self._kind == "glass_tint":
            # 彩色毛玻璃：紫→青半透明垂直渐变 + 高光描边（hover 提亮）
            a = 200 if self._pressed else (175 if self._hover else 140)
            g = QLinearGradient(0, 0, 0, self.height())
            g.setColorAt(0, QColor(150, 110, 250, min(255, a + 20)))
            g.setColorAt(1, QColor(45, 212, 191, a))
            p.setBrush(QBrush(g))
            p.setPen(QPen(QColor(255, 255, 255, 90 if self._hover else 62), 1.2))
        elif self._kind == "glass":
            # 白系毛玻璃：顶部亮底部暗的垂直渐变（模拟玻璃反光）+ 高光描边
            if self._pressed:
                top, bottom, border = 62, 26, 105
            elif self._hover:
                top, bottom, border = 52, 20, 92
            else:
                top, bottom, border = 40, 14, 72
            g = QLinearGradient(0, 0, 0, self.height())
            g.setColorAt(0, QColor(255, 255, 255, top))
            g.setColorAt(1, QColor(255, 255, 255, bottom))
            p.setBrush(QBrush(g))
            p.setPen(QPen(QColor(255, 255, 255, border), 1.2))
        elif self._kind == "danger":
            p.setBrush(QColor(244, 67, 54, 150 if (self._hover or self._pressed) else 80))
            p.setPen(Qt.NoPen)
        else:
            if self._pressed:
                p.setBrush(QColor(255, 255, 255, 46))
            elif self._hover:
                p.setBrush(QColor(255, 255, 255, 34))
            else:
                p.setBrush(QColor(255, 255, 255, 26))
            p.setPen(Qt.NoPen)
        p.drawRoundedRect(rect, r, r)
        if self._kind == "dashed":
            pen = QPen(QColor(255, 255, 255, 95), 1)
            pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect, r, r)
        if self._kind == "primary":
            p.setPen(QColor(255, 255, 255))
        else:
            p.setPen(QColor(239, 237, 251))
        f = self.font()
        f.setBold(self._kind == "primary")
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())


class Stepper(QWidget):
    """水平步进器：「− 值 单位 +」胶囊（设置面板设计稿样式）

    中间值可直接点击编辑（纯数字，回车/失焦提交并 clamp 到范围）。
    接口对齐 QSpinBox 常用子集：value/setValue/setRange，
    并提供 editingFinished 信号兼容原 spin.editingFinished 的自动收集逻辑。
    """
    valueChanged = pyqtSignal(int)
    editingFinished = pyqtSignal()

    def __init__(self, value=30, minimum=1, maximum=480, suffix=" 分钟", parent=None):
        super().__init__(parent)
        self._suffix = suffix
        self._min = minimum
        self._max = maximum
        self._value = max(minimum, min(maximum, int(value)))
        self.setObjectName("stepperHost")
        self.setAttribute(Qt.WA_StyledBackground, True)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(2)
        self.minus_btn = PillButton("−", kind="muted", radius=12)
        self.minus_btn.setFixedSize(24, 24)
        self.minus_btn.clicked.connect(lambda: self.setValue(self._value - 1))
        # 中间值可点击直接编辑：纯数字输入框 + 单位小字（回车/失焦提交）
        self.value_edit = QLineEdit(str(self._value))
        self.value_edit.setObjectName("stepperEdit")
        self.value_edit.setAlignment(Qt.AlignCenter)
        self.value_edit.setFrame(False)
        self.value_edit.setFixedWidth(44)
        self.value_edit.setValidator(QIntValidator(minimum, maximum, self))
        self.value_edit.editingFinished.connect(self._commit_edit)
        self.value_edit.textChanged.connect(self._live_clamp)
        self.unit_label = QLabel(suffix.strip())
        self.unit_label.setObjectName("stepperUnit")
        self.plus_btn = PillButton("+", kind="muted", radius=12)
        self.plus_btn.setFixedSize(24, 24)
        self.plus_btn.clicked.connect(lambda: self.setValue(self._value + 1))
        lay.addWidget(self.minus_btn)
        lay.addWidget(self.value_edit)
        lay.addWidget(self.unit_label)
        lay.addWidget(self.plus_btn)
        self._sync()

    def _live_clamp(self, text):
        """实时钳上限：输入一旦超过最大值立即变为最大数（无需提交）。

        只钳上限；下限（如 0）允许保留中间态，提交时再收。setText 会再触发
        textChanged，但 "480" 合法直接 return，不会死循环。
        """
        t = text.strip()
        if not t.isdigit():
            return
        if int(t) > self._max:
            self.value_edit.setText(str(self._max))
            self.value_edit.setCursorPosition(len(str(self._max)))

    def _commit_edit(self):
        """编辑框提交：解析数字并 clamp；值未变时也补发 editingFinished（对齐 QSpinBox）"""
        text = self.value_edit.text().strip()
        for token in ("分钟", "min"):
            text = text.replace(token, "")
        try:
            v = int(text)
        except ValueError:
            v = self._value
        changed = max(self._min, min(self._max, v)) != self._value
        self.setValue(v)
        if not changed:
            self.editingFinished.emit()
        self._sync()  # 非法输入时把编辑框回写为当前值（避免残留乱文本）

    def _sync(self):
        self.value_edit.setText(str(self._value))

    def value(self):
        return self._value

    def setValue(self, v):
        v = max(self._min, min(self._max, int(v)))
        if v == self._value:
            return
        self._value = v
        self._sync()
        self.valueChanged.emit(v)
        self.editingFinished.emit()

    def setRange(self, minimum, maximum):
        self._min, self._max = minimum, maximum
        self.setValue(self._value)


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

