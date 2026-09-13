#!/usr/bin/env python3
"""Build standalone ds2fix binaries (CLI + GUI) with PyInstaller.

Run on the target OS to produce that OS's binaries (PyInstaller does not cross-compile). Outputs carry the
platform in their name so the release assets are unambiguous:
  Linux   -> dist/ds2fix_linux          + dist/ds2fix-gui_linux
  Windows -> dist\\ds2fix_windows.exe    + dist\\ds2fix-gui_windows.exe

Usage:  python build.py            (needs `pip install pyinstaller` — or use CI, see .github/workflows)
"""
import os, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HIDDEN = ["ds2fix", "ds2fix_core", "ds2fix_core.exe_patch", "ds2fix_core.tank"]


def run(entry, name, windowed):
    cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--noconfirm", "--clean",
           "--name", name, "--paths", str(ROOT), "--distpath", str(ROOT / "dist")]
    for h in HIDDEN:
        cmd += ["--hidden-import", h]
    if windowed:
        cmd.append("--windowed")
    cmd.append(str(ROOT / entry))
    print("::", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def main():
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        sys.exit("PyInstaller not found. Install it first:  pip install pyinstaller")
    suffix = "_windows" if os.name == "nt" else "_linux"
    run("ds2fix.py", "ds2fix" + suffix, windowed=False)          # CLI (console)
    run("ds2fix_gui.py", "ds2fix-gui" + suffix, windowed=True)   # GUI (no console window)
    # tidy PyInstaller scratch
    for d in ("build",):
        shutil.rmtree(ROOT / d, ignore_errors=True)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()
    print("\nBuilt:", ", ".join(p.name for p in (ROOT / "dist").iterdir()))


if __name__ == "__main__":
    main()
