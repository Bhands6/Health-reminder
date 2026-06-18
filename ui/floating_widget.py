# -*- coding: utf-8 -*-
"""悬浮窗口：支持迷你模式、进度环、勿扰、系统托盘、全局快捷键"""

import time
import logging
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QApplication, QMenu, QAction, QSystemTrayIcon,
    QDesktopWidget, QShortcut, QMessageBox, QDialog,
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QSize
from PyQt5.QtGui import (
    QColor, QPainter, QFont, QIcon, QLinearGradient, QBrush,
    QPen, QPixmap, QRadialGradient, QFontMetrics, QKeySequence,
)

from constants import (
    THEME, BUILTIN_REMINDERS, CUSTOM_COLORS, FONT_EMOJI, FONT_UI,
)
from utils import (
    load_config, save_config, record_stat, get_today_stats,
    play_reminder_sound, is_dnd_active, load_stats,
)
from ui.widgets import (
    draw_progress_ring, draw_closed_eyes, draw_closed_rest, draw_closed_water,
)
from ui.popup import ReminderPopup

logger = logging.getLogger(__name__)


class FloatingWidget(QWidget):
    """悬浮窗口 - 支持迷你模式、进度环、勿扰"""

    BUILTIN = dict(BUILTIN_REMINDERS)

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.paused = False
        self.drag_pos = QPoint()
        self.timers = {}
        self.next_times = {}
        self.snooze_timers = {}
        self.mini_mode = self.config.get("mini_mode", False)
        self.hovered = False
        self._popups = []

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self.update_display)
        self.countdown_timer.start(100)

        self.init_ui()
        self.init_timers()
        self.init_tray()
        self.init_shortcuts()
        logger.info("FloatingWidget initialized")

    def init_ui(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.update_size()
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, 80)

    def update_size(self):
        if self.mini_mode:
            size = self.config.get("widget_size", 80)
            self.setFixedSize(size, size)
        else:
            self.setFixedSize(220, 120)

    def _get_all_reminders(self):
        """获取所有提醒（内置 + 自定义）"""
        reminders = {}
        for key, (icon, title, msg, color) in self.BUILTIN.items():
            cfg = self.config.get(key, {})
            reminders[key] = {
                "icon": icon, "name": title, "message": msg,
                "color": color, "interval": cfg.get("interval", 20),
                "enabled": cfg.get("enabled", False),
            }
        for i, item in enumerate(self.config.get("custom", [])):
            key = f"custom_{i}"
            reminders[key] = {
                "icon": item.get("icon", "🔔"),
                "name": item.get("name", "自定义"),
                "message": item.get("message", ""),
                "color": CUSTOM_COLORS[i % len(CUSTOM_COLORS)],
                "interval": item.get("interval", 30),
                "enabled": item.get("enabled", True),
            }
        return reminders

    def init_timers(self):
        for key, info in self._get_all_reminders().items():
            if info["enabled"]:
                interval = info["interval"] * 60 * 1000
                timer = QTimer(self)
                timer.timeout.connect(lambda k=key: self.trigger_reminder(k))
                timer.start(interval)
                self.timers[key] = timer
                self.next_times[key] = datetime.now() + timedelta(milliseconds=interval)
        logger.info("Timers started: %s", list(self.timers.keys()))

    def reinit_timers(self):
        for timer in self.timers.values():
            timer.stop()
        for timer in self.snooze_timers.values():
            timer.stop()
        self.timers.clear()
        self.next_times.clear()
        self.snooze_timers.clear()
        self.init_timers()

    def trigger_reminder(self, key):
        if self.paused:
            return
        if is_dnd_active(self.config):
            return

        all_rem = self._get_all_reminders()
        if key not in all_rem:
            return
        info = all_rem[key]

        interval = info["interval"] * 60 * 1000
        self.next_times[key] = datetime.now() + timedelta(milliseconds=interval)
        record_stat(key, "triggered")

        # 播放提示音
        if self.config.get("sound", True):
            play_reminder_sound(key if key in BUILTIN_REMINDERS else "custom")

        # 系统通知
        try:
            from plyer import notification
            notification.notify(title=info["name"], message=info["message"], timeout=5, app_name="健康提醒")
        except Exception as e:
            logger.warning("System notification failed: %s", e)

        # 弹窗
        popup = ReminderPopup(
            f"{info['icon']} {info['message']}", info["color"], key,
            interval=info["interval"],
            position=self.config.get("popup_position", "center"),
        )
        popup.snooze_signal.connect(self.handle_snooze)
        popup.show()
        self._popups.append(popup)
        # 清理已关闭的弹窗引用
        self._popups = [p for p in self._popups if p.isVisible()]

    def handle_snooze(self, key, minutes):
        """处理贪睡"""
        if key in self.timers:
            self.timers[key].stop()

        def _snooze_callback(k=key):
            if k in self.timers:
                self.timers[k].start()
            self.trigger_reminder(k)

        snooze_timer = QTimer(self)
        snooze_timer.setSingleShot(True)
        snooze_timer.timeout.connect(_snooze_callback)
        snooze_timer.start(minutes * 60 * 1000)
        self.snooze_timers[key] = snooze_timer

    def get_next_reminder(self):
        if not self.next_times:
            return None, None
        nearest_key = min(self.next_times, key=lambda k: self.next_times[k])
        remaining = self.next_times[nearest_key] - datetime.now()
        if remaining.total_seconds() < 0:
            remaining = timedelta(seconds=0)
        return nearest_key, remaining

    # ==================== 绘制 ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.mini_mode:
            self._paint_mini(painter)
        else:
            self._paint_full(painter)

    def _paint_mini(self, painter):
        size = self.config.get("widget_size", 80)
        shadow_offset = max(4, size // 12)
        circle_size = size - shadow_offset
        circle_r = circle_size // 2

        shadow = QColor(0, 0, 0, 50)
        painter.setBrush(QBrush(shadow))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_offset, shadow_offset, circle_size, circle_size, circle_r, circle_r)

        gradient = QRadialGradient(circle_r, circle_r, circle_r)
        gradient.setColorAt(0, QColor(*THEME["primary"], 230))
        gradient.setColorAt(1, QColor(*THEME["secondary"], 230))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, circle_size, circle_size, circle_r, circle_r)

        if is_dnd_active(self.config):
            icon_size = max(12, circle_size // 4)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont(FONT_EMOJI, icon_size))
            painter.drawText(0, 0, circle_size, circle_size, Qt.AlignCenter, "🌙")
            return

        key, remaining = self.get_next_reminder()
        all_rem = self._get_all_reminders()
        if key and remaining and key in all_rem:
            info = all_rem[key]
            total = info["interval"] * 60
            elapsed = total - remaining.total_seconds()
            progress = max(0, min(1, elapsed / total))
            ring_r = circle_r - 7
            draw_progress_ring(painter, circle_r, circle_r, ring_r, progress, info["color"])

            icon_size = max(12, circle_size // 4)
            t = time.time() % 3.5
            blink = t < 0.4
            if key == "eye_care" and blink:
                draw_closed_eyes(painter, circle_r, icon_size, THEME["primary"])
            elif key == "rest" and blink:
                draw_closed_rest(painter, circle_r, icon_size)
            elif key == "water" and blink:
                draw_closed_water(painter, circle_r, icon_size)
            else:
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont(FONT_EMOJI, icon_size))
                painter.drawText(0, 0, circle_size, circle_size, Qt.AlignCenter, info["icon"])
        else:
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont(FONT_EMOJI, max(12, circle_size // 4)))
            painter.drawText(0, 0, circle_size, circle_size, Qt.AlignCenter, "💚")

    def _paint_full(self, painter):
        shadow = QColor(0, 0, 0, 50)
        painter.setBrush(QBrush(shadow))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(6, 6, self.width() - 6, self.height() - 6, 18, 18)

        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor(*THEME["primary"], 230))
        gradient.setColorAt(1, QColor(*THEME["secondary"], 230))
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(0, 0, self.width() - 6, self.height() - 6, 18, 18)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont(FONT_UI, 11, QFont.Bold))
        if is_dnd_active(self.config):
            status = "🌙 勿扰中"
        elif self.paused:
            status = "⏸ 已暂停"
        else:
            status = "💚 健康提醒"
        painter.drawText(15, 12, self.width() - 20, 25, Qt.AlignLeft, status)

        key, remaining = self.get_next_reminder()
        all_rem = self._get_all_reminders()
        if key and remaining and key in all_rem:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            info = all_rem[key]
            painter.setFont(QFont(FONT_UI, 10))
            painter.setPen(QColor(255, 255, 255, 220))
            painter.drawText(15, 40, self.width() - 20, 20, Qt.AlignLeft,
                           f"{info['icon']} {info['name']}  {mins:02d}:{secs:02d}")

            total = info["interval"] * 60
            elapsed = total - remaining.total_seconds()
            progress = max(0, min(1, elapsed / total))
            bar_y = 65
            bar_width = self.width() - 30
            painter.setBrush(QColor(255, 255, 255, 40))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(15, bar_y, bar_width, 5, 2, 2)
            painter.setBrush(QColor(255, 255, 255, 150))
            painter.drawRoundedRect(15, bar_y, int(bar_width * progress), 5, 2, 2)

            painter.setPen(QColor(255, 255, 255, 150))
            painter.setFont(QFont(FONT_UI, 8))
            painter.drawText(15, 75, self.width() - 20, 15, Qt.AlignLeft,
                           f"已完成 {get_today_stats().get(key, {}).get('completed', 0)} 次")
        else:
            painter.setFont(QFont(FONT_UI, 9))
            painter.setPen(QColor(255, 255, 255, 150))
            painter.drawText(15, 45, self.width() - 20, 20, Qt.AlignLeft, "暂无活跃提醒")

        # 右下角提示
        painter.setFont(QFont(FONT_UI, 8))
        painter.setPen(QColor(255, 255, 255, 80))
        painter.drawText(15, self.height() - 22, self.width() - 20, 15, Qt.AlignLeft, "右键菜单 | 双击设置")

    # ==================== 交互 ====================

    def update_display(self):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.open_settings()

    def enterEvent(self, event):
        self.hovered = True
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(30,30,50,240);
                color: rgba(200,180,255,1);
                border: 1px solid rgba(200,180,255,0.2);
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(102,126,234,0.4);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(200,180,255,0.15);
                margin: 4px 10px;
            }
        """)

        # 暂停/继续
        pause_text = "▶ 继续提醒" if self.paused else "⏸ 暂停提醒"
        pause_action = QAction(pause_text, self)
        pause_action.triggered.connect(self.toggle_pause)
        menu.addAction(pause_action)

        menu.addSeparator()

        # 迷你模式切换
        mini_text = "🔲 完整模式" if self.mini_mode else "⭕ 迷你模式"
        mini_action = QAction(mini_text, self)
        mini_action.triggered.connect(self.toggle_mini_mode)
        menu.addAction(mini_action)

        # 悬浮球大小（仅迷你模式）
        if self.mini_mode:
            size_menu = menu.addMenu("⭕ 悬浮球大小")
            for s in [60, 80, 100, 120, 150, 180]:
                act = QAction(f"{s}px", self)
                act.triggered.connect(lambda _, sz=s: self.set_widget_size(sz))
                size_menu.addAction(act)

        menu.addSeparator()

        # 今日统计
        stats_action = QAction("📊 今日统计", self)
        stats_action.triggered.connect(self.show_stats)
        menu.addAction(stats_action)

        # 设置
        settings_action = QAction("⚙️ 设置", self)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        # 退出
        quit_action = QAction("🚪 退出", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)

        menu.exec_(event.globalPos())

    def toggle_pause(self):
        self.paused = not self.paused
        status = "已暂停" if self.paused else "已恢复"
        logger.info("Reminders %s", status)
        self.update()

    def toggle_mini_mode(self):
        self.mini_mode = not self.mini_mode
        self.config["mini_mode"] = self.mini_mode
        save_config(self.config)
        self.update_size()
        self.update()

    def set_widget_size(self, size):
        self.config["widget_size"] = size
        save_config(self.config)
        self.update_size()
        self.update()

    def show_stats(self):
        today_stats = get_today_stats()
        lines = ["📊 今日统计\n"]
        all_rem = self._get_all_reminders()
        total_triggered = 0
        total_completed = 0
        for key, info in all_rem.items():
            stat = today_stats.get(key, {})
            triggered = stat.get("triggered", 0)
            completed = stat.get("completed", 0)
            total_triggered += triggered
            total_completed += completed
            lines.append(f"{info['icon']} {info['name']}: 触发 {triggered} 次, 完成 {completed} 次")

        lines.append(f"\n总计: 触发 {total_triggered} 次, 完成 {total_completed} 次")
        QMessageBox.information(self, "今日统计", "\n".join(lines))

    def open_settings(self):
        from ui.settings import SettingsDialog
        dialog = SettingsDialog(self.config, self)
        result = dialog.exec_()
        # 确保关闭设置后主窗口仍然可见
        if not self.isVisible():
            self.show()
        if result == QDialog.Accepted:
            self.config = dialog.config
            self.update_size()
            self.reinit_timers()

    def init_tray(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(*THEME["primary"]))
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont(FONT_EMOJI, 16))
        painter.drawText(0, 0, 32, 32, Qt.AlignCenter, "💚")
        painter.end()
        icon = QIcon(pixmap)

        self.tray = QSystemTrayIcon(icon, self)
        self.tray.setToolTip("健康提醒")

        tray_menu = QMenu()
        show_action = QAction("显示悬浮窗", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)

        tray_menu.addSeparator()

        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

    def init_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+Shift+P"), self).activated.connect(self.toggle_pause)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self).activated.connect(self.open_settings)
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self).activated.connect(self.quit_app)
        QShortcut(QKeySequence("Ctrl+Shift+M"), self).activated.connect(self.toggle_mini_mode)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        """å¿½ç¥å³é­äºä»¶ï¼é²æ­¢åºç¨éåº"""
        event.ignore()
        self.hide()

    def quit_app(self):
        self.tray.hide()
        QApplication.quit()
