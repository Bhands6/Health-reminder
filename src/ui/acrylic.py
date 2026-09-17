# -*- coding: utf-8 -*-
"""Windows 亚克力（Acrylic）窗口背景

Web 上的 backdrop-filter 由浏览器合成器实现；桌面程序要模糊「窗口背后的桌面/其他窗口」，
只能交给系统合成器 —— 也就是 Win10 1803+ / Win11 的 SetWindowCompositionAttribute。

两个已知代价：
  1. 模糊作用于**整个窗口矩形**。窗口若留透明边距或做圆角，边角处会露出「模糊的方块」，
     所以启用亚克力的窗口建议让背景铺满内容区。
  2. 亚克力有 GPU 合成开销，拖动窗口时可能掉帧（Windows 已知问题）；
     对性能敏感的场景可以改用 enable_blur()（更轻的毛玻璃）。

非 Windows 或调用失败时返回 False，调用方无需特殊处理。
"""

import ctypes
import logging

logger = logging.getLogger(__name__)

WCA_ACCENT_POLICY = 19

ACCENT_DISABLED = 0
ACCENT_ENABLE_BLURBEHIND = 3            # Win8+ 毛玻璃，较轻
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4     # Win10 1803+ 亚克力，更细腻

# AccentFlags：0x20|0x40|0x80|0x100 = 四边都绘制
ACCENT_FLAGS_ALL = 0x20 | 0x40 | 0x80 | 0x100


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_int),
        ("AccentFlags", ctypes.c_int),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_int),
    ]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t),
    ]


def _rgba_to_abgr(r, g, b, a=255):
    """GradientColor 是 ABGR 顺序（0xAABBGGRR），不是 RGBA"""
    return ((a & 0xFF) << 24) | ((b & 0xFF) << 16) | ((g & 0xFF) << 8) | (r & 0xFF)


def set_acrylic(hwnd, r=22, g=24, b=38, alpha=150,
                state=ACCENT_ENABLE_ACRYLICBLURBEHIND):
    """给窗口启用亚克力背景

    hwnd:  int(widget.winId())
    返回 True 表示 API 调用成功（不代表系统一定支持该效果）
    """
    try:
        accent = ACCENT_POLICY()
        accent.AccentState = state
        accent.AccentFlags = ACCENT_FLAGS_ALL
        accent.GradientColor = _rgba_to_abgr(r, g, b, alpha)
        accent.AnimationId = 0

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)

        func = ctypes.windll.user32.SetWindowCompositionAttribute
        func.argtypes = [ctypes.c_void_p, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA)]
        func.restype = ctypes.c_int
        ok = func(ctypes.c_void_p(int(hwnd)), ctypes.byref(data))
        logger.debug("SetWindowCompositionAttribute(state=%s) -> %s", state, ok)
        return bool(ok)
    except Exception as e:
        logger.warning("Failed to set acrylic: %s", e)
        return False


def enable_blur(hwnd, r=22, g=24, b=38, alpha=140):
    """更轻的毛玻璃（Win8+），拖窗口更顺但质感略逊于亚克力"""
    return set_acrylic(hwnd, r, g, b, alpha, state=ACCENT_ENABLE_BLURBEHIND)


# DwmSetWindowAttribute 的 DWMWA_WINDOW_CORNER_PREFERENCE
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2


def set_round_corner(hwnd, preference=DWMWCP_ROUND):
    """让 Win11 给窗口加系统圆角

    无边框窗口如果自己画圆角，亚克力的模糊矩形会在四角露出来；
    交给 DWM 处理则由系统同时负责圆角与裁剪，不会有泄漏。
    """
    try:
        value = ctypes.c_int(preference)
        func = ctypes.windll.dwmapi.DwmSetWindowAttribute
        func.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                         ctypes.c_void_p, ctypes.c_uint]
        func.restype = ctypes.c_int
        ok = func(ctypes.c_void_p(int(hwnd)), DWMWA_WINDOW_CORNER_PREFERENCE,
                  ctypes.byref(value), ctypes.sizeof(value))
        logger.debug("DwmSetWindowAttribute(corner) -> %s", ok)
        return ok == 0
    except Exception as e:
        logger.warning("Failed to set round corner: %s", e)
        return False


def disable_acrylic(hwnd):
    """关闭模糊背景"""
    return set_acrylic(hwnd, state=ACCENT_DISABLED)
