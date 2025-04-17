# -*- mode: python ; coding: utf-8 -*-

import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringTable,
    StringStruct,
    VarFileInfo,
    VarStruct
)

block_cipher = None

a = Analysis(
    ['SoftWare.py'],
    pathex=[],
    binaries=[],
    datas=[('res\\gear_icon-70125.ico', 'res')],
    hiddenimports=["pygame", "pillow", "os", "io", "tempfile"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

version = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 0, 0, 0),
        prodvers=(1, 0, 0, 0),
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([
            StringTable(
                u'040904B0',
                [
                    StringStruct(u'CompanyName', u'ThreeGuysTeam'),
                    StringStruct(u'FileDescription', u'PyroForgeDataViewer-SoftWare'),
                    StringStruct(u'FileVersion', u'1.0.0.0'),
                    StringStruct(u'InternalName', u'PyroForgeDataViewer'),
                    StringStruct(u'LegalCopyright', u''),
                    StringStruct(u'OriginalFilename', u'PyroForgeDataViewer.exe'),
                    StringStruct(u'ProductName', u'PyroForgeDataViewer'),
                    StringStruct(u'ProductVersion', u'1.0.0.0')
                ]
            )
        ]),
        VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
    ]
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PFDataViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    version=version,
    icon="res\\gear_icon-70125.ico"  # Specify the icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PFDataViewer',
    outdir='build\libs'
)