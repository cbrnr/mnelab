# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('mne')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('mnelab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sklearn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('mne_qt_browser')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['../src/mnelab/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='MNELAB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['../src/mnelab/icons/mnelab-macos.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='MNELAB',
)
app = BUNDLE(
    coll,
    name='MNELAB.app',
    icon='../src/mnelab/icons/mnelab-macos.icns',
    bundle_identifier=None,
    info_plist={
        "CFBundleIconName": "mnelab",
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "EDF File",
                "CFBundleTypeExtensions": ["edf"],
                "LSItemContentTypes": ["public.data"],
                "CFBundleTypeRole": "Editor"
            },
            {
                "CFBundleTypeName": "BDF File",
                "CFBundleTypeExtensions": ["bdf"],
                "LSItemContentTypes": ["public.data"],
                "CFBundleTypeRole": "Editor"
            },
            {
                "CFBundleTypeName": "XDF File",
                "CFBundleTypeExtensions": ["xdf"],
                "LSItemContentTypes": ["public.data"],
                "CFBundleTypeRole": "Editor"
            }
        ]
    }
)
