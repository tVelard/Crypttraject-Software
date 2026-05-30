# PyInstaller spec for the CryptTraject CLI binary.
#
# Produces a single executable:
#   - crypttraject-cli   (console)
#
# Run from the repo root:
#     pyinstaller packaging/crypttraject.spec --clean --noconfirm
#
# The tricky part is Pyfhel: it ships compiled extension modules
# (.so / .pyd / .dll) that PyInstaller's static analysis can miss.
# `collect_all` walks the installed package and pulls in every data
# file + binary + submodule, which is what we need for SEAL bindings.

# ruff: noqa  # PyInstaller specs are exec'd, not imported.

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# --- Bring in everything Pyfhel needs at runtime ---------------------------
pyfhel_datas, pyfhel_binaries, pyfhel_hidden = collect_all("Pyfhel")

# --- Other libs that occasionally need a nudge -----------------------------
# datasketch uses runtime imports for some hash modules.
datasketch_hidden = collect_submodules("datasketch")

# Pydantic v2 lazy-imports its core C extension.
pydantic_hidden = collect_submodules("pydantic_core")

hiddenimports = list(set(pyfhel_hidden + datasketch_hidden + pydantic_hidden + [
    "pygeohash",
    "numpy",
    "requests",
]))

# ---------------------------------------------------------------------------
# CLI analysis
# ---------------------------------------------------------------------------

a_cli = Analysis(
    ["entry_cli.py"],
    pathex=["../shared", "../client", "../server"],
    binaries=pyfhel_binaries,
    datas=pyfhel_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # The desktop GUI has been removed; never pull Qt into the bundle.
        "PySide6",
        "shiboken6",
        # The server stack is not shipped with the client binary.
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
pyz_cli = PYZ(a_cli.pure, a_cli.zipped_data, cipher=block_cipher)

exe_cli = EXE(
    pyz_cli,
    a_cli.scripts,
    [],
    exclude_binaries=True,
    name="crypttraject-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_cli, a_cli.binaries, a_cli.zipfiles, a_cli.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="crypttraject",
)
