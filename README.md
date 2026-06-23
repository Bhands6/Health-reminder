# 💚 健康提醒助手 (Health Reminder)

一款桌面健康提醒悬浮窗应用，帮你养成定时护眼、休息、喝水的好习惯。

基于 Python + PyQt5 开发，支持系统托盘、迷你模式、贪睡、勿扰、自定义提醒、温馨提醒等功能。

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![PyQt5](https://img.shields.io/badge/PyQt5-5.15+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 功能特性

### 📋 内置提醒

| 提醒类型 | 图标 | 默认间隔 | 说明 |
|---------|------|---------|------|
| 护眼提醒 | 👀 | 20 分钟 | 定时提醒远眺，缓解眼部疲劳 |
| 休息提醒 | 🧘 | 45 分钟 | 定时提醒起身活动 |
| 喝水提醒 | 💧 | 30 分钟 | 定时提醒补充水分 |

### ➕ 自定义提醒

- 自由添加个性化提醒（吃药、站立、冥想等）
- 21+ 可选图标（☕🍎🎵💪🏃🙏💊🌸⭐🎯📝🕐🌿🥤🧘🔔⏰📌💡🎉❤️）
- 独立设置间隔时间和开关

### 🖱️ 悬浮窗交互

| 操作 | 效果 |
|------|------|
| **单击** | 显示温馨提醒（迷你模式下爱心形状排列，完整模式下随机排列） |
| **双击** | 打开设置面板 |
| **右键** | 打开上下文菜单 |
| **拖拽** | 移动悬浮球位置 |
| **滚轮** | 调整悬浮球大小（迷你模式） |

### 🔔 弹窗提醒

- 渐变背景 + 动画淡入淡出
- 支持贪睡（延迟 5 分钟再提醒）
- 7 种弹窗位置可选（居中/左上/右上/左下/右下/中上/中下）
- 自动关闭（5 秒后）

### 💕 温馨提醒

- 点击悬浮球显示大量随机温馨提醒窗口
- **迷你模式**：窗口按爱心形状排列 🫶
- **完整模式**：窗口随机散布在屏幕上
- 支持自定义弹窗数量（10-500）
- 控制窗口显示提示信息，按空格键关闭所有窗口
- 窗口带有淡入淡出动画效果

### 🎨 主题与外观

- 亮色/暗色模式切换
- 自定义渐变颜色（起始色/结束色）
- 设置页面跟随主题色变化
- 半透明毛玻璃效果

### ⚙️ 其他功能

- **勿扰模式** — 设置免打扰时段，迷你模式下显示 💤 空闲状态
- **提示音** — 不同提醒类型有不同音效（Windows）
- **今日统计** — 记录每天的提醒触发和完成次数
- **开机自启动** — 支持 Windows 注册表自启动
- **系统托盘** — 最小化后驻留托盘，后台运行

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+P` | 暂停/继续提醒 |
| `Ctrl+Shift+S` | 打开设置 |
| `Ctrl+Shift+M` | 切换迷你/完整模式 |
| `Ctrl+Shift+Q` | 退出程序 |

## 项目结构

```
health-reminder/
├── main.py                  # 程序入口
├── README.md                # 项目说明文档
├── requirements.txt         # Python 依赖
├── .gitignore               # Git 忽略配置
├── LICENSE                  # MIT 许可证
├── 健康提醒.spec             # PyInstaller 打包配置
├── Health_Icon .png         # 应用图标源文件
├── assets/                  # 资源文件
│   ├── app_icon.ico         # 应用图标
│   ├── checkmark.png        # 勾选图标（自动生成）
│   ├── arrow_up.svg         # 上箭头图标（自动生成）
│   └── arrow_down.svg       # 下箭头图标（自动生成）
├── data/                    # 运行时数据
│   ├── config.json          # 用户配置文件（自动生成）
│   └── stats.json           # 统计数据（自动生成）
├── logs/                    # 日志目录
│   └── health-reminder.log  # 应用日志
└── src/                     # 源代码
    ├── constants.py         # 常量定义（主题、颜色、内置提醒配置）
    ├── utils.py             # 工具函数（配置读写、统计、自启动、提示音）
    └── ui/                  # UI 模块
        ├── __init__.py
        ├── floating_widget.py   # 悬浮窗主组件（拖拽、托盘、菜单）
        ├── settings.py          # 设置面板（卡片式布局）
        ├── popup.py             # 提醒弹窗（渐变背景、贪睡）
        ├── warm_tips.py         # 温馨提醒（爱心排列 + 随机散布）
        └── widgets.py           # 自定义控件（开关、进度环、Tooltip）
```

## 安装与运行

### 环境要求

- Python 3.8+
- Windows 10/11（macOS 基本支持）

### 方式一：直接运行

```bash
# 克隆仓库
git clone https://github.com/Bhands6/Health-reminder.git
cd Health-reminder

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 方式二：打包为 exe

```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller 健康提醒.spec
```

打包完成后在 `dist/` 目录下生成 `健康提醒.exe`。

## 依赖

| 依赖包 | 版本 | 用途 |
|--------|------|------|
| PyQt5 | >= 5.15.0 | GUI 框架 |
| plyer | >= 2.1.0 | 系统通知（跨平台） |

> Windows 系统额外使用 `winsound` 模块播放提示音（Python 内置，无需安装）。

## 配置说明

程序首次运行会自动创建 `data/config.json`，也可手动编辑：

```json
{
  "eye_care": { "enabled": true, "interval": 20 },
  "rest": { "enabled": true, "interval": 45 },
  "water": { "enabled": true, "interval": 30 },
  "sound": true,
  "auto_start": false,
  "custom": [
    {
      "name": "喝咖啡",
      "icon": "☕",
      "message": "该喝咖啡了",
      "interval": 1,
      "enabled": false
    }
  ],
  "dnd_enabled": false,
  "dnd_start": "22:00",
  "dnd_end": "08:00",
  "mini_mode": false,
  "widget_size": 100,
  "theme": "light",
  "gradient_start": null,
  "gradient_end": null,
  "popup_position": "center",
  "warm_tip_count": 100
}
```

### 字段说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `eye_care/rest/water` | object | — | 内置提醒开关和间隔（分钟，1-480） |
| `sound` | bool | `true` | 是否播放提示音 |
| `auto_start` | bool | `false` | 开机自启动 |
| `custom` | array | `[]` | 自定义提醒列表 |
| `dnd_enabled` | bool | `false` | 勿扰模式开关 |
| `dnd_start/dnd_end` | string | `"22:00"`/`"08:00"` | 勿扰时段（HH:MM，24小时制） |
| `mini_mode` | bool | `false` | 迷你模式（悬浮球样式） |
| `widget_size` | int | `100` | 悬浮球大小（60-200） |
| `theme` | string | `"light"` | 主题模式（`light`/`dark`） |
| `gradient_start/end` | array/null | `null` | 自定义渐变颜色 RGB，如 `[102,126,234]` |
| `popup_position` | string | `"center"` | 弹窗位置 |
| `warm_tip_count` | int | `100` | 温馨提醒弹窗数量（10-500） |

## 使用方式

1. 启动后桌面右上侧出现悬浮窗
2. **单击** → 显示温馨提醒窗口
3. **双击** → 打开设置面板
4. **右键** → 打开菜单（暂停/切换模式/温馨提醒/统计/设置/退出）
5. **拖拽** → 移动位置
6. 提醒触发时弹出渐变弹窗，可点击「知道了」关闭或「延迟 5 分钟」贪睡
7. 右键菜单中可设置温馨提醒窗口数量（10-500）

## 作者

**Bhands** · v3.0

GitHub: [Bhands6/Health-reminder](https://github.com/Bhands6/Health-reminder)
