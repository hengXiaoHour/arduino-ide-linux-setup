#!/usr/bin/env python3
"""
Arduino IDE 2.x Linux Installer

A complete setup script that installs the Arduino IDE AppImage properly
with desktop integration (icon, menu entry, pin-to-favorites).

Usage:
    python install_arduino_ide.py
    python install_arduino_ide.py path/to/arduino-ide_*.AppImage
    python install_arduino_ide.py --uninstall

What this solves:
  - FUSE dependency: Extracts the AppImage so it works without libfuse2
  - Missing icon: Extracts the official 512x512 icon from the AppImage
  - Clicking does nothing: Makes the .desktop file executable (+x)
  - Broken system icons: NEVER installs to ~/.local/share/icons/hicolor/
    (that shadows the system theme and breaks ALL app icons)
  - StartupWMClass: Ensures dock pinning works (no duplicate icons)
  - Quoted Exec path: Handles spaces in paths correctly
  - LD_LIBRARY_PATH: Sets up bundled libraries for the Electron app
"""

import shutil
import stat
import subprocess
import sys
import urllib.request
import json
from pathlib import Path

APP_DIR_NAME = "arduino-ide"
DESKTOP_FILE_NAME = "arduino-ide.desktop"
WRAPPER_NAME = "arduino-ide.sh"
ICON_NAME = "arduino-ide.png"


def main():
    home = Path.home()
    apps_dir = home / "apps" / APP_DIR_NAME
    desktop_dir = home / ".local" / "share" / "applications"

    if "--uninstall" in sys.argv:
        uninstall(apps_dir, desktop_dir)
        return

    print("Arduino IDE 2.x Linux Installer")
    print("=" * 40)

    appimage_path = resolve_appimage()
    if not appimage_path:
        answer = input("No AppImage found. Download from arduino.cc? [Y/n]: ").strip().lower()
        if answer not in ("", "y", "yes"):
            print("Download it manually from https://www.arduino.cc/en/software")
            sys.exit(1)
        appimage_path = download_appimage()
        if not appimage_path:
            print("Download failed.")
            sys.exit(1)

    print(f"\n[1/6] Installing AppImage -> {apps_dir}")
    apps_dir.mkdir(parents=True, exist_ok=True)
    dest_appimage = apps_dir / appimage_path.name
    if appimage_path.resolve() != dest_appimage.resolve():
        shutil.copy2(str(appimage_path), str(dest_appimage))
    dest_appimage.chmod(dest_appimage.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"[2/6] Extracting (no FUSE needed)...")
    extract_dir = apps_dir / "extracted"
    if extract_dir.exists():
        shutil.rmtree(str(extract_dir))
    subprocess.run(
        [str(dest_appimage), "--appimage-extract"],
        cwd=str(apps_dir),
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    squashfs = apps_dir / "squashfs-root"
    if squashfs.exists():
        squashfs.rename(extract_dir)

    print(f"[3/6] Extracting official icon...")
    icon_source = extract_dir / "usr/share/icons/hicolor/512x512/apps/arduino-ide.png"
    if icon_source.exists():
        shutil.copy2(str(icon_source), str(apps_dir / ICON_NAME))
    else:
        print("  Warning: icon not found (will use fallback)")

    print(f"[4/6] Creating launcher wrapper...")
    wrapper = apps_dir / WRAPPER_NAME
    appimage_name = dest_appimage.name
    wrapper.write_text(f"""#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"
APPIMAGE="${{HERE}}/{appimage_name}"
EXTRACTED="${{HERE}}/extracted/arduino-ide"

if [ -x "${{EXTRACTED}}" ]; then
    export LD_LIBRARY_PATH="${{HERE}}/extracted/usr/lib:${{LD_LIBRARY_PATH}}"
    export PATH="${{HERE}}/extracted:${{PATH}}"
    exec "${{EXTRACTED}}" --no-sandbox "$@"
elif [ -x "${{APPIMAGE}}" ]; then
    exec "${{APPIMAGE}}" --appimage-extract-and-run --no-sandbox "$@"
else
    echo "Arduino IDE not found. Re-run the installer."
    exit 1
fi
""")
    wrapper.chmod(0o755)

    print(f"[5/6] Creating desktop entry...")
    desktop_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = desktop_dir / DESKTOP_FILE_NAME
    desktop_file.write_text(f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Arduino IDE
Comment=Open-source electronics prototyping platform
TryExec={wrapper}
Exec={wrapper} %U
Icon={apps_dir / ICON_NAME}
Terminal=false
StartupWMClass=Arduino IDE
Categories=Development;IDE;Electronics;
""")
    desktop_file.chmod(0o755)

    print(f"[6/6] Validating...")
    result = subprocess.run(
        ["desktop-file-validate", str(desktop_file)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  Validation failed: {result.stderr.strip()}")
        sys.exit(1)

    subprocess.run(
        ["update-desktop-database", str(desktop_dir)],
        stderr=subprocess.DEVNULL,
    )

    print()
    print("Arduino IDE installed successfully!")
    print(f"  App:      {apps_dir}")
    print(f"  Launcher: {desktop_file}")
    print()
    print("Search 'Arduino IDE' in your app menu and pin to favorites.")
    print("If the icon doesn't appear, press Alt+F2, type 'r', and press Enter.\n")


def uninstall(apps_dir, desktop_dir):
    print("Uninstalling Arduino IDE...")
    desktop_file = desktop_dir / DESKTOP_FILE_NAME
    if desktop_file.exists():
        desktop_file.unlink()
        subprocess.run(["update-desktop-database", str(desktop_dir)], stderr=subprocess.DEVNULL)
        print(f"  Removed: {desktop_file}")
    if apps_dir.exists():
        shutil.rmtree(str(apps_dir))
        print(f"  Removed: {apps_dir}")
    print("Done.")


def resolve_appimage():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        p = Path(sys.argv[1])
        if p.exists():
            return p
        print(f"File not found: {p}")
        sys.exit(1)

    downloads = Path.home() / "Downloads"
    for pattern in ("arduino-ide_*.AppImage", "arduino-ide*.AppImage"):
        candidates = sorted(downloads.glob(pattern), reverse=True)
        if candidates:
            return candidates[0]
    return None


def download_appimage():
    print("\nFetching latest release info from GitHub...")
    try:
        req = urllib.request.Request(
            "https://api.github.com/repos/arduino/arduino-ide/releases/latest",
            headers={"User-Agent": "arduino-ide-installer/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        version = data["tag_name"]
        assets = data.get("assets", [])

        appimage_url = None
        for a in assets:
            name = a["name"]
            if "Linux_64bit.AppImage" in name:
                appimage_url = a["browser_download_url"]
                break

        if not appimage_url:
            print("  No Linux AppImage found in latest release.")
            return None

        dest = Path.home() / "Downloads" / appimage_url.split("/")[-1]
        print(f"  Downloading Arduino IDE {version} ({dest.name})...")
        print(f"  URL: {appimage_url}")
        print("  This may take a few minutes...")

        urllib.request.urlretrieve(appimage_url, dest)
        print(f"  Downloaded: {dest}")
        return dest

    except Exception as e:
        print(f"  Download failed: {e}")
        return None


if __name__ == "__main__":
    main()
