# -*- mode: python ; coding: utf-8 -*-
# 说明：
#   main.py 在运行时才把 src/ 插入 sys.path，PyInstaller 静态分析找不到
#   constants / utils / ui（build/健康提醒/warn-*.txt 中会看到它们被标为 missing module），
#   所以这里用 datas 把 src/ 源码一并放进包内。
#   可写数据目录由 constants.DATA_ROOT 决定：打包后取 exe 所在目录，
#   而不是 PyInstaller 的临时解压目录，否则配置与统计重启即丢。


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets'), ('src', 'src')],
    # 标准库会被自动分析收录，这里只保留分析不到的第三方模块与 Windows 专属模块
    hiddenimports=['plyer', 'winreg', 'winsound'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='健康提醒',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app_icon.ico'],
)
