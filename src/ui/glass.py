# -*- coding: utf-8 -*-
"""玻璃拟态（Glassmorphism）绘制工具

样式参数对齐 Bhands_Web 项目的玻璃效果：
    背景      rgba(0, 0, 0, .10)              —— 玻璃本身几乎不挡光
    背景模糊  backdrop-filter: blur(12px) saturate(1.8) brightness(1.16)
    边缘高光  inset 0 0 2px 1px rgba(255,255,255,.35)
    内侧柔光  inset 0 0 10px 4px rgba(255,255,255,.15)
    外投影    0 16px 56px rgba(17,17,26,.05)
    圆角      50px（面板）/ 999px（胶囊）

注：blur / saturate / brightness 在 Web 上作用于「元素背后的内容」，
桌面端要模糊窗口背后的桌面需要走 Windows 亚克力 API（见 acrylic.py）。
本模块只负责玻璃自身的质感：底色、边缘高光、内侧柔光、多层投影。
"""

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import (
    QBrush, QColor, QLinearGradient, QPainter, QPen, QRadialGradient,
)

# rgba(0,0,0,.10)
GLASS_TINT = (0, 0, 0, 26)
# inset 0 0 2px 1px rgba(255,255,255,.35)
GLASS_EDGE = (255, 255, 255, 89)
# inset 0 0 10px 4px rgba(255,255,255,.15)
GLASS_INNER_GLOW = (255, 255, 255, 38)
# 0 16px 56px rgba(17,17,26,.05)
GLASS_SHADOW = (17, 17, 26)
# brightness(1.16) 的近似：叠一层极淡的白
GLASS_BRIGHTEN = (255, 255, 255, 15)


def draw_glass_panel(painter, rect, radius=24, tint=None, shadow=True,
                     edge=True, inner_glow=True):
    """绘制一块玻璃面板

    painter: 已开启 Antialiasing 的 QPainter
    rect:    QRectF / QRect
    radius:  圆角半径
    tint:    (r, g, b, a) 底色，默认取 Web 侧的 rgba(0,0,0,.10)
    """
    r = QRectF(rect)
    base = tint if tint is not None else GLASS_TINT

    # 1) 外侧多层投影：从大到小叠出柔和衰减（对应 CSS 的 0 16px 56px 等）
    if shadow:
        for spread, dy, alpha in ((6, 18, 9), (4, 11, 10), (2, 5, 9)):
            s = QRectF(r).adjusted(-spread, -spread + dy, spread, spread + dy)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(GLASS_SHADOW[0], GLASS_SHADOW[1],
                                    GLASS_SHADOW[2], alpha))
            painter.drawRoundedRect(s, radius + spread, radius + spread)

    # 2) 玻璃主体：底色 + 顶部略亮（模拟 brightness 提亮）
    body = QLinearGradient(r.topLeft(), r.bottomLeft())
    body.setColorAt(0.0, QColor(base[0], base[1], base[2],
                                min(255, base[3] + GLASS_BRIGHTEN[3])))
    body.setColorAt(0.45, QColor(*base))
    body.setColorAt(1.0, QColor(base[0], base[1], base[2],
                                max(0, base[3] - 4)))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(body))
    painter.drawRoundedRect(r, radius, radius)

    # 3) 内侧柔光：从边缘向内的白色晕（inset 0 0 10px 4px）
    if inner_glow:
        glow = QRadialGradient(r.center(), max(r.width(), r.height()) * 0.6)
        glow.setColorAt(0.0, QColor(255, 255, 255, 0))
        glow.setColorAt(0.70, QColor(255, 255, 255, 0))
        glow.setColorAt(1.0, QColor(GLASS_INNER_GLOW[0], GLASS_INNER_GLOW[1],
                                    GLASS_INNER_GLOW[2], GLASS_INNER_GLOW[3]))
        painter.setBrush(QBrush(glow))
        painter.drawRoundedRect(r, radius, radius)

    # 4) 边缘高光描边（inset 0 0 2px 1px rgba(255,255,255,.35)）
    if edge:
        inset = QRectF(r).adjusted(0.6, 0.6, -0.6, -0.6)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(*GLASS_EDGE), 1.2))
        painter.drawRoundedRect(inset, radius, radius)

        # 顶边再补一道更亮的高光，做出玻璃的「厚度」
        top_pen = QPen(QColor(255, 255, 255, 51), 1.4)
        top_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(top_pen)
        y = r.top() + radius * 0.42
        painter.drawLine(int(r.left() + radius * 0.7), int(y),
                         int(r.right() - radius * 0.7), int(y))


def draw_glass_backdrop(painter, rect, radius=24, blur_strength=12, tint=None):
    """模拟 backdrop-filter 的观感

    真实模糊需要 Windows 亚克力 API；这里用「降低对比 + 轻微提亮」近似，
    用于不支持亚克力的场合或离屏预览。
    """
    r = QRectF(rect)
    layer = QLinearGradient(r.topLeft(), r.bottomRight())
    layer.setColorAt(0.0, QColor(255, 255, 255, 26))
    layer.setColorAt(0.5, QColor(255, 255, 255, 12))
    layer.setColorAt(1.0, QColor(0, 0, 0, 18))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(layer))
    painter.drawRoundedRect(r, radius, radius)


def glass_color(alpha_out=255):
    """返回适合作为文字/图标的浅色（玻璃上通常用白字）"""
    return QColor(255, 255, 255, alpha_out)
