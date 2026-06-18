# -*- mode: python ; coding: utf-8 -*-
# Mac 版 spec 文件 — 在 macOS 上运行: pyinstaller health-reminder-mac.spec

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('arrow_down.svg', '.'),
        ('arrow_up.svg', '.'),
        ('checkmark.png', '.'),
        ('app_icon.icns', '.'),
    ],
    hiddenimports=['plyer.platforms.macosx.notification'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['winsound', 'winreg'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='健康提醒',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='健康提醒',
)

app = BUNDLE(
    coll,
    name='健康提醒.app',
    icon='app_icon.icns',
    bundle_identifier='com.health-reminder.app',
    info_plist={
        'CFBundleDisplayName': '健康提醒',
        'CFBundleName': '健康提醒',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,  # 后台运行，不在 Dock 显示
    },
)
