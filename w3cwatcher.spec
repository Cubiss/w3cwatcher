# w3cwatcher.spec
block_cipher = None

a = Analysis(
    ['run_tray.pyw'],
    pathex=['.'],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='W3CWatcher',
    console=False
)
