"""Build driver for the CryptTraject desktop-app Windows installer.

Run from the repo root:

    python packaging/build_binaries.py

What it does:
  1. sanity-check PyInstaller + Pyfhel + PySide6 are importable in the env
  2. clean previous build/ and dist/ directories
  3. run PyInstaller on packaging/crypttraject.spec (windowed GUI app)
  4. on Windows: compile packaging/installer.iss with Inno Setup (ISCC)
     into dist/CryptTraject-Setup.exe — a one-click installer that drops
     the app in Program Files with Start Menu / desktop shortcuts and
     nothing else to install.
     On other OSes: fall back to zipping dist/crypttraject/ for dev use.

PyInstaller cannot cross-compile and the installer targets Windows, so the
release build runs on a Windows runner (see .github/workflows/release.yml).
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
ISS = ROOT / "packaging" / "installer.iss"

# Keep in sync with pyproject.toml [project].version.
APP_VERSION = "0.1.0"


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
        fail(
            "PySide6 is not installed in this environment. "
            "The desktop app and its Qt WebEngine map need it. "
            "Run: pip install PySide6"
        )

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


def find_iscc() -> str | None:
    """Locate the Inno Setup command-line compiler (ISCC.exe)."""
    found = shutil.which("ISCC")
    if found:
        return found
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Inno Setup 6" / "ISCC.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def build_installer() -> Path:
    """Compile the Inno Setup installer into dist/CryptTraject-Setup.exe."""
    src = ROOT / "dist" / "crypttraject"
    if not src.exists():
        fail(f"expected PyInstaller output not found: {src}")

    iscc = find_iscc()
    if iscc is None:
        fail(
            "Inno Setup compiler (ISCC.exe) not found. Install Inno Setup 6 "
            "(https://jrsoftware.org/isdl.php) or, in CI, use the "
            "'innosetup' chocolatey package."
        )

    cmd = [iscc, f"/DAppVersion={APP_VERSION}", str(ISS)]
    print("[build] $ " + " ".join(cmd))
    subprocess.check_call(cmd, cwd=str(ROOT / "packaging"))

    out = ROOT / "dist" / "CryptTraject-Setup.exe"
    if not out.exists():
        fail(f"installer was not produced: {out}")
    return out


def make_zip() -> Path:
    """Fallback for non-Windows: zip dist/crypttraject/ for dev use."""
    src = ROOT / "dist" / "crypttraject"
    if not src.exists():
        fail(f"expected build output not found: {src}")

    arch = platform.machine().lower().replace("amd64", "x86_64")
    os_tag = {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}.get(
        platform.system(), platform.system().lower()
    )
    archive = ROOT / "dist" / f"CryptTraject-cli-{os_tag}-{arch}.zip"

    print(f"[build] zipping {src.name}/ -> {archive.name}")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            zf.write(f, arcname=f.relative_to(src.parent))
    return archive


def main() -> int:
    check_environment()
    clean()
    run_pyinstaller()

    if platform.system() == "Windows":
        out = build_installer()
    else:
        # The product ships a Windows installer only; other platforms get a
        # plain zip so developers can still run the CLI locally.
        out = make_zip()

    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"[build] DONE — {out} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
