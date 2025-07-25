# -*- mode: python ; coding: utf-8 -*-

from kivy_deps import sdl2, glew

block_cipher = None

a = Analysis(
    ['snapsend.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('fonts/K2D-Bold.ttf', 'fonts'),
        ('fonts/K2D-Light.ttf', 'fonts'),
        ('fonts/K2D-ExtraBold.ttf', 'fonts'),  # Add the missing font
        ('fonts/K2D-ExtraLight.ttf', 'fonts'),  # Add this
        ('back.png', '.'),
        ('settings_icon.png', '.'),
        ('logo.svg', '.'),
        ('snapsend.kv', '.'),
    ],
    hiddenimports=[
        'kivy',
        'PIL',
        'win32timezone',
    ],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    [],
    name='SnapSend',
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
)