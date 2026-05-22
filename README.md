# Health-reminder

桌面健康提醒悬浮窗应用，帮你养成定时护眼、休息、喝水的好习惯。

基于 Python + PyQt5 开发，支持系统托盘、迷你模式、贪睡、勿扰、自定义提醒等功能。

## 功能特性

**内置提醒**
- 护眼提醒 —— 定时提醒远眺，缓解眼部疲劳
- 休息提醒 —— 定时提醒起身活动
- 喝水提醒 —— 定时提醒补充水分

**自定义提醒**
- 自由添加个性化提醒（吃药、站立、冥想等）
- 20+ 可选图标
- 独立设置间隔时间

**交互方式**
- 悬浮窗可拖拽，支持迷你模式和完整模式
- 迷你模式带进度环动画，图标会"眨眼"
- 弹窗提醒支持贪睡（延迟 5 分钟再次提醒）
- 系统托盘驻留，最小化后继续运行
- 全局快捷键

**其他**
- 勿扰模式 —— 设置免打扰时段
- 提示音 —— 不同提醒类型有不同音效
- 今日统计 —— 记录每天的提醒触发和完成次数

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+Shift+P` | 暂停/继续提醒 |
| `Ctrl+Shift+S` | 打开设置 |
| `Ctrl+Shift+M` | 切换迷你/完整模式 |
| `Ctrl+Shift+Q` | 退出程序 |

## 安装

### 方式一：直接运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 方式二：打包为 exe

```bash
pip install pyinstaller
pyinstaller 健康提醒.spec
```

打包完成后在 `dist/` 目录下生成可执行文件。

## 依赖

- PyQt5 >= 5.15.0
- plyer >= 2.1.0

Windows 系统额外使用 `winsound` 模块播放提示音（Python 内置，无需安装）。

## 配置说明

程序启动后会自动创建 `config.json`，也可手动编辑：

```json
{
  "eye_care": {"enabled": true, "interval": 20},
  "rest": {"enabled": true, "interval": 45},
  "water": {"enabled": true, "interval": 30},
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
  "widget_size": 80
}
```

| 字段 | 说明 |
|------|------|
| `eye_care/rest/water` | 内置提醒开关和间隔（分钟） |
| `sound` | 是否播放提示音 |
| `custom` | 自定义提醒列表 |
| `dnd_enabled` | 勿扰模式开关 |
| `dnd_start/dnd_end` | 勿扰时段（24小时制） |
| `mini_mode` | 启动时是否为迷你模式 |
| `widget_size` | 迷你模式悬浮球大小（60-200） |

## 使用方式

1. 启动后桌面右侧出现悬浮窗，显示最近一次提醒的倒计时
2. **左键拖拽**移动位置
3. **双击**打开设置面板
4. **右键**打开菜单（暂停、切换模式、勿扰、统计、设置、退出）
5. 迷你模式下可拖动滑条调整悬浮球大小
6. 提醒触发时弹出渐变弹窗，可点击关闭或贪睡
