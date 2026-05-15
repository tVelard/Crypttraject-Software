"""Cross-platform build driver for CryptTraject client binaries.

Run from the repo root:

    python packaging/build_binaries.py

What it does:
  1. sanity-check PyInstaller + Pyfhel are importable in the current env
  2. clean previous build/ and dist/ directories
  3. run PyInstaller on packaging/crypttraject.spec
  4. zip the produced dist/crypttraject/ folder into a
     CryptTraject-<os>-<arch>.zip alongside it

PyInstaller cannot cross-compile, so this must be run once per target
OS. The GitHub Actions workflow in .github/workflows/release.yml runs
this script on Linux, Windows, and macOS runners.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "packaging" / "crypttraject.spec"


def fail(msg: str) -> "NoReturn":
    print(f"[build] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def check_environment() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        fail("PyInstaller is not installed. Run: pip install pyinstaller")

    try:
        import Pyfhel  # noqa: F401
    except ImportError:
        fail(
            "Pyfhel is not installed in this environment. "
            "Pyfhel must be importable so PyInstaller can find its "
            "native SEAL extensions. Run: pip install Pyfhel"
        )

    try:
        import PySide6  # noqa: F401
    except ImportError:
        fail("PySide6 is not installed (needed for the GUI bundle).")

    print(f"[build] python   : {sys.version.split()[0]}")
    print(f"[build] platform : {platform.system()} {platform.machine()}")


def clean() -> None:
    for d in ("build", "dist"):
        path = ROOT / d
        if path.exists():
            print(f"[build] removing {d}/")
            shutil.rmtree(path)


def run_pyinstaller() -> None:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC),
        "--clean",
        "--noconfirm",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
    ]
    print("[build] $ " + " ".join(cmd))
    # cwd = packaging/ so relative pathex entries in the spec resolve correctly.
    subprocess.check_call(cmd, cwd=str(ROOT / "packaging"))


def make_archive() -> Path:
    """Zip dist/crypttraject/ into dist/CryptTraject-<os>-<arch>.zip."""
    src = ROOT / "dist" / "crypttraject"
    if not src.exists():
        fail(f"expected build output not found: {src}")

    arch = platform.machine().lower().replace("amd64", "x86_64")
    os_tag = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(
        platform.system(), platform.system().lower()
    )
    archive = ROOT / "dist" / f"CryptTraject-{os_tag}-{arch}.zip"

    print(f"[build] zipping {src.name}/ -> {archive.name}")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            zf.write(f, arcname=f.relative_to(src.parent))
    return archive


def main() -> int:
    check_environment()
    clean()
    run_pyinstaller()
    archive = make_archive()
    size_mb = archive.stat().st_size / (1024 * 1024)
    print(f"[build] DONE — {archive} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
