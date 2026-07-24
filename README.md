# Arduino IDE 2.x — One-command Full Linux Install

**One paste. Downloads, installs, adds icon to menu. Done.**

The Arduino IDE for Linux ships as an AppImage. Double-clicking works, but getting it into your app menu with the proper icon is a nightmare. Existing guides copy icons into `~/.local/share/icons/hicolor/`, which **shadows the system icon theme and breaks every other app icon** (Brave, Chrome, Telegram — all go blurry or disappear).

This script is a **complete installer** — not just an icon fixer. It downloads the latest Arduino IDE, extracts it (no FUSE needed), extracts the official icon, and creates a working desktop entry. One command, zero effort.

## One-liner (full install)

```bash
curl -LO https://raw.githubusercontent.com/hengXiaoHour/arduino-ide-linux-setup/master/install_arduino_ide.py && python3 install_arduino_ide.py
```

That single command: **downloads the IDE → installs it → adds the icon → creates the menu entry**. You're done.

## The Problems It Solves

| Problem | Cause | Fix |
|---|---|---|
| **Clicking the icon does nothing** | `.desktop` file missing execute permission | `chmod 755` on the desktop entry |
| **No icon / generic gear icon** | AppImage carries the icon inside, nobody extracts it | Extracts the official 512x512 icon from the AppImage |
| **"AppImages require FUSE"** | `libfuse2` not installed on Ubuntu 24.04+ | Extracts the AppImage permanently — no FUSE needed |
| **All other app icons go blurry / broken** | Many guides install icons to `~/.local/share/icons/hicolor/`, which shadows the system-wide hicolor theme | Icons are referenced by **absolute path** — no icon theme modification |
| **Duplicate dock icons** | Missing `StartupWMClass` in `.desktop` file | Sets `StartupWMClass=Arduino IDE` so the window groups with its dock icon |
| **"No such file or directory" on paths with spaces** | `Exec` line not quoted | Double-quotes the `Exec` path |
| **Chromium sandbox errors** | Missing `--no-sandbox` flag | Passes `--no-sandbox` |
| **Bundled libraries not found** | Missing `LD_LIBRARY_PATH` | Sets `LD_LIBRARY_PATH` to the AppImage's bundled `usr/lib` |

## Usage

```bash
# Auto-download + install everything
python install_arduino_ide.py

# Or specify the path manually (skip download)
python install_arduino_ide.py ~/Downloads/arduino-ide_*.AppImage

# Remove everything
python install_arduino_ide.py --uninstall
```

After installation, search **"Arduino IDE"** in your app menu and pin to favorites. If the icon doesn't appear immediately, press **Alt+F2**, type `r`, and press Enter (restarts GNOME Shell).

## How It Works

1. **Copies** the AppImage to `~/apps/arduino-ide/`
2. **Extracts** it with `--appimage-extract` (no FUSE, works on any Linux)
3. **Extracts** the official 512x512 icon to `~/apps/arduino-ide/arduino-ide.png`
4. **Creates** a wrapper script (`arduino-ide.sh`) that sets `LD_LIBRARY_PATH` and falls back to `--appimage-extract-and-run` if the extracted dir is missing
5. **Creates** `~/.local/share/applications/arduino-ide.desktop` with:
   - `Exec` path quoted
   - `Icon` as absolute path (no icon theme modification)
   - `StartupWMClass=Arduino IDE`
   - `--no-sandbox` flag
   - File is `chmod 755`
6. **Validates** the desktop entry with `desktop-file-validate`

## Serial Port Access

If your board is detected but you can't upload or open the serial monitor:

```bash
sudo usermod -aG dialout $USER
```

Then **log out and log back in**. One-time fix.

## Upgrading

When a new version comes out:

```bash
python install_arduino_ide.py --uninstall
# Download the new AppImage to ~/Downloads
python install_arduino_ide.py
```

## Why Not Install to hicolor Theme?

```python
# WARNING: Do NOT install icons to ~/.local/share/icons/hicolor/
# It shadows the system-wide hicolor theme and breaks ALL app icons.
# Icons are referenced by absolute path in the .desktop file instead.
```

When you create `~/.local/share/icons/hicolor/index.theme`, GTK uses your local
minimal theme instead of the system theme. Every app that uses a named icon
(not an absolute path) instantly loses its icon. This includes Brave, Chrome,
Telegram, VSCode, and most other applications.
