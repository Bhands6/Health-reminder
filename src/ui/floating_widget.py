# -*- coding: utf-8 -*-
"""悬浮窗口：支持迷你模式、进度环、勿扰、系统托盘、全局快捷键"""

import time
import logging
from datetime import datetime, timedelta

from PyQt5.QtWidgets import (
    QWidget, QApplication, QMenu, QAction, QSystemTrayIcon,
    QDesktopWidget, QShortcut, QMessageBox, QDialog,
    QSlider, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidgetAction, QSpinBox,
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QRectF
from PyQt5.QtGui import (
    QColor, QPainter, QFont, QIcon, QPixmap, QKeySequence,
)

from constants import (
    THEME, BUILTIN_REMINDERS, CUSTOM_COLORS, FONT_EMOJI, FONT_UI, APP_ICON,
    IS_WINDOWS,
)
from utils import (
    load_config, save_config, record_stat, get_today_stats,
    play_reminder_sound, is_dnd_active, load_stats,
)
from ui.widgets import (
    draw_progress_ring, draw_closed_eyes, draw_closed_rest, draw_closed_water,
)
from ui.glass import draw_glass_panel, draw_glass_text
from ui.popup import ReminderPopup
from ui.warm_tips import show_warm_tips

logger = logging.getLogger(__name__)

# ---- Windows 系统级热键（RegisterHotKey）相关常量 ----
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes


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
        self._hotkey_actions = {}        # 系统级热键 id -> 处理方法名
        self._fallback_shortcuts = []    # 未能注册为系统级热键时的窗口级快捷键

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
            size = self.config.get("widget_size", 100)
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
        all_rem = self._get_all_reminders()
        if key not in all_rem:
            return
        info = all_rem[key]

        # 先滚动下一次触发时间：暂停 / 勿扰期间也要滚动，
        # 否则倒计时会一直停在 00:00、进度环保持满格
        interval = info["interval"] * 60 * 1000
        self.next_times[key] = datetime.now() + timedelta(milliseconds=interval)

        if self.paused:
            return
        if is_dnd_active(self.config):
            return

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

        # 回收上一次的贪睡定时器，避免反复贪睡时定时器对象越积越多
        old_timer = self.snooze_timers.pop(key, None)
        if old_timer is not None:
            old_timer.stop()
            old_timer.deleteLater()

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
        size = self.config.get("widget_size", 100)
        margin = max(6, size // 12)          # 留白给玻璃的外投影
        circle_size = size - margin * 2
        circle_r = circle_size // 2
        cx = margin + circle_r
        box = (margin, margin, circle_size, circle_size)

        # 玻璃球体：极淡底色 + 边缘高光 + 内侧柔光
        draw_glass_panel(painter, QRectF(*box), radius=circle_r)

        if is_dnd_active(self.config):
            icon_size = max(12, circle_size // 4)
            draw_glass_text(painter, *box, Qt.AlignCenter, "🌙",
                            QFont(FONT_EMOJI, icon_size))
            return

        key, remaining = self.get_next_reminder()
        all_rem = self._get_all_reminders()
        if key and remaining and key in all_rem:
            info = all_rem[key]
            total = info["interval"] * 60
            elapsed = total - remaining.total_seconds()
            progress = max(0, min(1, elapsed / total))
            ring_r = circle_r - 7
            draw_progress_ring(painter, cx, cx, ring_r, progress, info["color"])

            icon_size = max(12, circle_size // 4)
            t = time.time() % 3.5
            blink = t < 0.4
            if key == "eye_care" and blink:
                draw_closed_eyes(painter, cx, icon_size, THEME["primary"])
            elif key == "rest" and blink:
                draw_closed_rest(painter, cx, icon_size)
            elif key == "water" and blink:
                draw_closed_water(painter, cx, icon_size)
            else:
                draw_glass_text(painter, *box, Qt.AlignCenter, info["icon"],
                                QFont(FONT_EMOJI, icon_size))
        else:
            draw_glass_text(painter, *box, Qt.AlignCenter, "💚",
                            QFont(FONT_EMOJI, max(12, circle_size // 4)))

    def _paint_full(self, painter):
        margin = 8
        panel = QRectF(0, 0, self.width() - margin, self.height() - margin)
        text_w = self.width() - 20

        # 玻璃面板：极淡底色 + 边缘高光 + 内侧柔光 + 多层投影
        draw_glass_panel(painter, panel, radius=20)

        if is_dnd_active(self.config):
            status = "🌙 勿扰中"
        elif self.paused:
            status = "⏸ 已暂停"
        else:
            status = "💚 健康提醒"
        draw_glass_text(painter, 15, 12, text_w, 25, Qt.AlignLeft, status,
                        QFont(FONT_UI, 11, QFont.Bold))

        key, remaining = self.get_next_reminder()
        all_rem = self._get_all_reminders()
        if key and remaining and key in all_rem:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            info = all_rem[key]
            draw_glass_text(painter, 15, 40, text_w, 20, Qt.AlignLeft,
                            f"{info['icon']} {info['name']}  {mins:02d}:{secs:02d}",
                            QFont(FONT_UI, 10), QColor(255, 255, 255, 225))

            total = info["interval"] * 60
            elapsed = total - remaining.total_seconds()
            progress = max(0, min(1, elapsed / total))
            bar_y = 65
            bar_width = self.width() - 30
            painter.setBrush(QColor(255, 255, 255, 55))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(15, bar_y, bar_width, 5, 2, 2)
            painter.setBrush(QColor(255, 255, 255, 190))
            painter.drawRoundedRect(15, bar_y, int(bar_width * progress), 5, 2, 2)

            draw_glass_text(painter, 15, 75, text_w, 15, Qt.AlignLeft,
                            f"已完成 {get_today_stats().get(key, {}).get('completed', 0)} 次",
                            QFont(FONT_UI, 8), QColor(255, 255, 255, 165))
        else:
            draw_glass_text(painter, 15, 45, text_w, 20, Qt.AlignLeft, "暂无活跃提醒",
                            QFont(FONT_UI, 9), QColor(255, 255, 255, 165))

        # 底部操作提示
        draw_glass_text(painter, 15, self.height() - 24, text_w, 15, Qt.AlignLeft,
                        "单击温馨提示 | 双击设置 | 右键菜单",
                        QFont(FONT_UI, 8), QColor(255, 255, 255, 130))

    # ==================== 交互 ====================

    def update_display(self):
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._drag_start_pos = event.globalPos()
            self._is_dragging = False
            self._suppress_click = False  # 每次按下都复位，避免上一次双击残留标记吞掉单击
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            # 判断是否在拖动（移动超过5像素）
            if not self._is_dragging:
                delta = event.globalPos() - self._drag_start_pos
                if abs(delta.x()) > 5 or abs(delta.y()) > 5:
                    self._is_dragging = True
            if self._is_dragging:
                self.move(event.globalPos() - self.drag_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 双击的第二次 release 紧跟在 DoubleClick 之后，
            # 若继续处理会把单击定时器重新拉起来，导致「双击打开设置」的同时又弹出温馨提醒
            if getattr(self, "_suppress_click", False):
                self._suppress_click = False
                event.accept()
                return
            # 只有不是拖动时才触发点击
            if not self._is_dragging:
                # 使用定时器区分单击和双击
                if not hasattr(self, '_click_timer'):
                    self._click_timer = QTimer(self)
                    self._click_timer.setSingleShot(True)
                    self._click_timer.timeout.connect(self._on_single_click)
                    self._click_count = 0
                
                self._click_count += 1
                
                # 如果是第一次点击，启动定时器等待可能的双击
                if self._click_count == 1:
                    self._click_timer.start(250)  # 250ms内如果没有第二次点击，则认为是单击
            event.accept()
        # 右键菜单不在这里手动调用 contextMenuEvent：
        # 窗口的 contextMenuPolicy 是默认值 DefaultContextMenu，Qt 在右键释放时会
        # 自动派发 ContextMenuEvent 并调用 contextMenuEvent()。
        # 这里再调一次会叠出第二个菜单，表现就是「点屏幕其他地方菜单关不掉」。
    

    

    

    
    def _on_single_click(self):
        self._click_count = 0
        # 先收掉上一批，否则连点会叠加出成百上千个窗口
        old_controller = getattr(self, "_warm_tip_controller", None)
        if old_controller is not None:
            old_controller.close_all_windows()
        warm_tip_count = self.config.get("warm_tip_count", 100)
        # mini模式下使用爱心模式
        heart_mode = self.mini_mode
        self._warm_tip_controller = show_warm_tips(
            warm_tip_count, heart_mode=heart_mode, parent=self
        )
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            # 双击打开设置窗口
            self._suppress_click = True  # 抑制紧随其后的第二次 release
            if hasattr(self, '_click_timer'):
                self._click_timer.stop()
                self._click_count = 0
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
        
        # 单击温馨提示
        warm_action = QAction("💝 单击温馨提示", self)
        warm_action.triggered.connect(lambda: self._on_single_click())
        menu.addAction(warm_action)

        # 悬浮球大小（仅迷你模式）
        if self.mini_mode:
            title_action = QAction("⭕ 悬浮球大小", self)
            title_action.setEnabled(False)
            menu.addAction(title_action)

            slider_widget = QWidget()
            slider_widget.setStyleSheet("background: transparent; border: none;")
            sw_lay = QVBoxLayout(slider_widget)
            sw_lay.setContentsMargins(16, 2, 16, 6)
            sw_lay.setSpacing(4)

            self._size_slider = QSlider(Qt.Horizontal)
            self._size_slider.setRange(60, 200)
            self._size_slider.setValue(self.config.get("widget_size", 100))
            self._size_slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 6px; background: rgba(200,180,255,0.15);
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    width: 16px; height: 16px; margin: -5px 0;
                    background: rgba(102,126,234,0.8);
                    border-radius: 8px;
                }
                QSlider::handle:horizontal:hover {
                    background: rgba(102,126,234,1);
                }
            """)

            self._size_spin = QSpinBox()
            self._size_spin.setRange(60, 200)
            self._size_spin.setValue(self.config.get("widget_size", 100))
            self._size_spin.setSuffix(" px")
            self._size_spin.setFixedWidth(80)
            self._size_spin.setAlignment(Qt.AlignCenter)
            self._size_spin.setStyleSheet("""
                QSpinBox {
                    background: rgba(200,180,255,0.1); color: rgba(200,180,255,0.9);
                    border: 1px solid rgba(200,180,255,0.2); border-radius: 6px;
                    font-size: 12px; padding: 2px;
                }
                QSpinBox::up-button, QSpinBox::down-button {
                    width: 16px; border: none;
                }
            """)

            self._size_slider.valueChanged.connect(self._on_slider_change)
            self._size_spin.valueChanged.connect(self._on_spin_change)

            sw_lay.addWidget(self._size_slider)

            spin_row = QHBoxLayout()
            spin_row.addStretch()
            spin_row.addWidget(self._size_spin)
            spin_row.addStretch()
            sw_lay.addLayout(spin_row)

            slider_action = QWidgetAction(self)
            slider_action.setDefaultWidget(slider_widget)
            menu.addAction(slider_action)

        menu.addSeparator()

        # 温馨提醒窗口数量设置
        warm_tip_title = QAction("💝 温馨提醒数量", self)
        warm_tip_title.setEnabled(False)
        menu.addAction(warm_tip_title)
        
        # 创建输入框（编辑后直接保存）
        warm_tip_widget = QWidget()
        warm_tip_widget.setStyleSheet("background: transparent; border: none;")
        warm_tip_layout = QHBoxLayout(warm_tip_widget)
        warm_tip_layout.setContentsMargins(10, 5, 10, 5)
        
        # 数值输入框
        warm_tip_spin = QSpinBox()
        warm_tip_spin.setRange(10, 500)
        warm_tip_spin.setValue(self.config.get("warm_tip_count", 100))
        warm_tip_spin.setSuffix(" 个")
        warm_tip_spin.setFixedWidth(80)
        warm_tip_spin.setStyleSheet("""
            QSpinBox {
                background: rgba(200,180,255,0.1);
                color: rgba(200,180,255,0.9);
                border: 1px solid rgba(200,180,255,0.2);
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }
        """)
        warm_tip_layout.addWidget(warm_tip_spin)
        
        # 编辑完成后直接保存
        def save_warm_tip_count():
            count = warm_tip_spin.value()
            self.config["warm_tip_count"] = count
            save_config(self.config)
        
        warm_tip_spin.editingFinished.connect(save_warm_tip_count)
        
        warm_tip_action = QWidgetAction(self)
        warm_tip_action.setDefaultWidget(warm_tip_widget)
        menu.addAction(warm_tip_action)

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

    def _on_slider_change(self, v):
        self._size_spin.blockSignals(True)
        self._size_spin.setValue(v)
        self._size_spin.blockSignals(False)
        self.set_widget_size(v)

    def _on_spin_change(self, v):
        self._size_slider.blockSignals(True)
        self._size_slider.setValue(v)
        self._size_slider.blockSignals(False)
        self.set_widget_size(v)

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
        icon = QIcon(APP_ICON)

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
        """注册快捷键

        Windows 下优先注册系统级热键（RegisterHotKey + WM_HOTKEY），
        悬浮窗没有焦点时也能响应；某个组合键被其他程序占用时，
        该组合键单独回退为窗口级 QShortcut，保证功能仍然可用。
        """
        hotkeys = [
            ("toggle_pause", "Ctrl+Shift+P", 0x50),      # P
            ("open_settings", "Ctrl+Shift+S", 0x53),     # S
            ("toggle_mini_mode", "Ctrl+Shift+M", 0x4D),  # M
            ("quit_app", "Ctrl+Shift+Q", 0x51),          # Q
        ]

        for hotkey_id, (action, sequence, vk) in enumerate(hotkeys, start=1):
            registered = False
            if IS_WINDOWS:
                try:
                    registered = bool(ctypes.windll.user32.RegisterHotKey(
                        int(self.winId()), hotkey_id,
                        MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT, vk,
                    ))
                except Exception as e:
                    logger.warning("RegisterHotKey failed for %s: %s", action, e)

            if registered:
                self._hotkey_actions[hotkey_id] = action
            else:
                shortcut = QShortcut(QKeySequence(sequence), self)
                shortcut.activated.connect(getattr(self, action))
                self._fallback_shortcuts.append(shortcut)

        logger.info(
            "Global hotkeys: %s | window-level shortcuts: %d",
            list(self._hotkey_actions.values()), len(self._fallback_shortcuts),
        )

    def _unregister_hotkeys(self):
        """注销系统级热键，避免退出后仍占用组合键"""
        for hotkey_id in list(self._hotkey_actions):
            try:
                ctypes.windll.user32.UnregisterHotKey(int(self.winId()), hotkey_id)
            except Exception as e:
                logger.warning("UnregisterHotKey %s failed: %s", hotkey_id, e)
        self._hotkey_actions.clear()

    def nativeEvent(self, eventType, message):
        """接收系统级热键消息（Windows 专有）"""
        if self._hotkey_actions and eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == WM_HOTKEY:
                    action = self._hotkey_actions.get(int(msg.wParam))
                    if action:
                        getattr(self, action)()
                        return True, 0
            except Exception as e:
                logger.warning("Failed to handle hotkey message: %s", e)
        return super().nativeEvent(eventType, message)

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.activateWindow()

    def closeEvent(self, event):
        """忽略关闭事件，防止应用退出"""
        event.ignore()
        self.hide()

    def quit_app(self):
        self._unregister_hotkeys()
        self.tray.hide()
        QApplication.quit()
