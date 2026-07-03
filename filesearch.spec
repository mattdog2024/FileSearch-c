# -*- coding: utf-8 -*-
"""PyInstaller spec file"""
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Use collect_all to get ALL jieba files (code + data + dicts)
jieba_datas, jieba_binaries, jieba_hiddenimports = collect_all('jieba')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=jieba_binaries,
    datas=[
        ('core', 'core'),
        ('ui', 'ui'),
        ('icon.ico', '.'),
    ] + jieba_datas,
    hiddenimports=[
        'jieba',
        'jieba.finalseg',
        'jieba._compat',
        'jieba.probability',
        'pdfplumber',
        'pdfminer',
        'pdfminer.six',
        'openpyxl',
        'docx',
        'pptx',
        'olefile',
        'chardet',
        'PyPDF2',
    ] + jieba_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FileSearch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # no console window
    icon='icon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
