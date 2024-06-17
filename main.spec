# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
block_cipher = None
tmp_ret = collect_all('tkinterweb')
hiddenimports=['zeroconf._utils.ipaddress',
        'zeroconf._handlers.answers',
        'tkinterweb',
        'os',
        'json',
        're',
        'sys',
        'argparse',
        'subprocess',
        'functools',
        'datetime',
        'platform',
        'http.server',
        'socketserver',
        'socket',
        'signal',
        'logging',
        'threading',
        'tkinter',
        'PIL.Image',
        'PIL.ImageTk',
        'customtkinter',
        'ncclient',
        'ncclient.transport.errors',
        'ncclient.xml_',
        'lxml.etree',
        'setuptools_scm',
        'markdown',
        'psutil',
        'zeroconf.ServiceBrowser',
        'zeroconf.Zeroconf',
        'tkinterweb.HtmlFrame'
        ]

datas=[
        ('version.txt', '.'),
        ('disable-profinet.xml', '.'),
        ('enable-profinet.xml', '.'),
        ('icons/open.png', 'icons'),
        ('icons/save.png', 'icons'),
        ('icons/close.png', 'icons'),
        ('icons/transparent.png', 'icons'),
        ('usage.md', '.')
    ]
binaries=[]
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
