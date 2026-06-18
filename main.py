# -*- coding: utf-8 -*-
"""
桌面健康提醒应用 v2.0
功能：护眼提醒、休息提醒、喝水提醒、自定义提醒、贪睡、勿扰、统计
技术栈：Python + PyQt5 + plyer（支持 Windows / macOS）
"""

import sys
import os
import logging

# 将项目根目录加入 sys.path，确保模块导入正常
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import IS_WINDOWS, apply_theme, apply_gradient_colors
from utils import (
    load_config, save_config, set_autostart,
    create_checkmark_icon, create_arrow_icons,
)
from ui.widgets import TooltipFilter


def setup_logging():
    """配置日志系统"""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "health-reminder.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger().info("=== 健康提醒应用启动 ===")


def main():
    setup_logging()

    # 设置 Windows AppUserModelID，使通知标题显示为"健康提醒"而非"Python"
    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("健康提醒.V2.0")
        except Exception:
            pass

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.installEventFilter(TooltipFilter(app))
    create_checkmark_icon()
    create_arrow_icons()

    from ui.floating_widget import FloatingWidget
    widget = FloatingWidget()
    apply_theme(widget.config.get("theme", "light"))
    apply_gradient_colors(widget.config)
    set_autostart(widget.config.get("auto_start", False))
    widget.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()



