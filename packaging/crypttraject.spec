# PyInstaller spec for the CryptTraject desktop application.
#
# Produces a windowed GUI executable:
#   - CryptTraject.exe   (PySide6 / Qt, no console)
#
# Run from the repo root:
#     pyinstaller packaging/crypttraject.spec --clean --noconfirm
#
# Two tricky dependencies:
#   * Pyfhel ships compiled SEAL extensions (.pyd/.dll) that static
#     analysis can miss — collect_all walks the package and pulls them in.
#   * PySide6 QtWebEngine bundles a Chromium runtime (QtWebEngineProcess,
#     .pak resources, ICU data, locales). collect_all("PySide6") embeds
#     those so the Leaflet map renders on a machine with nothing installed.
#     This is what makes the bundle large (~150 MB) and Windows-only here.

# ruff: noqa  # PyInstaller specs are exec'd, not imported.

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# --- Bring in everything Pyfhel needs at runtime ---------------------------
pyfhel_datas, pyfhel_binaries, pyfhel_hidden = collect_all("Pyfhel")

# --- PySide6 + Qt WebEngine (Chromium) -------------------------------------
pyside_datas, pyside_binaries, pyside_hidden = collect_all("PySide6")

# --- Other libs that occasionally need a nudge -----------------------------
# datasketch uses runtime imports for some hash modules.
datasketch_hidden = collect_submodules("datasketch")

# Pydantic v2 lazy-imports its core C extension.
pydantic_hidden = collect_submodules("pydantic_core")

hiddenimports = list(set(
    pyfhel_hidden + pyside_hidden + datasketch_hidden + pydantic_hidden + [
        "pygeohash",
        "numpy",
        "requests",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineCore",
    ]
))

# ---------------------------------------------------------------------------
# GUI analysis
# ---------------------------------------------------------------------------

a_gui = Analysis(
    ["entry_gui.py"],
    pathex=["../shared", "../client", "../server"],
    binaries=pyfhel_binaries + pyside_binaries,
    datas=pyfhel_datas + pyside_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # The server stack is not shipped with the desktop client.
        "fastapi",
        "uvicorn",
        "starlette",
        "crypttraject_server",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz_gui = PYZ(a_gui.pure, a_gui.zipped_data, cipher=block_cipher)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="CryptTraject",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # windowed app, no console
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_gui, a_gui.binaries, a_gui.zipfiles, a_gui.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="crypttraject",
)
